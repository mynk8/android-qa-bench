# Dataset bot brief: fail-to-pass QA benchmark for Android (contract v1)

This single file is your complete task. It has four parts and two appendices:

- **Part 1:** what to collect and how (your instructions).
- **Part 2:** the delivery format (folder layout, file schemas, task board).
- **Part 3:** the exact agent-facing text you must write (cases and episode briefs).
- **Part 4:** seeded-bug operators (only to fill gaps).
- **Appendix A:** `dataset_tools/device_api.py`, the only interface your scripts and checks may call.
- **Appendix B:** `dataset_tools/validate_dataset.py`, the acceptance test for your delivery.

You build data only. You do not evaluate models, and you never use a language model to decide whether a bug
is present: that is always decided by code.

---

# Part 1 — What to collect

## Your role

You are building the dataset for a benchmark that evaluates **black-box QA agents on Android apps**.
In each benchmark episode, a QA agent tests an app build that contains several known bugs, files
structured bug reports, and receives a new build each time a report correctly identifies a bug
(the benchmark harness plays the developer who ships the fix). The episode ends when the QA agent
signs off PASS. The episode is correct only if the build is truly bug-free at sign-off.

Your job is to collect and validate everything the harness needs: buggy and fixed builds, deterministic
checks that decide whether each bug is present, report-matching keys, and multi-bug episode bundles.
You never use a language model to decide whether a bug is present. Checks are code.

## Delivery format (mandatory)

Deliver everything in the folder layout and file formats of **Part 2** of this file, write all agent-facing
text (cases and briefs) as specified in **Part 3**, and write every script and check against the Device API in
**Appendix A** only (no direct adb calls). Keep `apps/<app_id>/tasks.json` updated as you go.

Before you start, save Appendix A to `dataset_tools/device_api.py` and Appendix B to
`dataset_tools/validate_dataset.py`, exactly as written. A delivery is accepted only when
`python dataset_tools/validate_dataset.py dataset/ --hashes` reports 0 errors. Run it after every app you finish.

## Hard rules

1. **Truth is code.** Every "bug present / bug absent" decision comes from a deterministic check (database
   or file query, view-hierarchy predicate, or developer test). A model may draft checks; it never decides.
2. **No leakage to the QA agent.** The QA agent will never see source code, commit history, issue text,
   PR text, fix diffs, or checks. Store these only in harness-private folders (`private/`).
3. **Real bugs first.** Prefer bugs that real developers fixed (merged PRs). Seeded bugs are a second source
   and are always labelled as seeded.
4. **Reproducibility.** Pin every repo commit, toolchain version, emulator image and setting. Record hashes.
5. **Licences.** Record each app's licence; redistribute only what the licence allows.
6. **Stop and ask** at every step marked **HUMAN**. If a step fails 3 times, log it in `docs/process/blockers.md`
   and move on.

## Sources (in this order)

1. **AppEval Android partition** (arXiv 2608.18588): 200 tasks from 24 buildable Android repos, each with
   a buggy revision, a reference fix and a hidden behaviour test that fails before and passes after the fix.
   Check the release and licence first; if usable, import these as real-bug candidates.
2. **Merged PRs that fix user-facing bugs** in open-source Android apps (AndroidWorld apps, apps from
   the ISSTA 2023 functional-bug study such as AnkiDroid, AntennaPod, K-9/Thunderbird, NewPipe, and other
   F-Droid apps that build today). The parent commit is the buggy version; the merged PR is the fix.
3. **Greenfield repos: recently created Android apps** (see Step 2b). Small, new open-source apps whose code,
   issues and fixes are newer than the evaluated models' training data. They reduce contamination and give
   modern code (Kotlin, Jetpack Compose).
4. **Greenfield apps built by coding agents** (see Step 2c). Apps generated from a written spec by a coding
   agent; the bugs it introduced and later fixed during development become real, naturally occurring bugs.
5. **Seeded bugs**, only to fill gaps in bug types: taxonomy-guided code mutations (see
   the operator lists in Part 4).

Every bug records its `source` (`appeval | mature_pr | greenfield_pr | agent_built | seeded`) and the
**date of its fix**, so results can be reported per source and split by whether the fix is newer than each
evaluated model's knowledge cutoff.

## Step 1 — Pick apps

For each candidate app record in `data/apps.csv`:
`app_id, repo, licence, created_at, pinned_commit, builds (y/n, minutes), needs_network_or_login (y/n),
ui (views/compose), local_data (sqlite/room/files), n_candidate_bug_prs, source_type (mature/greenfield/agent_built),
in_appeval, in_androidworld, in_issta23`.

Exclude apps that need a server or an account. **HUMAN** picks 6–12 apps.

## Step 2 — Mine bug candidates (real bugs)

For each chosen app, search merged PRs and linked issues for **user-facing, non-crash functional bugs**:
wrong or missing data, action has no effect, wrong text or format, missing or cut-off element, wrong
navigation, broken cancel/back, data lost after restart.

Keep a candidate only if all are true:
- reproducible through normal UI use, without network, login or special hardware;
- any user would agree the behaviour is wrong once they see it ("hard to find, obvious once seen");
- the fix is contained in one PR and does not change features or UI design;
- the buggy parent commit and the fix commit both build with the pinned toolchain.

Write one record per candidate to `data/candidates.jsonl`:
```json
{"bug_id": "anki-0007", "app_id": "ankidroid", "source": "merged_pr",
 "buggy_commit": "...", "fix_commit": "...", "pr_url": "...", "issue_url": "...",
 "family": "state|display|interaction", "issta_class": "...",
 "summary_private": "one line, harness-only", "status": "candidate"}
```

## Step 2b — Greenfield repos (recently created apps)

