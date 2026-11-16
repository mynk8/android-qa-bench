#!/usr/bin/env bash
# MCP QA agent for aqb run --agent-mcp: Claude Code headless, device tools only.
# Usage: claude_agent.sh <prompt_file> <mcp_config>
# TZ=UTC: the devices (redroid, Limrun) run on UTC; the agent must see the same date as the device.
# AQB_MODEL: exact model id (default claude-sonnet-5-5); AQB_BUDGET_USD: per-run cap.
# Output is Claude Code's stream-json: the full transcript (every message, tool call and tool
# result, i.e. what the agent saw and said), ending with a {"type":"result"} line (usage, cost).
# Exit 0 only when Claude Code finished normally or hit the budget/turn cap; an error result
# (usage limit, API error) exits 3, so the harness records an infrastructure error.
tmp=$(mktemp)
TZ=UTC claude -p "$(cat "$1")" --model "${AQB_MODEL:-claude-sonnet-5-5}" \
  --mcp-config "$2" --strict-mcp-config --tools "" --allowedTools "mcp__device" \
  --setting-sources local --no-session-persistence --output-format stream-json --verbose \
  --max-budget-usd "${AQB_BUDGET_USD:-2.00}" | tee "$tmp"
rc=${PIPESTATUS[0]}
python3 - "$tmp" "$rc" <<'PY'
import json, sys
rc = int(sys.argv[2])
res = None
for line in open(sys.argv[1], errors="replace"):
    try:
        j = json.loads(line)
    except Exception:
        continue
    if j.get("type") == "result":
        res = j
st = (res or {}).get("subtype")
sys.exit(0 if res and st in ("success", "error_max_budget_usd", "error_max_turns") else 3)
PY
code=$?
rm -f "$tmp"
exit $code
