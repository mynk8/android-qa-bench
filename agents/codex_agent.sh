#!/usr/bin/env bash
# MCP QA agent for aqb run --agent-mcp: OpenAI Codex CLI headless, device tools only.
# Usage: codex_agent.sh <prompt_file> <mcp_config>
# Same contract as agents/claude_agent.sh:
# - Device tools only: every Codex built-in tool is switched off (shell, unified exec, multi-agent,
#   browser, computer use, apps, plugins, image tools, web search).
# - Code Mode stays on: for GPT-6 models (catalog tool_mode code_mode_only) Codex offers MCP tools
#   only through its `exec` JavaScript tool, so the model can chain several device calls in one
#   step. Every device call still counts as one harness action. The exec runtime has no require,
#   fetch, process or file access. Device tools are pre-approved (default_tools_approval_mode).
# - Sub-agents off: the model catalog enables them (multi_agent_version v2) regardless of feature
#   flags, so each episode passes a copy of ~/.codex/models_cache.json with that cleared.
# - No user config, rules, skills or session files: --ignore-user-config --ignore-rules
#   --ephemeral, and an empty temp HOME and CODEX_HOME holding only a copy of the ChatGPT sign-in
#   (copied back if Codex refreshed it). Checked 2026-11-14 with codex-cli 0.166.0 and gpt-6-luna:
#   device calls work, screenshots reach the model, no command, file, network or sub-agent access.
# - TZ=UTC: the devices run on UTC; the agent must see the same date as the device.
# - AQB_MODEL: Codex model slug (default gpt-6.1-sol). Reasoning effort is the model's default
#   unless AQB_REASONING is set (low|medium|high).
# - Route (AQB_CODEX_ROUTE): plan (default) = the ChatGPT sign-in; openrouter = the OpenRouter Responses API
#   (model openai/<AQB_MODEL>, key as in dsh_agent.sh: OPENROUTER_API_KEY, else the repo .env, else
#   ~/.dsh/.credentials.yaml; never printed); auto = the plan until it hits its usage
#   limit, then OpenRouter. In auto, a plan usage-limit error writes AQB_CODEX_PLAN_SPENT (default
#   runs/.codex-plan-spent) and ends that episode as an infrastructure error (exit 3, re-run by
#   --resume); every later episode reads the file and goes to OpenRouter. Delete the file to go
#   back to the plan. OpenRouter out of credit (HTTP 402) writes AQB_OPENROUTER_SPENT (default
#   runs/.openrouter-spent) and ends that episode as an infrastructure error; while that file
#   exists, route openrouter falls back to the plan. Delete it after a top-up. Pin the OpenRouter provider (OpenAI only) in the OpenRouter account settings:
#   Codex cannot add routing fields to its requests.
# Output: Codex's --json event stream (the full transcript), then one
# {"type":"result",...} line with the summed token usage and the route, so tools/leaderboard.py can
# read it. total_cost_usd uses AQB_PRICE_IN / AQB_PRICE_CACHED / AQB_PRICE_OUT (USD per million
# tokens); unset, it uses OpenAI's list price for gpt-6-luna and gpt-6.1-sol, else 0. Plan episodes
# get the same API-equivalent price, so both routes compare. Exit 0 when the turn completed, 3 on
# an error result (usage limit, API error), so the harness records an infrastructure error.
set -uo pipefail
prompt_file=$1
mcp_config=$2
mapfile -t mcp_args < <(python3 - "$mcp_config" <<'PY'
import json, sys
srv = json.load(open(sys.argv[1]))["mcpServers"]["device"]
toml = lambda v: json.dumps(v)  # JSON strings and arrays are valid TOML values
print(f'mcp_servers.device.command={toml(srv["command"])}')
print(f'mcp_servers.device.args={toml(srv.get("args", []))}')
env = ", ".join(f"{k} = {toml(v)}" for k, v in (srv.get("env") or {}).items())
print("mcp_servers.device.env={" + env + "}")
print("mcp_servers.device.startup_timeout_sec=60")
print("mcp_servers.device.tool_timeout_sec=300")
print('mcp_servers.device.default_tools_approval_mode="approve"')
PY
)
cfg=()
for a in "${mcp_args[@]}"; do cfg+=(-c "$a"); done
for f in shell_tool unified_exec multi_agent apps plugins remote_plugin \
         skill_search tool_suggest browser_use browser_use_external in_app_browser computer_use \
         image_generation view_image sleep_tool; do
  cfg+=(--disable "$f")
