#!/usr/bin/env bash
# MCP QA agent for aqb run --agent-mcp: DeepSeek inside Claude Code (same harness as the Claude
# runs), through DeepSeek's Anthropic-compatible endpoint. Usage: deepseek_agent.sh <prompt_file> <mcp_config>
# - Key: DEEPSEEK_API_KEY from the repo's .env (never printed). ANTHROPIC_API_KEY is removed from
#   the environment so no Anthropic credential is sent to DeepSeek.
# - AQB_MODEL: DeepSeek model id (default deepseek-flash = V4.1-Flash). Claude Code's background
#   "small/fast" calls use the same model.
# - Claude Code prices tokens as Anthropic models, so its total_cost_usd and --max-budget-usd do
#   not apply here: the budget cap is set high and the 300-action cap bounds each episode. Real
#   cost is computed from the token usage at DeepSeek's prices.
here=$(cd "$(dirname "$0")" && pwd)
key=$(grep -m1 '^DEEPSEEK_API_KEY=' "$here/../.env" 2>/dev/null | cut -d= -f2- | tr -d '"'"'"' \r')
if [ -z "$key" ]; then
  echo '{"type":"result","subtype":"error","is_error":true,"error":"DEEPSEEK_API_KEY missing in .env"}'
  exit 3
fi
model=${AQB_MODEL:-deepseek-flash}
exec env -u ANTHROPIC_API_KEY \
  ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic \
  ANTHROPIC_AUTH_TOKEN="$key" \
  ANTHROPIC_DEFAULT_HAIKU_MODEL="$model" ANTHROPIC_SMALL_FAST_MODEL="$model" \
  CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1 \
  AQB_MODEL="$model" AQB_BUDGET_USD="${AQB_BUDGET_USD:-1000}" \
  "$here/claude_agent.sh" "$@"
