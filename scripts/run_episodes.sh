#!/bin/bash
# Run every episode in scripts/episodes_all.txt for one model on a local redroid container.
# Resumable: re-running skips episodes that already have a result.
#
#   scripts/run_episodes.sh <model> [run-name]
#
# <model>: sonnet | haiku | opus (Claude 5.5 through Claude Code, agents/claude_agent.sh)
#          or a Codex model slug such as gpt-6.1-sol, gpt-6-luna (agents/codex_agent.sh)
#          or a DeepSeek model id such as deepseek-flash (Claude Code on DeepSeek, agents/deepseek_agent.sh)
#          or dsh-<openrouter deepseek model>, e.g. dsh-deepseek-v4.1-flash (DeepSeek Harness via
#          OpenRouter, pinned to DeepSeek's own endpoint, under the doom-loop guard; agents/dsh_agent.sh)
# Default run name: eps-<prompt version>-<model>, for example eps-v4-sonnet, eps-v4-gpt-6-luna.
# AQB_IDS="id1 id2" runs only those episodes (smoke tests). AQB_REPEATS=n runs n repeats
# per episode (default 1); with --resume only the missing repeats run, e.g. 2 for pass@2.
set -euo pipefail
cd "$(dirname "$0")/.."
m=${1:?usage: scripts/run_episodes.sh <sonnet|haiku|opus|gpt-...|deepseek-...|dsh-...> [run-name]}
ver=$(python3 -c "import sys; sys.path.insert(0, '.'); from tools.eval_lib import EPISODE_PROMPT_VERSION as v; print(v)")
name=${2:-eps-$ver-$m}
case "$m" in
  sonnet|haiku|opus) export AQB_MODEL=claude-$m-5-5; agent=agents/claude_agent.sh ;;
  gpt-*)             export AQB_MODEL=$m;            agent=agents/codex_agent.sh ;;
  deepseek-*)        export AQB_MODEL=$m;            agent=agents/deepseek_agent.sh ;;
  dsh-*)             export AQB_MODEL=deepseek/${m#dsh-}; agent=agents/dsh_agent.sh ;;
  *) echo "unknown model $m" >&2; exit 2 ;;
esac
if [ -n "${AQB_IDS:-}" ]; then read -r -a ids <<< "$AQB_IDS"; else mapfile -t ids < <(grep -v '^\s*$' scripts/episodes_all.txt); fi
./aqb-cli run --redroid --subset all --ids "${ids[@]}" --repeats "${AQB_REPEATS:-1}" \
  --model "$AQB_MODEL" --name "$name" --resume \
  --agent-mcp "$PWD/$agent {prompt_file} {mcp_config}"
