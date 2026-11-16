# Methodology

How AQB is built, run and graded. Every step names the code or data that implements it, so a
reader (or an agent) can check it against the repository.

## 1. Apps

Nine open-source Android apps (upstream repositories in the README). Four are mature projects with
long histories: Amaze File Manager, AnkiDroid, Markor, Tasks.org. Five have a history entirely
from 2026: Minus, Iris Gallery, Featherline, NerdCalci, Idle Fantasy. NerdCalci (a notepad
calculator) and Idle Fantasy (an idle role-playing game) are not form-and-list apps; most of their
bugs are plausible-looking wrong values a tester must compute to catch. All apps render standard
Android or Compose UI, so every visible text is in the accessibility tree.

Each app is pinned to one head commit (`private/apps/repo_meta.json`, `dataset/apps/<app>/app.json`).
Seed data per app: `dataset/apps/<app>/seed.py` and `seed/`.

## 2. Bugs

### 2.1 Mining
Each bug starts from a merged upstream fix whose change corrects behaviour a user can see.
Provenance per bug: `private/diffs/<bug>.diff` (original fix), `dataset/bugs/<bug>/bug.json`
(`source`, `fix_date`, `family`, `symptom_type`). Mining scripts, candidate shortlists and
per-app authoring reports for the later bugs: `private/mining/`.

A fix is kept when its bug (i) shows on the screen or in data the app displays, (ii) is
deterministic, and (iii) can be judged wrong by a tester without the code. Bugs whose only symptom
is wording or a default value are kept for specified cases only. Dropped bugs and the reason for
each: `private/dropped/`.

Current set: 101 bugs; families state 41, display 40, interaction 20; sources 57 from mature
projects, 44 from 2026 projects.

### 2.2 Forward-porting
Every bug is re-introduced on its app's pinned head: buggy build = head +
`private/forwardport/<bug>.patch`; fixed build = clean head. All bugs of an app share one source
tree, so an episode build can combine several of them and every text the agent reads matches the
head's UI. Each port records its approach, a confidence label and label issues
(`private/forwardport/<bug>.json`). Build plan: `private/forwardport/plan.json`. Every APK is
recorded in `artifacts/build_manifest.jsonl` with source commit, applied patches, JDK, Gradle task,
package, SHA-256 and build log.

### 2.3 Device checks and calibration
Each bug has three deterministic checks in `dataset/bugs/<bug>/checks.py`, written against the
device API (`dataset_tools/device_api.py`, helpers in `check_helpers.py`):

| Check | What it does | Required on buggy | Required on fixed |
|---|---|---|---|
| target | drives the bug's own trigger and reads the result | FAIL | PASS |
| held-out | reaches the same defect by another input or path | FAIL | PASS |
| preservation | checks neighbouring behaviour | PASS | PASS |

Checks seed the app, drive a fixed path, and read the screen or the app's stored data. App-private
data is read by an instrumentation probe (`aqb/probe/`) signed with the app's debug key, so no
device needs root. `aqb calibrate` runs every check on both builds; the result per run, with
observations and screenshot hashes, is in `dataset/bugs/<bug>/calibration.json`. A bug is
`verified` only when every requirement in the table holds. Each check ran once per build.

### 2.4 Grading keys
`dataset/bugs/<bug>/match.json` holds the key the matcher uses (section 5):
location concepts, expected and observed concept groups, accepted symptom types, and anchors
(elements where the defect shows and buggy-only values, validated against calibration evidence by
`private/review/scorer/check_anchors.py`). `reference_reports.json` holds a correct, a vague and a
wrong-bug report per bug; the matcher must credit only the correct one.

### 2.5 Review of the dataset
Two reviews by agents that did not write the items, recorded in `private/review/`:

- **Agent-facing text** (`INSTRUCTIONS.md`, one file per app, e.g. `amaze.json`): every case and
  episode brief was checked against the head's UI and the way each bug was re-created, and rewritten
  where it was wrong or gave the answer away; each entry records what changed and why.
- **Logical gaps** (`AUDIT.md`, findings `audit-g*.json`, fixes `fix-g*.json`, `AUDIT_FIX.md`): all
  items were audited for patch fidelity, case fairness, leaks, grading and check validity. The 21
  major and 53 minor findings were fixed (patches re-ported, case texts corrected, keys tightened,
  wording-only bugs moved to specified cases) or the bug was dropped, and every changed bug and
  episode was re-calibrated on a device.

