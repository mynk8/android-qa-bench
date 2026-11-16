# AQB: an Android release-QA benchmark for LLM agents

AQB asks an LLM agent to do what a release QA tester does: given a build of a real Android app and
its release notes, find the regressions before the release ships, report them, and sign off. Each
regression is a real upstream bug, forward-ported onto a pinned head commit and verified on a
device against its fixed build. Grading is deterministic code; no model judges the agent.

| Item | Count |
|---|---:|
| Apps (open source) | 9 |
| Device-verified bugs | 101 |
| Episodes (release-QA sweeps of a build with 1 to 3 planted regressions) | 51 |
| Regressions planted in episodes (observable) | 92 (91) |
| Release-note lines in episode briefs (real / decoy) | 92 / 93 |
| Cases (one specified check on a clean or faulty build) | 308 (202 specified, 106 unspecified) |
| Agent configurations evaluated on all 51 episodes | 6 |

## Where to read

| What | Where |
|---|---|
| How the benchmark is built, run and graded | [docs/METHODOLOGY.md](docs/METHODOLOGY.md) |
| Results of the six configurations, with every derived number | [docs/RESULTS.md](docs/RESULTS.md) |
| The paper (LaTeX, PDF, figures and the scripts that make them) | [docs/paper/](docs/paper/) |
| Scored runs: results, per-episode traces and full agent transcripts | [results/](results/) |
| The dataset contract (format every bug, case and episode follows) | [BOT_BRIEF.md](BOT_BRIEF.md) |

## Headline results (51 episodes, one run each)

| Configuration | Recall | Strict pass | Precision | Episode Score | Actions / episode | $ / episode |
|---|---:|---:|---:|---:|---:|---:|
| GPT-6.1 Sol (low), Codex CLI | **59%** | **29%** | 34% | 0.29 | 202 | 0.65 |
| DeepSeek V4.1 Flash (high), DeepSeek Harness | 51% | 12% | 34% | 0.18 | 294 | 0.06 |
| Claude Sonnet 5.5 (medium), Claude Code | 46% | 24% | 44% | **0.39** | 67 | 0.54 |
| Claude Haiku 5.5, Claude Code | 43% | 14% | 28% | 0.24 | 217 | 0.64 |
| GPT-6 Luna (max), Codex CLI | 34% | 12% | 24% | 0.21 | 166 | 0.16* |
| GPT-6 Luna (medium), Codex CLI | 15% | 4% | **50%** | 0.14 | 39 | 0.02 |

Recall: planted regressions credited. Strict pass: every regression reported, then a sign-off.
Episode Score: catch credit x report precision x 1/2 if cut off at the action cap or the report
limit. Cost at API list prices as reported by each harness; *mean over sessions that logged a cost
(DeepSeek 23 of 51, Luna max 50 of 51). Sonnet, Haiku and DeepSeek ran episode prompt v4, the others
v4.1 (sign-off rule; see METHODOLOGY section 7). Intervals, splits and analysis:
[docs/RESULTS.md](docs/RESULTS.md).

Reproduce from the stored runs:

```bash
python3 tools/leaderboard.py results/gpt-6.1-sol-low
python3 tools/changelog_coverage.py results/gpt-6.1-sol-low --detail
python3 docs/paper/data/collect.py && python3 docs/paper/data/analysis.py && python3 docs/paper/data/stats_extra.py
```

## Running an agent

Linux with KVM or Docker, 16 GB RAM, about 40 GB of disk. `./aqb-cli` (or `python3 -m aqb`) runs
every step.

```bash
./aqb-cli doctor                      # what is installed, built and calibrated
./aqb-cli build                       # core APKs from each app's pinned head + patches
./aqb-cli calibrate --pending         # device checks per bug and episode; marks them verified
./aqb-cli run --redroid --subset all --type episode --repeats 1 --name my-run \
  --agent-mcp 'agents/claude_agent.sh {prompt_file} {mcp_config}' --model claude-sonnet-5-5
python3 tools/leaderboard.py runs/my-run
```

`scripts/run_episodes.sh <model> <run-name>` runs the 51 episodes with the settings used for the
stored results. Agents operate the device only through the MCP server `aqb/mcp_device.py`
(`observe`, `screenshot`, `tap`, `long_press`, `type_text`, `swipe`, `press_key`, `rotate`,
`open_app`, `wait`, plus `file_report` / `sign_off` for episodes and `submit_verdict` for cases).
Run the agent with every other tool disabled: an agent with a shell on the host could read
`private/`. Wrappers for Claude Code, Codex CLI and DeepSeek Harness are in `agents/`.

Without an emulator or APKs (fake device, oracle agent):

```bash
./aqb-cli run --agent oracle --subset all --dry-run --limit 6 --name smoke
```

## Layout

```
dataset/                 agent-facing data and ground truth
  apps/<app>/            app.json, seed data, build index
  bugs/<bug>/            bug.json, checks.py (target, held-out, preservation), repro.py,
                         match.json (grading key), calibration.json (device evidence),
                         reference_reports.json
  cases/<case>/          case.json + agent_input.md
  episodes/<episode>/    episode.json + brief.md (what the agent receives)
  instances.jsonl        every instance with agent-safe fields
dataset_tools/           device API, matcher (grader), validators
aqb/                     CLI: build, calibrate, devices (redroid, emulator, Limrun), MCP server
agents/                  agent wrappers (Claude Code, Codex CLI, DeepSeek Harness), loop guard
tools/                   episode and case harness, leaderboard, coverage, rescoring, export
scripts/                 run_episodes.sh, the episode list
results/<config>/        scored runs of the six configurations
docs/                    METHODOLOGY.md, RESULTS.md, paper/
private/                 answer material: original diffs, forward-port patches, release-note key,
                         screen anchors, mining provenance, dropped bugs, matcher validation corpora
artifacts/               build manifest (commit, patches, toolchain and SHA-256 of every APK)
```

`private/` holds the answers. Never give an agent access to it, and keep it out of any public
release of the dataset used as a leaderboard.

## Apps

| App | Upstream | Licence | Package |
|---|---|---|---|
| Amaze File Manager | TeamAmaze/AmazeFileManager | GPL-3.0 | `com.amaze.filemanager` |
| AnkiDroid | ankidroid/Anki-Android | GPL-3.0 | `com.ichi2.anki` |
| Markor | gsantner/markor | Apache-2.0 | `net.gsantner.markor` |
| Tasks.org | tasks/tasks | GPL-3.0 | `org.tasks` |
| Minus | isaacsa51/Minus | Apache-2.0 | `com.serranoie.app.minus` |
| Iris Gallery | MohamadOday/iris-gallery | Apache-2.0 | `com.iris.gallery` |
| Featherline | mkx173/Featherline | GPL-3.0 | `com.mkx.hrttracker` |
| NerdCalci | vishaltelangre/NerdCalci | GPL-3.0 | `com.vishaltelangre.nerdcalci` |
| Idle Fantasy | tristinbaker/IdleFantasy | GPL-3.0 | `com.tristinbaker.idlefantasy` |

Redistribute builds only as each licence allows (GPL-3.0 needs a source offer; see
`private/licences.md`).

## Checks

```bash
python3 dataset_tools/validate_dataset.py dataset/
python3 tools/finalize.py
python3 -m unittest tools.tests.test_eval tools.tests.test_matcher tools.tests.test_fast tools.tests.test_mcp tools.tests.test_audit_fixes
python3 tools/rescore_episodes.py results/<config> --check   # stored decisions reproduce with current keys
python3 tools/make_public_release.py ../aqb-public           # export without private/, checked
```