done
cfg+=(-c 'web_search="disabled"' -c 'approval_policy="never"')
[ -n "${AQB_REASONING:-}" ] && cfg+=(-c "model_reasoning_effort=\"$AQB_REASONING\"")
here=$(cd "$(dirname "$0")" && pwd)
model=${AQB_MODEL:-gpt-6.1-sol}
route=${AQB_CODEX_ROUTE:-plan}
spent=${AQB_CODEX_PLAN_SPENT:-$here/../runs/.codex-plan-spent}
or_spent=${AQB_OPENROUTER_SPENT:-$here/../runs/.openrouter-spent}
if [ "$route" = auto ]; then
  if [ -e "$spent" ]; then route=openrouter; else route=plan; fi
  auto=1
else
  auto=0
fi
[ "$route" = openrouter ] && [ -e "$or_spent" ] && route=plan  # OpenRouter credit ran out
env_args=()
if [ "$route" = openrouter ]; then
  key=${OPENROUTER_API_KEY:-}
  [ -z "$key" ] && key=$(grep -m1 '^OPENROUTER_API_KEY=' "$here/../.env" 2>/dev/null | cut -d= -f2- | tr -d '"'"'"' \r')
  [ -z "$key" ] && key=$(sed -nE 's/^[[:space:]]+OPENROUTER_API_KEY:[[:space:]]*["'"'"']?([^"'"'"' ]+).*/\1/p' "$HOME/.dsh/.credentials.yaml" 2>/dev/null | head -1)
  if [ -z "$key" ]; then
    echo '{"type":"result","subtype":"error","is_error":true,"agent":"codex","route":"openrouter","error":"OPENROUTER_API_KEY not found"}'; exit 3
  fi
  env_args=(OPENROUTER_API_KEY="$key")
  case "$model" in */*) ;; *) model=openai/$model ;; esac
  cfg+=(-c 'model_provider="openrouter"' -c 'model_providers.openrouter.name="OpenRouter"'
        -c 'model_providers.openrouter.base_url="https://openrouter.ai/api/v1"'
        -c 'model_providers.openrouter.env_key="OPENROUTER_API_KEY"'
        -c 'model_providers.openrouter.wire_api="responses"'
        -c 'model_providers.openrouter.supports_websockets=false')
fi
# The model catalog turns on Codex's sub-agent tools (multi_agent_version v2) whatever the feature
# flags say. Give Codex a copy of its own catalog with that switched off for this model.
catalog=$(mktemp --suffix .json)
if ! python3 - "$HOME/.codex/models_cache.json" "${model##*/}" "$catalog" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
ms = d.get("models", d) if isinstance(d, dict) else d
hit = [m for m in ms if m.get("slug") == sys.argv[2]]
for m in hit:
    m["multi_agent_version"] = None
json.dump({"models": ms}, open(sys.argv[3], "w"))
sys.exit(0 if hit else 1)
PY
then
  rm -f "$catalog"
  echo '{"type":"result","subtype":"error","is_error":true,"agent":"codex","error":"model not in the Codex model catalog"}'; exit 3