`tools/leak_scan.py` checks that `dataset/` holds no commit SHAs, repository, PR or issue URLs, and
that no brief contains a bug id, commit wording, fix hint or a code identifier from the original
fix; `tools/finalize.py` runs it with the validator and the reference-report check.

## 3. Episodes

An episode (`dataset/episodes/<episode>/`) is a pre-release QA sweep of one build of one app.

- **Composition.** One to three bugs of the same app whose patches touch different files and apply
  together (16 episodes with one, 29 with two, 6 with three; 92 planted regressions). Groups whose
  bugs interfered on the device were split. In `amaze-E01`, amaze-0004 removes the code path that
  amaze-0005 changes; amaze-0005 is masked and excluded from scoring, leaving 91 observable
  regressions.
- **Start-build check.** Every episode build was calibrated: each observable bug's target check
  fails on it and the preservation checks pass.
- **Brief** (`brief.md`, the only task text the agent receives):
  - the areas to sweep;
  - preconditions: the seeded data;
  - *Changed in this build*: one line per planted regression plus one or two lines for harmless
    changes (92 real, 93 decoy), in mixed order.
- **Release-note rules.** A line names the feature and what changed in its mechanism, like a real
  changelog ("Subtasks section of the sort sheet: its controls are now built the same way for
  every option"). It never states a symptom, a trigger or an expected value. Real and decoy lines
  use the same verbs. Answer key: `private/release_notes/notes.json` (which line hides which
  bug).

## 4. Running an episode

### 4.1 Device
A fresh Android 15 x86_64 redroid container per episode (`aqb/redroid_session.py`), 1080x2400 at
420 dpi. Before the episode: device reset, the episode's start build installed, the app's seed data
written, the app opened.

### 4.2 Agent interface
The agent reaches the device only through the MCP server `aqb/mcp_device.py`:

| Tool | Effect |
|---|---|
| `observe` | numbered UI elements with text, content description, state and centre; optional screenshot |
| `screenshot` | a screenshot |
| `tap`, `long_press` | by element number or coordinates |
| `type_text`, `swipe`, `press_key`, `rotate`, `open_app`, `wait` | device input |
| `file_report` | a bug report (4.4) |
| `sign_off` | PASS verdict with confidence and notes; ends the episode |

Each call is relayed over a local socket to the harness (`tools/eval_lib.py`, `tools/run_eval.py`),
which executes it, records it in `trace.jsonl` and returns the result. The agent process starts in
an empty temporary directory, its harness has every built-in tool disabled (no shell, files or
web), and a message that names secret paths (`private/...`, `checks.py`, `match.json`) disqualifies
the run as `reward_hack`.

### 4.3 Prompt
`tools/eval_lib.py`: `AGENT_PROMPT` = the brief + `QA_METHOD` + how to finish (`FINISH_EPISODE`).
`QA_METHOD` is a generic testing method that names no app, screen or bug:

- plan every area and exercise each before signing off; signing off with bugs unreported is the
  worst outcome;
- for each feature check state (leave and come back), reversal, repetition, input (empty,
  boundary, unusual values), consistency between screens, device rotation, navigation by more than
  one route;
- use the seeded data; reproduce a problem once before reporting it.

### 4.4 Reports
`file_report` fields: `screen`, `element`, `field`, `symptom_type` (wrong_value, missing,
not_persisted, cut_off, wrong_navigation, no_effect, duplicated, overlap), `expected`, `observed`,
`steps`, and where possible `element_ref` (number of the element in the latest `observe`) and
`observed_quote` (exact on-screen text that shows the defect).

### 4.5 Developer and termination
A scripted developer replies to each report (`REPLY` in `tools/eval_lib.py`):

| Report | Reply |
|---|---|
| credited to a planted regression | "thanks, confirmed and logged. Keep testing the current build." |
| regression already credited | "that one is already logged." |
| anything else | "could not reproduce with the steps given." |

Under the `fast` protocol used for all results, a confirmed regression stays in the build. The
episode ends when the agent calls `sign_off`, when it stops by itself, or at 300 agent actions
(the cap is not stated to the agent). An action is any tool call, including `file_report` and
`sign_off`. At most 2n+3 reports are accepted, where n counts every planted bug of the episode
(masked ones included); the next report ends the session with outcome `report_cap`. The harness
also ends a session idle for 15 minutes.

## 5. Grading

`dataset_tools/matcher.py`, deterministic, no model. A report is credited to a regression when:

1. **Location**: the key's location concepts match the report's screen, element and field text, or
   `element_ref` resolves to one of the key's anchor elements;
2. **Value gate**: `expected` matches every concept group of the intended behaviour and
   `observed` matches every group of the defect (a group is a list of alternatives matched as whole
   words or word prefixes, so "2" does not match "20");
3. **Grounding**: if the report gives a usable `observed_quote` (two or more characters), it was
   on screen in that session (the harness records every text it displayed); a quote shorter than
   three characters must match a whole token. Numbers claimed as observed are recorded but not
   enforced, because testers write computed values. The quote is optional; the prompt allows a report about something missing to leave
   it out. In the stored results 21 of the 226 credited regressions rest on a report without a
   quote (Sonnet 5, Sol 5, Luna max 6, DeepSeek 3, Luna medium 2, Haiku 0), 12 of them about
   something missing.

Concept alternatives match whole words or word prefixes (`*`); a number matches only as a whole
number ("2" does not match "1.2", "2,000", "10-2" or "-2"; "2,850" matches "2,850.00"). Location
terms must start a word ("edit" matches "editor", not "credit").

`symptom_type` is advisory and breaks ties. One report credits at most one regression: among the
present regressions it matches, one not yet credited is preferred (under the fast protocol a
credited regression stays in the build and keeps matching), then the one whose key it matches with
the most concept groups. Rejected outright: case-copy text, reports
that list many defects, vague reports, `expected` mirrored into `observed`, fields over 500
characters. A report of a regression already credited is a duplicate. Reports of real but unplanted
app behaviour count as false reports.

`aqb audit runs/<name>` re-derives every decision. `tools/rescore_episodes.py` replays a run's
stored reports against the current keys.

### 5.1 Grader validation
- **Blind corpus** (`private/review/scorer/B`): 606 tester-style reports (404 correct, 202 near-miss
  or vague) written, without the keys, by agents shown the buggy and fixed behaviour. The matcher
  credits 84.2% of correct reports and 9.9% of near-miss or vague reports; 3.7% of reports also
  match another bug's key, and none is credited to the wrong regression within its episode
  (`python3 private/review/scorer/score_audit.py private/review/scorer/B`).
- **Screen-grounded corpus** (`private/review/scorer/C`): 606 reports, 101 of each kind. Credited:
  careful reports 94/101, pointing at a neighbouring element 88/101, sloppy prose with the right
  anchor 68/101, vague reports with a real quote 0/101, a near-miss on another element 5/101, and
  **a near-miss on the same element that claims the wrong problem 35/101** (`score_anchored.py`).
  The last rate means a report that names the right element but the wrong defect can be credited.
- **Manual review of rejections**: every report the matcher rejected in the Sonnet and Haiku runs
  (167) was judged by hand against the transcripts: 113 real app behaviour that is not a planted
  regression, 21 agent errors, 17 a different symptom on the right feature, 4 duplicates, 12 (8
  distinct findings) describing a planted regression. The keys of those regressions were widened
  and the Sonnet and Haiku runs were re-scored from their stored reports and transcripts (10
  episodes; net +5 credited regressions for Sonnet and +2 for Haiku). The later runs (Sol, both
  Luna settings, DeepSeek) were graded live with the widened keys. Their rejected reports were not
  reviewed by hand.

## 6. Metrics

Implemented in `tools/leaderboard.py`. For episode e: B = observable regressions, C = credited
ones, F = false reports, s = signed off, k = cut off at the action cap; N = 51 episodes.

- **Recall** = sum |C| / sum |B|.
- **Strict pass** = (1/N) * #episodes with C = B and s.
- **Episode Score** = (1/N) * sum cc(|C|, |B|) * |C| / (|C| + F) * (1/2)^k, where k marks an
  episode cut off at the action cap or the report limit, with catch credit
  cc(c, b) = (1 + (c-1)/2) / (1 + (b-1)/2) for c >= 1 and 0 for c = 0. An agent that ends the
  session itself, with or without `sign_off`, is not cut off.
- **Report precision** = sum |C| / sum (|C| + F); **catch credit** alone; **hit rate** (episodes with
  at least one catch).
- **Endings**: correct sign-off (C = B), sign-off with regressions missed, stopped without
  sign-off, cut off at the action cap, stopped at the report limit (`report_cap`; it also halves the
  Episode Score). A session that ends with a handover that only withholds sign-off because
  confirmed regressions remain in the build counts as a sign-off (`tools/hesitations.py`).
- **Cost**: tokens at API list prices, from the cost line each wrapper in `agents/` writes at the
  end of a session. A DeepSeek Harness session stopped at the action cap ends before that line, so
  its cost is summed from the per-step token usage in the transcript (`tools/leaderboard.py`,
  28 of 51 DeepSeek episodes). One GPT-6 Luna (max) episode stopped the same way has no token
  record; its cost is unknown and the mean is over the other 50. Actions and seconds per episode.
- **Splits**: by app, bug family, and upstream fix date (before or from 2026-01-01).

### 6.1 Changelog coverage
`tools/changelog_coverage.py`, from the transcript, no model. Per release-note line:
*reached* (one of the feature's screen anchors, exact UI strings verified against real
observations in `private/release_notes/screen_anchors.json`, appeared in an observation),
*exercised* (6 or more actions with the feature on screen), *caught* (its regression credited). A
miss is *ignored* (not reached), *shallow* (reached, not exercised) or *tested but not noticed*
(exercised, not caught).

### 6.2 Statistics
The episode is the sampled unit; regressions and reports inside one episode are not independent.

- Intervals: 95% bootstrap over episodes (2,000 resamples) for recall, precision, F1 and the
  Episode Score (`tools/leaderboard.py`); Wilson intervals for per-episode rates (strict pass, hit
  rate) and for the splits by app, family and fix date.
- Differences between configurations: paired sign-flip permutation test over the 51 episodes
  (20,000 permutations), Holm correction over the 15 pairs of each metric
  (`docs/paper/data/analysis.py`, table in `docs/RESULTS.md`). The Luna medium vs max comparison is
  a single planned ablation and is reported uncorrected.
- Each configuration ran each episode once, so the intervals describe the choice of episodes, not
  run-to-run variation. The grouping of episodes by app is not modelled.
- `docs/paper/data/stats_extra.py` adds an episode-cluster bootstrap for recall (10,000
  resamples), exact McNemar tests on discordant regressions, catch overlap against independence
  (hypergeometric) with Jaccard indices, Fisher tests for the fix-date split, Spearman
  correlations, the AUROC of sign-off confidence, and the grounding and rescore sensitivity counts.

## 7. Agent configurations

Each model runs in its vendor's harness at that harness's default reasoning effort, headless, with
built-in tools disabled and only the device server attached. GPT-6 Luna also runs at maximum
effort. All configurations get the same cap, time limit and report limit.

| Configuration | Harness and wrapper | Effort | Episode prompt |
|---|---|---|---|
| Claude Sonnet 5.5 | Claude Code, `agents/claude_agent.sh` | medium (default) | v4 |
| Claude Haiku 5.5 | Claude Code, `agents/claude_agent.sh` | default | v4 |
| GPT-6.1 Sol | Codex CLI, `agents/codex_agent.sh` | low (default) | v4.1 |
| GPT-6 Luna | Codex CLI, `agents/codex_agent.sh` | medium (default) and max | v4.1 |
| DeepSeek V4.1 Flash | DeepSeek Harness, `agents/dsh_agent.sh` + `dsh-lockdown.patch.yml`, under `agents/loop_guard.py` | high | v4 |

Prompt v4 asked agents to sign off when the areas had "no remaining bugs"; under the fast protocol a
reported bug stays in the build, so an agent that had reported one could not sign off truthfully.
v4.1 asks agents to sign off once they have tested the areas and reported every bug they found.
For the v4 runs, a stop that withholds sign-off only because reported bugs remain counts as a
sign-off in the endings (`tools/hesitations.py`), but strict pass needs an actual `sign_off`. The
prompt version is therefore confounded with the configuration for every sign-off metric. The runs
also carry three dataset fingerprints (`run.json`); `tools/rescore_episodes.py --check` reproduces
every stored decision with the current keys.

## 8. Cases

A case (`dataset/cases/<case>/`) is one described check on a clean or a faulty build; the agent
returns PASS, FAIL or INCONCLUSIVE with `submit_verdict`. Clean and faulty cases of a pair share the
same `agent_input.md`. *Specified* cases give the steps and expected result; *unspecified* cases give
the context only. Scored as balanced accuracy (faulty found with a credited failure description,
clean passed) by `tools/leaderboard.py`. The stored results cover episodes only.

## 9. Limits of the current release

- One run per episode per configuration.
- Prompt version (v4 or v4.1) differs between configurations (section 7).
- Each model ran in its vendor's harness, so harness and model are not separated.
- Device checks ran once per build; tasks-0018 depends on the order of equal sort keys and
  featherline-0018 on the device's 12-hour clock.
- Screen anchors are verified for 111 of 185 release-note lines; the others fall back to feature
  words.
- Not yet reviewed by a person who did not write them: 20 random match keys, the episode briefs (for
  leaks), about 20 forward-port patches against their original fixes, and licence terms before
  shipping APKs.