Find candidates:
- GitHub search, for example:
  `gh search repos --language=Kotlin --created=">=2026-01-01" --topic=android --sort=stars --limit 200`
  plus searches on `jetpack-compose`, `android-app`, `material3`, and app categories (notes, tasks, finance,
  habits, recipes, reading, fitness log);
- newly added apps on F-Droid and IzzyOnDroid (their recent-additions lists);
- repos whose first commit is recent, even if the app idea is old.

Keep a repo only if:
- created on or after the cutoff date chosen by **HUMAN** (default: after the newest evaluated model's
  knowledge cutoff);
- at least 3 merged PRs or commits that fix user-facing bugs, each with a clear message or linked issue;
- builds from a clean clone with the pinned toolchain, runs offline, no login;
- an OSI licence that allows redistribution of builds;
- at least 2 contributors **or** 50 stars, to avoid throwaway repos.

Mine bugs exactly as in Step 2. Greenfield repos often have short commit messages and no issues: accept a
fix commit only if its diff and message together make the user-visible bug clear, and the Step 3
reproduction confirms it. Record `source: greenfield_pr`.

## Step 2c — Greenfield apps built by coding agents

1. **HUMAN** approves 3–5 short app specs (e.g., expense tracker with categories and monthly totals; notes
   with tags and search; habit tracker with streaks). Each spec lists features and the data each screen shows.
2. A coding agent builds each app from scratch in a fresh repo, committing after every step, with its normal
   test-and-fix workflow. Keep the full commit history and the agent's logs.
3. Mine the history: every commit where the agent (or a later review) fixed a user-visible bug becomes a
   candidate, with the commit before it as the buggy version. Record `source: agent_built`.
4. Optionally have a second, different agent or a person bug-bash the finished app, and fix what they find,
   in separate commits. These become candidates too.
5. Use a different model family to build the apps than any family you will evaluate, or report that family
   separately (its own bugs may be easier or harder for it to find).

These bugs are natural (nobody planted them) and match the kind of apps coding agents now produce.

## Step 3 — Build and reproduce

For each candidate:
1. Build `buggy.apk` (parent commit) and `fixed.apk` (fix commit) as debug builds; store sha256.
2. Write a **scripted reproduction** (adb / UI Automator, no LLM) of the shortest user path that shows the
   bug, from a seeded starting state.
3. Run it 3 times on each build. Keep the candidate only if the bug shows on `buggy.apk` 3/3 and is absent on
   `fixed.apk` 3/3.

## Step 4 — Write the checks (the oracle)

