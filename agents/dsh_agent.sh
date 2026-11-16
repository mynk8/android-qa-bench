#!/usr/bin/env bash
# MCP QA agent for aqb run --agent-mcp: DeepSeek Harness (dsh) headless, DeepSeek V4.1 Flash via
# OpenRouter. Usage: dsh_agent.sh <prompt_file> <mcp_config.json>  (same contract as claude_agent.sh)
#
# - Harness: ~/workspace/deepseek-harness (DSH_REPO), launched from an empty temp cwd with a fresh
#   temp DSH_HOME per episode (no sessions, memory or AGENTS.md carried between runs).
# - Tools: agents/dsh-lockdown.patch.yml disables every built-in tool; the model sees only the
#   device MCP server's tools (mcp__device__*). Approvals: never.
# - Model: deepseek/deepseek-v4.1-flash (AQB_MODEL), reasoning effort high (AQB_DSH_EFFORT).
#   Output is capped at AQB_DSH_MAX_OUT tokens per request (default 32000, DeepSeek's own default
#   for its reasoning API), so one runaway message ends quickly. The model entry declares image
#   input; without it dsh sends the model an empty string for every screenshot.
# - Inference provider: pinned per request to DeepSeek's own endpoint (provider.only=[deepseek],
#   allow_fallbacks=false) through pi-ai's openRouterRouting compat field. dsh withholds that field
#   by default; the harness checkout has it set to 'offer' in packages/llm/llm-pi-ai (src and lib).
# - Key: OPENROUTER_API_KEY from the environment, else the repo .env, else ~/.dsh/.credentials.yaml.
#   Never printed; dsh strips it from the MCP server's environment.
# - Doom loops: run under agents/loop_guard.py, which kills a degenerate repetition loop (exit 4,
#   outcome doom_loop). dsh --json emits reasoning per finished message, so the per-request output
#   cap bounds how long a loop runs before the guard sees it.
# Output: dsh --json events, then one {"type":"result",...} line with summed token usage and cost at
# AQB_PRICE_IN / AQB_PRICE_CACHED / AQB_PRICE_OUT (USD per million; OpenRouter list prices for this
# model by default). Exit: 0 turn completed, 4 doom loop, 3 infrastructure error (auth, rate limit,
# crash, no final event).
set -uo pipefail
prompt_file=$1; mcp_config=$2
here=$(cd "$(dirname "$0")" && pwd)
repo=${DSH_REPO:-$HOME/workspace/deepseek-harness}
model=${AQB_MODEL:-deepseek/deepseek-v4.1-flash}
key=${OPENROUTER_API_KEY:-}
[ -z "$key" ] && key=$(grep -m1 '^OPENROUTER_API_KEY=' "$here/../.env" 2>/dev/null | cut -d= -f2- | tr -d '"'"'"' \r')
[ -z "$key" ] && key=$(sed -nE 's/^[[:space:]]+OPENROUTER_API_KEY:[[:space:]]*["'"'"']?([^"'"'"' ]+).*/\1/p' "$HOME/.dsh/.credentials.yaml" 2>/dev/null | head -1)
if [ -z "$key" ]; then
  echo '{"type":"result","subtype":"error","is_error":true,"error":"OPENROUTER_API_KEY not found"}'; exit 3
fi
tmp=$(mktemp -d -t aqb-dsh.XXXXXX); trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/home" "$tmp/cwd"
python3 - "$mcp_config" "$tmp/episode.patch.yml" "$model" "${AQB_DSH_EFFORT:-high}" "${AQB_DSH_MAX_OUT:-32000}" <<'PY'
import json, os, sys
cfg = json.load(open(sys.argv[1]))["mcpServers"]
model, effort, max_out = sys.argv[3], sys.argv[4], int(sys.argv[5])
rows = [{"id": f"mcp-{n}", "name": "@deepseek-ai/dsh-mcp-client",
         "config": {"serverName": n, "transport": "stdio", "command": s["command"], "args": s.get("args", []),
                    "env": s.get("env", {}), "failOnStartupError": True, "startupTimeoutMs": 60000,
                    "toolCallTimeoutMs": 300000, "reconnect": {"enabled": False}}} for n, s in cfg.items()]
