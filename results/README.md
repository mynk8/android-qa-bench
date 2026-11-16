# Scored runs

One directory per agent configuration, each holding all 51 episodes. The layout is a run
directory, so every tool in `tools/` reads it directly.

| Directory | Model | Harness | Reasoning effort |
|---|---|---|---|
| `claude-sonnet-5.5-medium` | Claude Sonnet 5.5 | Claude Code | medium (harness default) |
| `claude-haiku-5.5` | Claude Haiku 5.5 | Claude Code | harness default |
| `gpt-6.1-sol-low` | GPT-6.1 Sol | Codex CLI | low (harness default) |
| `gpt-6-luna-medium` | GPT-6 Luna | Codex CLI | medium (harness default) |
| `gpt-6-luna-max` | GPT-6 Luna | Codex CLI | max |
| `deepseek-v4.1-flash-high` | DeepSeek V4.1 Flash | DeepSeek Harness | high |

## Files

```
<config>/
  run.json                              model, agent command, protocol, prompt version, limits,
                                        device, dataset fingerprint, episode list
  results.jsonl                         one row per episode: outcome, recall, precision, steps,
                                        seconds, tokens and cost
  episodes/<episode>/<run_id>/
    result.json                         planted and credited regressions, every report and how it
                                        was scored, the sign-off, steps, usage
    trace.jsonl                         every tool call the harness executed, with results, and
                                        every scoring decision
  agent_logs/<episode>-rep0.log         the agent's full transcript in its harness's JSON format:
                                        messages, reasoning where the harness emits it, tool calls
                                        and everything the tools returned
  leaderboard.json, leaderboard.md      tools/leaderboard.py on this directory
```

Transcripts are complete except that screenshot images are replaced by a placeholder with their
size and SHA-256; the UI text the agent received with each observation is kept. Each episode has
exactly one scored attempt. `tools/export_results.py` produced this directory from the raw run
directories.

## Recompute

```bash
python3 tools/leaderboard.py results/claude-sonnet-5.5-medium            # scores and splits
python3 tools/changelog_coverage.py results/claude-sonnet-5.5-medium --detail
python3 tools/rescore_episodes.py results/claude-sonnet-5.5-medium       # replay reports against the keys
python3 tools/hesitations.py results/claude-haiku-5.5 -v                 # why sessions ended without sign-off
python3 docs/paper/data/collect.py && python3 docs/paper/data/analysis.py && python3 docs/paper/data/hard_core.py
python3 docs/paper/data/write_results_md.py                              # docs/RESULTS.md
```