fi
cfg+=(-c "model_catalog_json=\"$catalog\"")
# Empty HOME and CODEX_HOME for the run, so Codex lists none of the user's own skills; only the
# ChatGPT sign-in is carried over (copied back afterwards if Codex refreshed it).
real_home=${CODEX_HOME:-$HOME/.codex}
codex_bin=$(readlink -f "$(command -v codex)")
iso=$(mktemp -d)
mkdir -p "$iso/home" "$iso/codex"
[ -f "$real_home/auth.json" ] && cp -p "$real_home/auth.json" "$iso/codex/auth.json"
tmp=$(mktemp)
env -u OPENAI_API_KEY "${env_args[@]}" HOME="$iso/home" CODEX_HOME="$iso/codex" TZ=UTC \
  "$codex_bin" exec --ignore-user-config --ignore-rules --ephemeral --skip-git-repo-check \
  -s read-only -m "$model" "${cfg[@]}" --json "$(cat "$prompt_file")" \
  < /dev/null | tee "$tmp"
rc=${PIPESTATUS[0]}
if [ -f "$iso/codex/auth.json" ] && [ "$iso/codex/auth.json" -nt "$real_home/auth.json" ] \
   && ! cmp -s "$iso/codex/auth.json" "$real_home/auth.json"; then
  cp -p "$iso/codex/auth.json" "$real_home/auth.json"
fi
rm -rf "$iso"
AQB_ROUTE=$route AQB_AUTO=$auto AQB_SPENT=$spent AQB_OR_SPENT=$or_spent AQB_ROUTED_MODEL=$model python3 - "$tmp" "$rc" <<'PY'
import json, os, re, sys, time
rc = int(sys.argv[2])
use = {"input_tokens": 0, "cached_input_tokens": 0, "output_tokens": 0, "reasoning_output_tokens": 0}
done = failed = limit_hit = False
err = None
turns = 0
for line in open(sys.argv[1], errors="replace"):
    try:
        e = json.loads(line)
    except Exception:
        continue
    t = e.get("type")
    if t == "turn.completed":
        done = True
        turns += 1
        for k in use:
            use[k] += int((e.get("usage") or {}).get(k) or 0)
    elif t in ("turn.failed", "error"):
        failed = True
        err = e.get("message") or (e.get("error") or {}).get("message")
        if re.search(r"usage.?limit|credits.?depleted|requires more credits|insufficient.?credits|\b402\b",
                     line, re.I):
            limit_hit = True
route = os.environ["AQB_ROUTE"]
if route == "openrouter" and limit_hit:
    with open(os.environ["AQB_OR_SPENT"], "w") as f:
        f.write(time.strftime("%Y-%m-%dT%H:%M:%S%z") + " OpenRouter out of credit: " + str(err)[:300] + "\n")
if route == "plan" and limit_hit and os.environ.get("AQB_AUTO") == "1":
    with open(os.environ["AQB_SPENT"], "w") as f:
        f.write(time.strftime("%Y-%m-%dT%H:%M:%S%z") + " plan usage limit: " + str(err)[:300] + "\n")
LIST = {"gpt-6-luna": (0.10, 0.01, 0.50), "gpt-6.1-sol": (2.00, 0.10, 10.00)}
base = (os.environ.get("AQB_MODEL") or "gpt-6.1-sol").split("/")[-1]
dflt = dict(zip(("AQB_PRICE_IN", "AQB_PRICE_CACHED", "AQB_PRICE_OUT"), LIST.get(base, (0, 0, 0))))
p = lambda k: float(os.environ.get(k) or dflt[k])
fresh = use["input_tokens"] - use["cached_input_tokens"]
cost = (fresh * p("AQB_PRICE_IN") + use["cached_input_tokens"] * p("AQB_PRICE_CACHED")
        + use["output_tokens"] * p("AQB_PRICE_OUT")) / 1e6
ok = done and not failed
print(json.dumps({"type": "result", "subtype": "success" if ok else "error", "is_error": not ok,
                  "agent": "codex", "model": os.environ.get("AQB_MODEL") or "gpt-6.1-sol",
                  "route": route, "routed_model": os.environ["AQB_ROUTED_MODEL"], "usage_limit": limit_hit,
                  "num_turns": turns, "usage": use, "total_cost_usd": round(cost, 4), "error": err,
                  "exit_code": rc}))
sys.exit(0 if ok else 3)
PY
code=$?
rm -f "$tmp" "$catalog"
exit $code