patch = [{"insert": rows},
         {"id": "llm-pi-ai", "config": {"providers": {"openrouter": {
             "apiKeyEnv": "OPENROUTER_API_KEY",
             "models": [{"id": model, "maxTokens": max_out,
                         # served only by DeepSeek's own endpoint, never another host (needs the
                         # openRouterRouting compat gate set to 'offer' in the harness)
                         # dsh treats an undeclared custom model as text-only and replaces
                         # screenshot images with their (empty) text fallback
                         "input": ["text", "image"],
                         "compat": {"openRouterRouting": {"only": ["deepseek"], "allow_fallbacks": False}}}]}}}},
         {"id": "agent-default-model", "config": {"provider": "openrouter", "model": model, "reasoningEffort": effort}}]
if os.environ.get("AQB_DSH_BASE_URL"):  # tests only: point the route at a local mock
    patch[1]["config"]["providers"]["openrouter"]["baseURL"] = os.environ["AQB_DSH_BASE_URL"]
json.dump(patch, open(sys.argv[2], "w"), indent=1)
PY
extra=(); [ -n "${AQB_DSH_EXTRA_PATCH:-}" ] && extra=(--patch "$AQB_DSH_EXTRA_PATCH")
cd "$tmp/cwd"
env -u DEEPSEEK_API_KEY -u ANTHROPIC_API_KEY TZ=UTC DSH_HOME="$tmp/home" OPENROUTER_API_KEY="$key" \
  python3 "$here/loop_guard.py" -- \
  node "$repo/apps/cli/lib/bin.js" --profile headless \
    --patch "$here/dsh-lockdown.patch.yml" --patch "$tmp/episode.patch.yml" "${extra[@]}" \
    --approval-policy never --json - < "$prompt_file" | tee "$tmp/out.jsonl"
rc=${PIPESTATUS[0]}
if [ -n "${AQB_DSH_SESSION_OUT:-}" ]; then
  f=$(find "$tmp/home/sessions" -name 'session.v4.jsonl.zstd' 2>/dev/null | head -1)
  [ -n "$f" ] && zstd -q -dc "$f" > "$AQB_DSH_SESSION_OUT" || true
fi
python3 - "$tmp/out.jsonl" "$rc" "$model" <<'PY'
import json, os, sys
rc, model = int(sys.argv[2]), sys.argv[3]
use = {"input_tokens": 0, "cached_input_tokens": 0, "cache_write_tokens": 0, "output_tokens": 0}
final = None
steps = 0
for line in open(sys.argv[1], errors="replace"):
    try:
        e = json.loads(line)
    except Exception:
        continue
    if e.get("type") == "status" and e.get("phase") == "step_end":
        steps += 1
        u = e.get("usage") or {}
        use["input_tokens"] += int(u.get("inputTokens") or 0)
        use["cached_input_tokens"] += int(u.get("cacheReadTokens") or 0)
        use["cache_write_tokens"] += int(u.get("cacheWriteTokens") or 0)
        use["output_tokens"] += int(u.get("outputTokens") or 0)
    elif e.get("type") == "final":
        final = e
price = lambda k, d: float(os.environ.get(k) or d)
cost = (use["input_tokens"] * price("AQB_PRICE_IN", 0.0507) + use["cache_write_tokens"] * price("AQB_PRICE_IN", 0.0507)
        + use["cached_input_tokens"] * price("AQB_PRICE_CACHED", 0.001014)
        + use["output_tokens"] * price("AQB_PRICE_OUT", 0.2028)) / 1e6
kind = ((final or {}).get("reason") or {}).get("kind")
err = ((final or {}).get("reason") or {}).get("error")
if rc == 4:
    sub, code = "error_doom_loop", 4
elif rc == 0 and kind == "completed":
    sub, code = "success", 0
else:
    sub, code = "error", 3
print(json.dumps({"type": "result", "subtype": sub, "is_error": code != 0, "agent": "dsh", "model": model,
                  "num_steps": steps, "usage": use, "total_cost_usd": round(cost, 5),
                  "final_reason": kind, "error": err, "exit_code": rc}))
sys.exit(code)
PY