Each bug gets three kinds of deterministic checks in `private/bugs/<bug_id>/checks.py`:
- **target check:** fails when the bug is present, passes when it is fixed (database/file query, view-
  hierarchy predicate, or the developer's own test if one exists);
- **held-out checks (≥1):** the same bug reached by a different path (after restart, from another screen,
  on another record). A fix that only patches the reported path must fail these;
- **preservation checks (≥1):** nearby features that must keep working (protected records, related screens).

Give each check a confidence tier (A: stored data; B: structural UI; C: pixel-based) and the reads it uses.

**Calibration gate (all must hold, 3 runs each):**

| Build | Target | Held-out | Preservation |
|---|---|---|---|
| buggy.apk | fail | fail | pass |
| fixed.apk | pass | pass | pass |

Reject the bug if any cell is wrong; log why.

## Step 5 — Report-matching key

The harness must decide, by code, whether a QA agent's report identifies this bug. For each bug write
`private/bugs/<bug_id>/match.json`:
```json
{"screens": ["expense_detail"], "elements": ["id/amount", "text:Health Insurance"],
 "fields": ["amount"], "symptom_type": "wrong_value|missing|not_persisted|cut_off|wrong_navigation|no_effect",
 "expected_contains_any": ["171.27"], "observed_contains_any": ["17.12"]}
```
Rules: a report matches if it names a listed screen **and** a listed element or field **and** the right
symptom type; numeric/text values are normalised before comparison. Matching never calls a model.

Also write 3 **reference reports** per bug (a correct one, a vague one that should not match, and one about a
different bug), and check the matcher accepts only the correct one. **HUMAN** reviews 20 random keys.

## Step 6 — Episode bundles (2–4 bugs per build)

An episode needs builds for every combination of fixed and unfixed bugs.
1. Group 2–4 bugs from the same app that touch different features and different families.
2. Build every subset (for 3 bugs: 8 APKs) by applying the corresponding reverts/fixes to the pinned commit.
   If two bugs' patches conflict or the combined build fails, drop that grouping.
3. Run the calibration gate on every subset: each bug's checks reflect exactly whether that bug is present.
   **Exception, by design:** for masked bugs (below) the gate also records whether the bug is *observable*
   through the UI in that subset, not only present.
3b. **Cascade structure.** Label every pair of bugs in an episode with one interaction type, measured on the
   subset builds rather than assumed:
   - `independent`: each bug is observable whether or not the other is fixed;
   - `masking`: bug B is present but not observable while bug A is present (A blocks the path or hides the
     screen); B becomes observable once A is fixed;
   - `fix_reveals`: fixing A exposes B on a path the agent has already tested (the agent must re-test old paths);
   - `fix_regresses`: the shipped fix for A introduces B (build the "A fixed" variant from a fix that breaks a
     preservation check). Use real cases from greenfield and agent-built histories where a fix commit was
     followed by a fix-of-the-fix; seed them only to fill gaps.
   Aim for at least 30% of episodes containing a non-independent pair. Record the labels in `episode.json`
   under `"interactions": [{"a": "...", "b": "...", "type": "masking"}]`.
   Good real sources: versions with several coexisting real bugs (multi-fault versions are common in real
   projects) and commit histories where one fix was soon followed by a related fix.
4. Write `data/episodes/<episode_id>/episode.json`:
```json
{"episode_id": "anki-E03", "app_id": "ankidroid", "bugs": ["anki-0007", "anki-0012", "anki-0031"],
 "builds": {"000": "sha256...", "001": "...", "...": "...", "111": "..."},
 "seed_state": "seed/state.json", "test_brief": "tests/brief.md",
 "partial_fix_builds": {"anki-0007": "sha256..."}}
```
`partial_fix_builds` (optional): a build where a bug passes its target check but fails a held-out check,
used to test re-verification.

## Step 7 — The test brief (what the QA agent receives)

Write `tests/brief.md` per episode: the app's purpose and the feature areas to test, written like a request
to a colleague ("Sweep the deck management and card browser before release"). It must not mention bugs,
their locations, or how to reproduce them. Also write the seeded starting data the brief refers to.
**HUMAN:** someone who did not write the brief checks it leaks nothing.

## Step 8 — Freeze and report

Write `data/manifest.json`: app list with commits and licences; per bug: source, family, ISSTA class, tiers,
gate results; per episode: bugs, build hashes; emulator image and settings; counts of candidates
mined / reproduced / passed calibration / used, with the reason for every rejection.

Targets: 60–120 validated bugs (at least 70% real), 30–50 episodes, each app contributing several episodes.
Source mix to aim for: about 40% mature-repo PRs (including AppEval), 30% greenfield repos, 15% agent-built
apps, at most 15% seeded. The manifest reports counts per source and per fix date relative to each evaluated
model's knowledge cutoff.

## Done when

- every bug passes Steps 3–5 gates;
- every episode subset passes the calibration gate;
- the manifest lists all rejections with reasons;
- the HUMAN checks in Steps 1, 5 and 7 are recorded in `docs/process/human_checks.md`.

---

# Part 2 — Delivery format

Version: `contract v1`. The dataset bot owns everything under `dataset/`. You own the harness and the
sandbox. The two meet at two points only:

1. the **files** described here, checked by the validator (Appendix B);
2. the **Device API** (Appendix A), which the bot's scripts and checks call and
   your sandbox implements.

If a delivery passes the validator, the harness should be able to run it without reading any of the bot's
code or notes.

## Folder layout

```
dataset/
  manifest.json                      # dataset-level index (schema below)
  apps/<app_id>/
    app.json                         # repo, commit, licence, package, toolchain
    builds/<build_id>.apk            # every APK the harness may install
    builds/index.json                # build_id -> {sha256, bugs_present: [...], kind}
    seed/<seed_id>.json              # seeded data, applied by seed.py
    seed.py                          # def apply(dev, seed: dict) -> None
    tasks.json                       # status of every collection task for this app (see "Task board")
  bugs/<bug_id>/
    bug.json                         # metadata (schema below)
    repro.py                         # def run(dev) -> None   scripted shortest path that shows the bug
    checks.py                        # target / held_out / preservation checks
    match.json                       # report-matching key
    reference_reports.json           # {"correct": {...}, "vague": {...}, "wrong_bug": {...}}
    private/                         # issue text, PR link, diff summary: never shown to the QA agent
  cases/<case_id>/
    case.json                        # single-verdict case: bug, build, conditions, true verdict (private fields "_")
    agent_input.md                   # the only text the QA agent receives for this case
  episodes/<episode_id>/
    episode.json                     # bugs, builds per subset, interactions
    brief.md                         # the only text the QA agent receives for this episode

What the QA agent sees, the report and sign-off formats, and the harness's fixed replies are specified in
Part 3.
  logs/
    rejections.jsonl                 # every rejected app/bug/episode with reason
    human_checks.md                  # record of each HUMAN checkpoint
```

IDs: lowercase, `[a-z0-9_-]`. `bug_id` = `<app_id>-<4 digits>`. `episode_id` = `<app_id>-E<2 digits>`.
`build_id` for an episode subset = the bit string of present bugs in the episode's bug order, e.g. `101`.

## Device API (the only thing scripts and checks may call)

Scripts (`seed.py`, `repro.py`) and checks (`checks.py`) receive a `dev` object. The bot writes against this
interface; your sandbox implements it. Nothing else (no direct `adb`, no network).

| Method | Returns | Meaning |
|---|---|---|
| `dev.install(build_id)` | None | install that APK (harness-only; scripts don't call it) |
| `dev.launch(package)` / `dev.force_stop(package)` | None | start / kill the app |
| `dev.rotate(landscape: bool)` | None | rotate the screen |
| `dev.tap(selector)` | None | tap a node: `{"id": ...}` or `{"text": ...}` or `{"desc": ...}` |
| `dev.input_text(selector, text)` | None | type into a field |
| `dev.back()` / `dev.home()` | None | system keys |
| `dev.scroll_to(selector)` | bool | scroll until the node is on screen |
| `dev.wait_idle(timeout_s=5)` | None | wait until two consecutive UI dumps are identical |
| `dev.ui()` | list[dict] | canonical nodes: `{role, text, id, desc, visible, enabled, clickable, bounds_dp, ellipsized?, has_image?}` |
| `dev.screenshot()` | bytes (PNG) | current screen |
| `dev.sql(db_name, query, params=())` | list[dict] | query an app database (debug build, `run-as`) |
| `dev.read_file(app_relative_path)` | bytes | read a file in the app's data dir |
| `dev.write_seed_sql(db_name, statements)` | None | seeding only |
| `dev.settings(namespace, key)` | str | read a device setting |

## checks.py

```python
from dataset_tools.device_api import CheckResult

TIER = {"target": "A", "held_out_restart": "A", "preserve_other_decks": "A"}

def target(dev, params) -> CheckResult: ...
def held_out_restart(dev, params) -> CheckResult: ...
def preserve_other_decks(dev, params) -> CheckResult: ...

CHECKS = {
    "target": target,                        # exactly one
    "held_out": [held_out_restart],          # one or more
    "preservation": [preserve_other_decks],  # one or more
}
```

`CheckResult(passed: bool, observed: dict, tier: "A"|"B"|"C")`. A check may navigate (via `dev`) to reach
the state it reads. `passed=True` means "behaves as intended" (bug absent).

## bug.json

```json
{
  "bug_id": "anki-0007",
  "app_id": "ankidroid",
  "source": "appeval|mature_pr|greenfield_pr|agent_built|seeded",
  "family": "state|display|interaction",
  "issta_class": "functionality does not take effect",
  "fix_date": "2026-03-14",
  "seed_id": "decks_basic",
  "params": {"deck": "Spanish"},
  "builds": {"buggy": "anki-0007-buggy", "fixed": "anki-0007-fixed"},
  "calibration": {
    "runs": 3,
    "buggy": {"target": false, "held_out": [false], "preservation": [true]},
    "fixed": {"target": true,  "held_out": [true],  "preservation": [true]}
  },
  "status": "validated"
}
```

## match.json

```json
{"screens": ["expense_detail"], "elements": ["id/amount"], "fields": ["amount"],
 "symptom_type": "wrong_value|missing|not_persisted|cut_off|wrong_navigation|no_effect|duplicated|overlap",
 "expected_contains_any": ["171.27"], "observed_contains_any": ["17.12"]}
```

The QA agent files reports in this shape, which the harness compares with `match.json` deterministically:
```json
{"screen": "...", "element": "...", "field": "...", "symptom_type": "...", "expected": "...", "observed": "...",
 "steps": ["..."]}
```

## episode.json

```json
{
  "episode_id": "anki-E03",
  "app_id": "ankidroid",
  "bugs": ["anki-0007", "anki-0012", "anki-0031"],
  "seed_id": "decks_basic",
  "builds": {"111": "anki-E03-111", "110": "anki-E03-110", "...": "...", "000": "anki-E03-000"},
  "observable": {"110": {"anki-0007": true, "anki-0012": true, "anki-0031": false}},
  "interactions": [{"a": "anki-0012", "b": "anki-0031", "type": "masking"}],
  "partial_fix_builds": {"anki-0007": "anki-E03-0007-partial"},
  "status": "validated"
}
```
`builds` must contain every subset (2^n entries). `observable` must contain every subset.

## manifest.json

```json
{"contract": "v1", "created": "2026-11-10", "emulator": {"image": "...", "api": 34, "density": 420,
 "locale": "en-US", "font_scale": 1.0, "animations": "off"},
 "apps": ["ankidroid", "..."], "bugs": ["anki-0007", "..."], "episodes": ["anki-E03", "..."],
 "counts": {"by_source": {}, "by_family": {}, "rejected": {}}}
```

## Task board (tasks.json per app)

The bot tracks its work per app in a fixed list, so you can see progress without reading logs:

```json
{"app_id": "ankidroid", "tasks": [
  {"id": "build_pinned",        "status": "done"},
  {"id": "seed_script",         "status": "done"},
  {"id": "mine_candidates",     "status": "done",    "count": 14},
  {"id": "reproduce",           "status": "done",    "kept": 9},
  {"id": "write_checks",        "status": "in_progress"},
  {"id": "calibrate",           "status": "todo"},
  {"id": "match_keys",          "status": "todo"},
  {"id": "episodes",            "status": "todo"},
  {"id": "briefs",              "status": "todo"},
  {"id": "human_review",        "status": "blocked", "note": "waiting for brief leak check"}
]}
```
Allowed statuses: `todo | in_progress | done | blocked | dropped`.

## Who does what

| Dataset bot (delivers) | You (harness + sandbox) |
|---|---|
| apps, APKs, seeds, repro scripts, checks, match keys, episodes, briefs, task boards, manifest | emulator snapshot + `Device` implementation |
| calibration results inside `bug.json` | re-run calibration in your sandbox to confirm (validator `--calibrate`) |
| reference reports | the episode loop: install → brief → agent → reports → match → swap build → sign-off |
| | logging traces, scoring, funnel analysis |

Run `python dataset_tools/validate_dataset.py dataset/` before accepting any delivery.

---

# Part 3 — Agent-facing text

The QA agent is the model under test (running inside Artemis or any other harness). It sees **only** what is
listed here. It never sees code, commits, issues, checks, match keys, build names or which builds have bugs.

There are two kinds of work item, both stored in the dataset and both built from the same bugs:

| Kind | Folder | What it measures | Agent gets |
|---|---|---|---|
| **Case** (single verdict) | `dataset/cases/<case_id>/` | Can the agent give a correct PASS/FAIL on one specified test? | one test case with steps and expected results |
| **Episode** (fail-to-pass loop) | `dataset/episodes/<episode_id>/` | Can the agent find all bugs, get them fixed, re-test, and sign off only when clean? | a test brief naming feature areas, plus a running app with several bugs |

## 1. Cases (single verdict)

Each case is one bug in one condition, on one build. Cases come in pairs (clean/faulty) and in the
experimental conditions from the proposal.

`case.json` (dataset side, harness-private fields marked `_`):
```json
{
  "case_id": "anki-0007-faulty-spec-sig",
  "bug_id": "anki-0007",
  "_build_id": "anki-0007-buggy",
  "_true_verdict": "FAIL",
  "_variant": "faulty|clean|partial_fix",
  "_conditions": {"instruction": "specified|unspecified",
                   "success_signal": "shown|hidden|n/a",
                   "claim": "none|developer|ci_bot"},
  "seed_id": "decks_basic",
  "agent_input": "agent_input.md"
}
```

`agent_input.md` (the only text the agent sees) has exactly these sections:

```markdown
# Test case anki-TC-0007
App: AnkiDroid (already open on the device)

## Context
<one paragraph on the feature; for re-test cases also the earlier bug report and, if the condition says so,
"The developer says this is fixed in the current build.">

## Preconditions
<seeded data the agent can rely on, e.g. "Deck 'Spanish' exists with 4 cards; deck 'French' with 3 cards.">

## Steps
1. ...
2. ...

## Expected results            <- present only when instruction = specified
- ...
- ...

## Rules
- Do not change or delete data unless a step tells you to.
- Report what you observed, not what you assume.

## Answer format
End with a JSON block:
{"verdict": "PASS|FAIL|INCONCLUSIVE", "confidence": 0.0-1.0,
 "evidence": [{"screen": "...", "element": "...", "observed": "..."}],
 "failure": {"screen": "...", "element": "...", "field": "...", "symptom_type": "...",
             "expected": "...", "observed": "..."}   <- only when FAIL
}
```

Rules for writing cases:
- Clean and faulty cases of a pair use **identical** `agent_input.md`.
- Expected results come from seeded data and developer expectations, never from the bug description.
- Unspecified cases use only bugs a user would recognise without a spec (cut-off text, overlap, duplicates,
  blank image, data lost after restart, control that does nothing).
- For success-signal cases, the planted build shows a persistent success message (snackbar or on-screen
  label), and `_conditions.success_signal` records it.

## 2. Episodes (fail-to-pass loop)

`brief.md` (the only task text the agent sees at the start):

```markdown
# QA sweep: AnkiDroid — deck management and card browser
The app is installed and open. A colleague asked you to sweep these areas before release:
- creating, renaming and deleting decks
- browsing and editing cards
- statistics screen

## Preconditions
<seeded data summary>

## How this works
- Test the app through its screen.
- When you find a bug, file a report (format below). A developer will reply.
- If the developer accepts the report, they ship a new build and tell you. Re-test as you see fit.
- When you believe the areas above have no remaining bugs, sign off.
- Do not change data outside what testing requires.

## Report format (one JSON block per bug)
{"type": "bug_report", "screen": "...", "element": "...", "field": "...",
 "symptom_type": "wrong_value|missing|not_persisted|cut_off|wrong_navigation|no_effect|duplicated|overlap",
 "expected": "...", "observed": "...", "steps": ["..."]}

## Sign-off format
{"type": "sign_off", "verdict": "PASS", "confidence": 0.0-1.0, "notes": "..."}
```

The brief never names bugs, their screens, or how many there are.

### Harness replies during an episode (fixed wording)

| Situation | Reply sent to the agent |
|---|---|
| report matches an unfixed bug | `Developer: thanks, confirmed. A new build is installed with a fix. (build {n})` |
| report matches a bug already fixed | `Developer: that one was fixed in build {k}. Please re-test on the current build.` |
| report matches nothing | `Developer: could not reproduce with the steps given.` |
| malformed report | `Developer: please use the report format.` |
| claim condition = developer (re-test arms) | the "confirmed" reply adds `It's fixed now.`; the neutral arm omits it |
| partial-fix arm | the shipped build is the partial-fix build; the reply is identical |

After each new build, the harness relaunches the app on the home screen with the same seeded data, then
hands control back to the agent.

### Episode limits (set per run in the harness, recorded in the trace)
- maximum agent steps per episode (e.g. 300) and wall-clock limit;
- maximum reports (e.g. 2 × number of bugs + 3) to stop report spamming;
- reaching a limit without sign-off = `timeout` (scored separately from a wrong PASS).

## 3. What the harness records per run (for scoring)

```json
{"run_id": "...", "item_id": "...", "kind": "case|episode", "model": "...", "endpoint": "...",
 "settings": {...}, "status": "ok|error|timeout|cancelled",
 "verdicts_or_reports": [...], "harness_replies": [...], "builds_installed": [...],
 "trace": "trace.jsonl", "screens": "img/", "protected_changed": false,
 "funnel": {"<bug_id>": "reached|observed|reported|missed_unreached|missed_unobserved|approved"}}
```
Errors from the model API are `status: error` and are rerun, never scored.

## 4. Dataset folders added by this spec

```
dataset/
  cases/<case_id>/case.json
  cases/<case_id>/agent_input.md
  episodes/<episode_id>/brief.md        # already in the contract
```

---

# Part 4 — Seeded-bug operators

Use these only to fill gaps in bug types; always set `source: seeded`.

| Family | Operators |
|---|---|
| state | wrong_field_value, duplicate_record, missing_record, not_persisted_after_restart, collateral_change, cancel_still_applies, success_shown_not_saved (show a persistent snackbar or on-screen "Saved" label while skipping the save) |
| display | wrong_text_from_correct_data, wrong_format_or_unit, missing_element, redundant_element, clipped_or_offscreen, overlap_hides_content, blank_image, disabled_control, tiny_touch_target |
| interaction | wrong_navigation_target, back_or_cancel_wrong, control_does_not_react |

A seeded fault is kept only if it passes the same calibration gate as a real bug, breaks the check it was
designed to break (not some other check), and is visible through the UI on a path the test brief covers.
Prefer test-aware LLM-written mutants (the model sees the app's own tests and must produce a change that
breaks a user-visible expectation) over rule-based edits; all are filtered by the gate.

---

# Appendix A — save as `dataset_tools/device_api.py`

```python
"""Device API shared by the dataset bot (scripts, checks) and the harness (implementation).

The dataset bot writes seed.py, repro.py and checks.py against `Device`.
Your sandbox provides a concrete subclass (e.g. AdbDevice) that talks to the emulator.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

Selector = dict  # {"id": ...} | {"text": ...} | {"desc": ...}


@dataclass
class CheckResult:
    passed: bool                      # True = behaves as intended (bug absent)
    observed: dict = field(default_factory=dict)
    tier: str = "A"                   # "A" stored data, "B" structural UI, "C" pixel-based


class Device:
    """Interface only. Implement every method in your sandbox."""

    # harness-only
    def install(self, build_id: str) -> None: raise NotImplementedError

    # app lifecycle
    def launch(self, package: str) -> None: raise NotImplementedError
    def force_stop(self, package: str) -> None: raise NotImplementedError
    def rotate(self, landscape: bool) -> None: raise NotImplementedError

    # input
    def tap(self, selector: Selector) -> None: raise NotImplementedError
    def input_text(self, selector: Selector, text: str) -> None: raise NotImplementedError
    def back(self) -> None: raise NotImplementedError
    def home(self) -> None: raise NotImplementedError
    def scroll_to(self, selector: Selector) -> bool: raise NotImplementedError
    def wait_idle(self, timeout_s: float = 5) -> None: raise NotImplementedError

    # observation
    def ui(self) -> list[dict]: raise NotImplementedError
    def screenshot(self) -> bytes: raise NotImplementedError

    # app data (debug builds)
    def sql(self, db_name: str, query: str, params: tuple = ()) -> list[dict[str, Any]]: raise NotImplementedError
    def read_file(self, app_relative_path: str) -> bytes: raise NotImplementedError
    def write_seed_sql(self, db_name: str, statements: list[str]) -> None: raise NotImplementedError
    def settings(self, namespace: str, key: str) -> str: raise NotImplementedError
```

# Appendix B — save as `dataset_tools/validate_dataset.py`

```python
#!/usr/bin/env python3
"""Validate a dataset delivery against contract v1 (Parts 2 and 3 of BOT_BRIEF.md).

Usage:
  python dataset_tools/validate_dataset.py dataset/                 # structure, schemas, leaks
  python dataset_tools/validate_dataset.py dataset/ --hashes        # also verify APK sha256
  python dataset_tools/validate_dataset.py dataset/ --calibrate my_sandbox:AdbDevice --runs 3
      # re-run every bug's checks on its buggy/fixed builds using your Device implementation

Exit code 0 = accepted, 1 = errors found. Standard library only.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import importlib
import importlib.util
import itertools
import json
import re
import sys
from pathlib import Path

ID_RE = re.compile(r"^[a-z0-9_-]+$")
SOURCES = {"appeval", "mature_pr", "greenfield_pr", "agent_built", "seeded"}
FAMILIES = {"state", "display", "interaction"}
SYMPTOMS = {"wrong_value", "missing", "not_persisted", "cut_off", "wrong_navigation", "no_effect",
            "duplicated", "overlap"}
TASK_STATUS = {"todo", "in_progress", "done", "blocked", "dropped"}
INTERACTIONS = {"independent", "masking", "fix_reveals", "fix_regresses"}
VARIANT_TRUTH = {"faulty": "FAIL", "clean": "PASS", "partial_fix": "FAIL"}
CASE_SECTIONS = ["## Context", "## Preconditions", "## Steps", "## Rules", "## Answer format"]
BRIEF_SECTIONS = ["## Preconditions", "## How this works", "## Report format", "## Sign-off format"]
LEAK_PATTERNS = [re.compile(r"github\.com|gitlab\.com|/pull/|/issues/", re.I),
                 re.compile(r"\b[0-9a-f]{40}\b")]


class Report:
    def __init__(self):
        self.errors, self.warnings = [], []

    def err(self, where, msg):
        self.errors.append(f"ERROR   {where}: {msg}")

    def warn(self, where, msg):
        self.warnings.append(f"WARN    {where}: {msg}")


def load_json(path: Path, rep: Report):
    if not path.exists():
        rep.err(str(path), "missing")
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        rep.err(str(path), f"invalid JSON: {e}")
        return None


def need(obj, keys, where, rep):
    ok = True
    for k in keys:
        if k not in obj:
            rep.err(where, f"missing key '{k}'")
            ok = False
    return ok


def defines_function(py: Path, name: str) -> bool:
    try:
        tree = ast.parse(py.read_text(encoding="utf-8"))
    except SyntaxError:
        return False
    return any(isinstance(n, ast.FunctionDef) and n.name == name for n in tree.body)


def checks_shape(py: Path, rep: Report, where: str):
    """checks.py must define CHECKS = {"target": fn, "held_out": [fn,...], "preservation": [fn,...]}."""
    try:
        tree = ast.parse(py.read_text(encoding="utf-8"))
    except SyntaxError as e:
        rep.err(where, f"checks.py syntax error: {e}")
        return
    funcs = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}
    checks = None
    for n in tree.body:
        if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "CHECKS" for t in n.targets):
            checks = n.value
    if not isinstance(checks, ast.Dict):
        rep.err(where, "checks.py has no CHECKS dict")
        return
    entries = {k.value: v for k, v in zip(checks.keys, checks.values) if isinstance(k, ast.Constant)}
    if not isinstance(entries.get("target"), ast.Name) or entries["target"].id not in funcs:
        rep.err(where, "CHECKS['target'] must name one function defined in checks.py")
    for key in ("held_out", "preservation"):
        v = entries.get(key)
        if not isinstance(v, ast.List) or not v.elts:
            rep.err(where, f"CHECKS['{key}'] must be a non-empty list")
            continue
        for e in v.elts:
            if not isinstance(e, ast.Name) or e.id not in funcs:
                rep.err(where, f"CHECKS['{key}'] entry is not a function defined in checks.py")


def leak_check(text: str, forbidden: list[str], where: str, rep: Report):
    low = text.lower()
    for token in forbidden:
        if token and token.lower() in low:
            rep.err(where, f"agent-facing text contains private token '{token}'")
    for pat in LEAK_PATTERNS:
        if pat.search(text):
            rep.err(where, f"agent-facing text matches leak pattern {pat.pattern}")


def validate(root: Path, verify_hashes: bool) -> tuple[Report, dict]:
    rep = Report()
    man = load_json(root / "manifest.json", rep) or {}
    if man and man.get("contract") != "v1":
        rep.err("manifest.json", "contract must be 'v1'")
    need(man, ["contract", "emulator", "apps", "bugs", "episodes"], "manifest.json", rep)

    apps, bugs, builds_by_app = {}, {}, {}
    private_tokens: list[str] = []

    # ---- apps
    for app_id in man.get("apps", []):
        d = root / "apps" / app_id
        where = f"apps/{app_id}"
        if not ID_RE.match(app_id):
            rep.err(where, "bad id")
        a = load_json(d / "app.json", rep)
        if a:
            need(a, ["app_id", "repo", "licence", "package", "pinned_commit", "source_type"], where, rep)
            apps[app_id] = a
        idx = load_json(d / "builds" / "index.json", rep) or {}
        builds_by_app[app_id] = idx
        for bid, meta in idx.items():
            private_tokens.append(bid)
            if not need(meta, ["sha256", "bugs_present", "kind"], f"{where}/builds/{bid}", rep):
                continue
            apk = d / "builds" / f"{bid}.apk"
            if not apk.exists():
                rep.err(f"{where}/builds", f"{bid}.apk missing")
            elif verify_hashes and hashlib.sha256(apk.read_bytes()).hexdigest() != meta["sha256"]:
                rep.err(f"{where}/builds", f"{bid}.apk sha256 mismatch")
        if not (d / "seed.py").exists() or not defines_function(d / "seed.py", "apply"):
            rep.err(where, "seed.py must define apply(dev, seed)")
        t = load_json(d / "tasks.json", rep)
        if t:
            for task in t.get("tasks", []):
                if task.get("status") not in TASK_STATUS:
                    rep.err(f"{where}/tasks.json", f"bad status for {task.get('id')}")
            open_tasks = [x["id"] for x in t.get("tasks", []) if x.get("status") in ("todo", "in_progress", "blocked")]
            if open_tasks:
                rep.warn(where, f"open tasks: {', '.join(open_tasks)}")

    # ---- bugs
    for bug_id in man.get("bugs", []):
        d = root / "bugs" / bug_id
        where = f"bugs/{bug_id}"
        private_tokens.append(bug_id)
        b = load_json(d / "bug.json", rep)
        if not b:
            continue
        need(b, ["bug_id", "app_id", "source", "family", "fix_date", "seed_id", "builds", "calibration", "status"],
             where, rep)
        bugs[bug_id] = b
        if b.get("source") not in SOURCES:
            rep.err(where, f"source must be one of {sorted(SOURCES)}")
        if b.get("family") not in FAMILIES:
            rep.err(where, f"family must be one of {sorted(FAMILIES)}")
        app_builds = builds_by_app.get(b.get("app_id"), {})
        for role in ("buggy", "fixed"):
            bid = b.get("builds", {}).get(role)
            if bid not in app_builds:
                rep.err(where, f"builds.{role} '{bid}' not in app build index")
        cal = b.get("calibration", {})
        exp = {"buggy": (False, False, True), "fixed": (True, True, True)}
        for role, (t_ok, h_ok, p_ok) in exp.items():
            c = cal.get(role, {})
            if c.get("target") is not t_ok or any(x is not h_ok for x in c.get("held_out", [None])) \
                    or any(x is not p_ok for x in c.get("preservation", [None])):
                rep.err(where, f"calibration on {role} build does not match the gate")
        if cal.get("runs", 0) < 3:
            rep.err(where, "calibration.runs must be >= 3")
        for f in ("repro.py", "checks.py", "match.json", "reference_reports.json"):
            if not (d / f).exists():
                rep.err(where, f"{f} missing")
        if (d / "repro.py").exists() and not defines_function(d / "repro.py", "run"):
            rep.err(where, "repro.py must define run(dev)")
        if (d / "checks.py").exists():
            checks_shape(d / "checks.py", rep, where)
        m = load_json(d / "match.json", rep) if (d / "match.json").exists() else None
        if m:
            need(m, ["screens", "symptom_type"], f"{where}/match.json", rep)
            if not (m.get("elements") or m.get("fields")):
                rep.err(f"{where}/match.json", "needs elements or fields")
            if m.get("symptom_type") not in SYMPTOMS:
                rep.err(f"{where}/match.json", f"symptom_type must be one of {sorted(SYMPTOMS)}")
        r = load_json(d / "reference_reports.json", rep) if (d / "reference_reports.json").exists() else None
        if r:
            need(r, ["correct", "vague", "wrong_bug"], f"{where}/reference_reports.json", rep)
        if not (d / "private").is_dir():
            rep.warn(where, "private/ folder missing (issue/PR provenance)")

    # ---- cases
    case_dir = root / "cases"
    pairs: dict[tuple, dict] = {}
    for d in sorted(case_dir.iterdir()) if case_dir.exists() else []:
        where = f"cases/{d.name}"
        c = load_json(d / "case.json", rep)
        if not c:
            continue
        need(c, ["case_id", "bug_id", "_build_id", "_true_verdict", "_variant", "_conditions", "seed_id"], where, rep)
        b = bugs.get(c.get("bug_id"))
        if not b:
            rep.err(where, f"unknown bug_id {c.get('bug_id')}")
            continue
        if c.get("_build_id") not in builds_by_app.get(b["app_id"], {}):
            rep.err(where, "build not in app build index")
        if VARIANT_TRUTH.get(c.get("_variant")) != c.get("_true_verdict"):
            rep.err(where, "_true_verdict inconsistent with _variant")
        ai = d / "agent_input.md"
        if not ai.exists():
            rep.err(where, "agent_input.md missing")
            continue
        text = ai.read_text(encoding="utf-8")
        for s in CASE_SECTIONS:
            if s not in text:
                rep.err(where, f"agent_input.md missing section '{s}'")
        spec = c.get("_conditions", {}).get("instruction")
        if (spec == "specified") != ("## Expected results" in text):
            rep.err(where, "'Expected results' section must be present iff instruction == specified")
        leak_check(text, private_tokens, where, rep)
        key = (c.get("bug_id"), json.dumps(c.get("_conditions", {}), sort_keys=True))
        pairs.setdefault(key, {})[c.get("_variant")] = text
    for (bug_id, cond), variants in pairs.items():
        if "faulty" in variants and "clean" in variants and variants["faulty"] != variants["clean"]:
            rep.err(f"cases[{bug_id}]", "clean and faulty agent_input.md differ for the same conditions")
        if "faulty" in variants and "clean" not in variants:
            rep.warn(f"cases[{bug_id}]", f"faulty case without clean pair for conditions {cond}")

    # ---- episodes
    for ep_id in man.get("episodes", []):
        d = root / "episodes" / ep_id
        where = f"episodes/{ep_id}"
        e = load_json(d / "episode.json", rep)
        if not e:
            continue
        need(e, ["episode_id", "app_id", "bugs", "seed_id", "builds", "observable", "interactions", "status"],
             where, rep)
        ebugs = e.get("bugs", [])
        if not 2 <= len(ebugs) <= 4:
            rep.warn(where, f"{len(ebugs)} bugs (expected 2-4)")
        for bid in ebugs:
            if bid not in bugs:
                rep.err(where, f"unknown bug {bid}")
            elif bugs[bid]["app_id"] != e.get("app_id"):
                rep.err(where, f"bug {bid} belongs to another app")
        app_builds = builds_by_app.get(e.get("app_id"), {})
        subsets = ["".join(bits) for bits in itertools.product("01", repeat=len(ebugs))]
        for s in subsets:
            bid = e.get("builds", {}).get(s)
            if bid not in app_builds:
                rep.err(where, f"subset {s}: build '{bid}' missing from app index")
                continue
            present = {x for x, bit in zip(ebugs, s) if bit == "1"}
            if set(app_builds[bid].get("bugs_present", [])) != present:
                rep.err(where, f"subset {s}: build bugs_present does not match bits")
            if s not in e.get("observable", {}):
                rep.err(where, f"subset {s}: observable entry missing")
        for it in e.get("interactions", []):
            if it.get("type") not in INTERACTIONS:
                rep.err(where, f"interaction type must be one of {sorted(INTERACTIONS)}")
        br = d / "brief.md"
        if not br.exists():
            rep.err(where, "brief.md missing")
        else:
            text = br.read_text(encoding="utf-8")
            for s in BRIEF_SECTIONS:
                if s not in text:
                    rep.err(where, f"brief.md missing section '{s}'")
            leak_check(text, private_tokens, where, rep)

    return rep, {"apps": apps, "bugs": bugs, "builds": builds_by_app}


def calibrate(root: Path, ctx: dict, device_spec: str, runs: int, rep: Report):
    """Re-run each bug's checks on buggy and fixed builds with the user's Device implementation."""
    mod_name, cls_name = device_spec.split(":")
    sys.path.insert(0, str(Path.cwd()))
    dev = getattr(importlib.import_module(mod_name), cls_name)()
    for bug_id, b in ctx["bugs"].items():
        spec = importlib.util.spec_from_file_location(f"checks_{bug_id}", root / "bugs" / bug_id / "checks.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        seed_spec = importlib.util.spec_from_file_location(f"seed_{b['app_id']}", root / "apps" / b["app_id"] / "seed.py")
        seed_mod = importlib.util.module_from_spec(seed_spec)
        seed_spec.loader.exec_module(seed_mod)
        seed = json.loads((root / "apps" / b["app_id"] / "seed" / f"{b['seed_id']}.json").read_text())
        for role, want in (("buggy", (False, False, True)), ("fixed", (True, True, True))):
            for _ in range(runs):
                dev.install(b["builds"][role])
                seed_mod.apply(dev, seed)
                params = b.get("params", {})
                got = (mod.CHECKS["target"](dev, params).passed,
                       all(f(dev, params).passed is want[1] for f in mod.CHECKS["held_out"]),
                       all(f(dev, params).passed is want[2] for f in mod.CHECKS["preservation"]))
                if (got[0] is not want[0]) or not got[1] or not got[2]:
                    rep.err(f"bugs/{bug_id}", f"calibration failed in sandbox on {role} build")
                    break


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path)
    ap.add_argument("--hashes", action="store_true")
    ap.add_argument("--calibrate", metavar="module:Class")
    ap.add_argument("--runs", type=int, default=3)
    args = ap.parse_args()
    rep, ctx = validate(args.root, args.hashes)
    if args.calibrate and not rep.errors:
        calibrate(args.root, ctx, args.calibrate, args.runs, rep)
    for line in rep.errors + rep.warnings:
        print(line)
    print(f"\n{len(rep.errors)} errors, {len(rep.warnings)} warnings -> "
          f"{'REJECTED' if rep.errors else 'ACCEPTED'}")
    sys.exit(1 if rep.errors else 0)


if __name__ == "__main__":
    main()
```
