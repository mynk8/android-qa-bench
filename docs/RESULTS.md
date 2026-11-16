# Results

Six agent configurations on all 51 episodes, one run each. Every number here is computed from
`results/` by the scripts in `docs/paper/data/` (`collect.py`, `analysis.py`, `hard_core.py`,
then `write_results_md.py`). Definitions: [METHODOLOGY.md](METHODOLOGY.md), section 6.

## Main results

| Configuration | Recall % | Strict pass % | Precision % | Episode Score | Catch credit | Actions / ep | Minutes / ep | $ / ep |
|---|---|---|---|---|---|---:|---:|---:|
| GPT-6.1 Sol (low) | 59.3 [50.0, 68.5] | 29.4 [18.7, 43.0] | 34.0 [28.3, 40.3] | 0.289 [0.22, 0.36] | 0.66 | 202 | 7.4 | 0.649 |
| DeepSeek V4.1 Flash (high) | 50.5 [40.0, 60.4] | 11.8 [5.5, 23.4] | 34.1 [27.1, 41.5] | 0.183 [0.12, 0.25] | 0.54 | 294 | 20.7 | 0.061 |
| Claude Sonnet 5.5 (medium) | 46.2 [36.3, 55.7] | 23.5 [14.0, 36.8] | 44.2 [33.0, 56.6] | 0.390 [0.29, 0.50] | 0.50 | 67 | 2.9 | 0.539 |
| Claude Haiku 5.5 | 42.9 [31.1, 53.9] | 13.7 [6.8, 25.7] | 27.7 [19.8, 36.4] | 0.237 [0.16, 0.32] | 0.47 | 217 | 5.5 | 0.637 |
| GPT-6 Luna (max) | 34.1 [23.9, 44.0] | 11.8 [5.5, 23.4] | 24.4 [16.2, 33.3] | 0.209 [0.13, 0.29] | 0.35 | 166 | 16.0 | 0.156 (50/51 logged) |
| GPT-6 Luna (medium) | 15.4 [8.6, 23.2] | 3.9 [1.1, 13.2] | 50.0 [34.5, 67.6] | 0.144 [0.07, 0.22] | 0.18 | 39 | 2.2 | 0.015 |

Recall counts the 91 observable regressions; credited and false reports per configuration:

| Configuration | Credited | False | Reports filed |
|---|---:|---:|---:|
| GPT-6.1 Sol (low) | 54 | 105 | 164 |
| DeepSeek V4.1 Flash (high) | 46 | 89 | 146 |
| Claude Sonnet 5.5 (medium) | 42 | 53 | 99 |
| Claude Haiku 5.5 | 39 | 102 | 147 |
| GPT-6 Luna (max) | 31 | 96 | 130 |
| GPT-6 Luna (medium) | 14 | 14 | 28 |

## How episodes ended

| Configuration | Correct sign-off | Signed off, regressions missed | Stopped, no sign-off | Cut off at 300 actions | Stopped at report limit |
|---|---:|---:|---:|---:|---:|
| GPT-6.1 Sol (low) | 29% | 55% | 2% | 14% | 0% |
| DeepSeek V4.1 Flash (high) | 12% | 6% | 0% | 78% | 4% |
| Claude Sonnet 5.5 (medium) | 24% | 76% | 0% | 0% | 0% |
| Claude Haiku 5.5 | 18% | 26% | 35% | 22% | 0% |
| GPT-6 Luna (max) | 12% | 84% | 0% | 2% | 2% |
| GPT-6 Luna (medium) | 4% | 90% | 6% | 0% | 0% |

Sign-off confidence reported by the agent, by whether every regression had been reported:

| Configuration | Mean confidence, correct (n) | Mean confidence, regressions missed (n) | Actions at sign-off with regressions missed |
|---|---|---|---:|
| GPT-6.1 Sol (low) | 0.84 (15) | 0.82 (28) | 182.2 |
| DeepSeek V4.1 Flash (high) | 0.81 (6) | 0.81 (3) | 251.7 |
| Claude Sonnet 5.5 (medium) | 0.49 (12) | 0.47 (39) | 69.9 |
| Claude Haiku 5.5 | 0.49 (7) | 0.52 (12) | 195.9 |
| GPT-6 Luna (max) | 0.92 (6) | 0.89 (43) | 165.2 |
| GPT-6 Luna (medium) | 0.77 (2) | 0.76 (46) | 39.6 |

## Sol and Sonnet, paired by episode

- Per-episode recall, Sol minus Sonnet: +0.154 (95% CI +0.023 to +0.284).
- Sol caught more in 17 episodes, Sonnet in 7, tie in 27.
- Regressions caught by both 32, only Sol 22, only Sonnet 10, neither 27.
- Over all six configurations: 74 of 91 observable regressions caught at least once; 17 caught by none.

## Changelog coverage (92 release-note lines that hide a regression)

| Configuration | Reached | Exercised (6+ actions) | Caught | Ignored | Shallow | Tested, not noticed | Caught with a short look | Decoys reached / exercised |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| GPT-6.1 Sol (low) | 88 | 68 | 54 | 0 | 9 | 29 | 15 | 92 / 85 of 93 |
| DeepSeek V4.1 Flash (high) | 87 | 79 | 46 | 0 | 3 | 43 | 10 | 92 / 87 of 93 |
| Claude Sonnet 5.5 (medium) | 78 | 44 | 42 | 6 | 19 | 25 | 23 | 85 / 56 of 93 |
| Claude Haiku 5.5 | 83 | 72 | 39 | 4 | 6 | 43 | 10 | 87 / 81 of 93 |
| GPT-6 Luna (max) | 82 | 66 | 31 | 5 | 10 | 46 | 11 | 89 / 77 of 93 |
| GPT-6 Luna (medium) | 68 | 27 | 14 | 20 | 35 | 23 | 10 | 76 / 30 of 93 |

## Pairwise differences

Paired sign-flip permutation test over the 51 episodes (20,000 permutations); Holm correction over
the 15 pairs of each metric. Difference = first minus second configuration, per-episode mean.

| Pair | Recall diff | p (Holm) | Strict pass diff | p (Holm) | Episode Score diff | p (Holm) |
|---|---:|---:|---:|---:|---:|---:|
| Claude Sonnet 5.5 (medium) vs GPT-6 Luna (medium) | +0.288 | 0.001 * | +0.196 | 0.084 | +0.246 | 0.006 * |
| GPT-6.1 Sol (low) vs GPT-6 Luna (max) | +0.294 | 0.001 * | +0.176 | 0.313 | +0.081 | 0.674 |
| GPT-6.1 Sol (low) vs GPT-6 Luna (medium) | +0.441 | 0.001 * | +0.255 | 0.015 * | +0.145 | 0.026 * |
| DeepSeek V4.1 Flash (high) vs GPT-6 Luna (medium) | +0.327 | 0.001 * | +0.078 | 1.000 | +0.039 | 1.000 |
| Claude Haiku 5.5 vs GPT-6 Luna (medium) | +0.278 | 0.001 * | +0.098 | 0.630 | +0.093 | 0.656 |
| GPT-6 Luna (max) vs DeepSeek V4.1 Flash (high) | -0.180 | 0.011 * | +0.000 | 1.000 | +0.026 | 1.000 |
| GPT-6.1 Sol (low) vs Claude Haiku 5.5 | +0.163 | 0.057 | +0.157 | 0.630 | +0.052 | 1.000 |
| Claude Sonnet 5.5 (medium) vs GPT-6 Luna (max) | +0.141 | 0.061 | +0.118 | 0.984 | +0.181 | 0.004 * |
| GPT-6 Luna (max) vs GPT-6 Luna (medium) | +0.147 | 0.065 | +0.078 | 1.000 | +0.064 | 1.000 |
| Claude Haiku 5.5 vs GPT-6 Luna (max) | +0.131 | 0.165 | +0.020 | 1.000 | +0.029 | 1.000 |
| Claude Sonnet 5.5 (medium) vs GPT-6.1 Sol (low) | -0.154 | 0.165 | -0.059 | 1.000 | +0.100 | 0.656 |
| GPT-6.1 Sol (low) vs DeepSeek V4.1 Flash (high) | +0.114 | 0.433 | +0.176 | 0.437 | +0.107 | 0.237 |
| Claude Haiku 5.5 vs DeepSeek V4.1 Flash (high) | -0.049 | 1.000 | +0.020 | 1.000 | +0.054 | 0.848 |
| Claude Sonnet 5.5 (medium) vs DeepSeek V4.1 Flash (high) | -0.039 | 1.000 | +0.118 | 0.984 | +0.207 | 0.001 * |
| Claude Sonnet 5.5 (medium) vs Claude Haiku 5.5 | +0.010 | 1.000 | +0.098 | 1.000 | +0.153 | 0.058 |

\* significant at 0.05 after Holm correction.

## Use of the actions the QA method calls for

Episodes (of 51) with at least one such action; `open_app` only (re-opening a file inside the app is not counted).

| Configuration | Rotate | Re-open app | Long-press | Type text |
|---|---:|---:|---:|---:|
| GPT-6.1 Sol (low) | 51 | 27 | 7 | 51 |
| DeepSeek V4.1 Flash (high) | 49 | 29 | 36 | 48 |
| Claude Sonnet 5.5 (medium) | 23 | 13 | 16 | 34 |
| Claude Haiku 5.5 | 51 | 29 | 21 | 40 |
| GPT-6 Luna (max) | 51 | 14 | 30 | 46 |
| GPT-6 Luna (medium) | 44 | 6 | 15 | 23 |

## Recall by app, family and fix date

| App | GPT-6.1 Sol (low) | DeepSeek V4.1 Flash (high) | Claude Sonnet 5.5 (medium) | Claude Haiku 5.5 | GPT-6 Luna (max) | GPT-6 Luna (medium) |
|---|---:|---:|---:|---:|---:|---:|
| amaze (11) | 6 | 7 | 3 | 3 | 5 | 0 |
| ankidroid (15) | 7 | 6 | 8 | 6 | 6 | 0 |
| featherline (9) | 2 | 3 | 4 | 1 | 0 | 0 |
| idlefantasy (12) | 7 | 6 | 3 | 3 | 3 | 5 |
| iris (3) | 2 | 2 | 0 | 2 | 0 | 0 |
| markor (13) | 7 | 9 | 8 | 7 | 6 | 2 |
| minus (8) | 6 | 2 | 3 | 4 | 1 | 1 |
| nerdcalci (8) | 8 | 7 | 7 | 8 | 6 | 5 |
| tasks (12) | 9 | 4 | 6 | 5 | 4 | 1 |
| family: display (35) | 22 | 19 | 18 | 17 | 12 | 9 |
| family: interaction (19) | 11 | 8 | 7 | 8 | 6 | 2 |
| family: state (37) | 21 | 19 | 17 | 14 | 13 | 3 |
| fixed before 2026 (33) | 19 | 16 | 17 | 14 | 14 | 3 |
| fixed in 2026 (58) | 35 | 30 | 25 | 25 | 17 | 11 |

## Regressions both Sol and Sonnet missed (27)

Grouped by what a tester must do to expose them. *Caught by*: other configurations that caught it.
*Most actions*: the most actions any of Sonnet, Sol, Haiku or DeepSeek spent with the feature on screen.

### Needs round trip: change, leave and reopen, check it was kept (6)

| Bug | Release-note line | Defect | Caught by | Most actions |
|---|---|---|---|---:|
| ankidroid-0007 | Add note deck chooser: its initial deck is now loaded from the deck list's current choice. | expected the deck chosen for a new note is remembered the next time the editor opens; observed the deck for new cards is not saved | none | 11 |
| ankidroid-0023 | Timebox settings: the minutes field is now resolved from the collection's on/off state when the screen opens. | expected after switching the timebox off and on again the limit shows 21, the value set before; observed the limit goes back to the default 20 after the timebox was switched off and on | haiku | 26 |
| featherline-0005 | Preparation form picker: every amount field is now carried over when the form is changed. | expected switching preparation type and back clears the previous dose value; observed switching back resurrects the previously typed dose value | none | 121 |
| markor-0018 | Editor overflow menu typing helpers: their toggles are now applied directly to the open editor session. | expected after reopening the file auto-format is still off and Enter adds no list marker; observed after reopening the file auto-format is on again and Enter adds a '- ' marker | none | 15 |
| markor-0019 | Editor tab width dialog: the chosen width is now applied directly to the editor that is open. | expected after reopening the file Indent still adds two spaces, so the line has four spaces; observed after reopening the file Indent adds four spaces, so the line has six spaces | none | 5 |
| minus-0007 | Budget sheet split view selector: the active view is now stored in view-model memory. | expected Weekly is still the selected option after the app is closed and opened again; observed after closing and reopening the app the selection is back to Daily | none | 31 |

### Needs a specific input or action (10)

| Bug | Release-note line | Defect | Caught by | Most actions |
|---|---|---|---|---:|
| amaze-0011 | Bookmarks page in Settings: a new entry is now compared with stored ones on title and location together. | expected a second bookmark to the same path is rejected; observed Docs2 is added for the same path | none | 78 |
| amaze-0015 | Multi-file overflow menu: the bulk-marking entry is now handled as an on/off toggle of the current state. | expected all items remain selected after choosing Select All a second time; observed choosing Select All again deselects all items and the selection bar closes | none | 5 |
| amaze-0016 | Batch overflow menu: the invert-marking entry is now handled entirely inside the list adapter. | expected the selection action bar closes when select inverse leaves nothing selected; observed the selection action bar stays open with 0 selected | deepseek | 5 |
| amaze-0019 | Retitling prompt: input validation for files and folders is now handled by a consolidated validator. | expected a notice says no changes will be made because the new name matches the old name; observed no notice or warning appears when typing the same name | deepseek | 24 |
| ankidroid-0027 | Deck retitling dialog: the clash check with other decks is now computed by comparing text instead of identifiers. | expected French can be renamed to FRENCH and the deck list shows FRENCH; observed the name field reports that the deck already exists and Rename does nothing | haiku | 18 |
| ankidroid-0030 | Set due date dialog: the day and range inputs are now handled by a common text-input component. | expected typing 1234567 leaves 12345 in the field because only five digits are allowed; observed the field accepts all seven digits, 1234567 | none | 25 |
| featherline-0016 | Settings measurement editor: submitted text is now parsed by a single number parser for every input. | expected saving the empty field clears the weight and closes the sheet; observed an error asks for a valid weight and the weight stays | none | 45 |
| featherline-0019 | Group editor first-dose picker: a picked value is now compared with the stored one before it is applied. | expected after confirming the same start date the start time shows the start of the day; observed the start time still reads Now | none | 80 |
| markor-0003 | Editor line actions menu: the line-cloning action now computes its insertion point after the line break. | expected the line is duplicated so the file reads gamma, gamma; observed nothing is duplicated | deepseek | 42 |
| markor-0014 | Strong-emphasis hold gesture: the affected lines are now computed from the start and end of the selection range. | expected long-pressing Bold wraps the line, giving **gamma**; observed nothing happens, the line stays gamma and the app closes | none | 151 |

### Needs knowing what the correct value is (10)

| Bug | Release-note line | Defect | Caught by | Most actions |
|---|---|---|---|---:|
| ankidroid-0008 | Card browser cards/notes toggle: each mode's display settings are now read from one shared place. | expected notes mode uses the notes sort order; observed notes mode uses the cards sort order | none | 40 |
| ankidroid-0025 | Filtered deck builder: the criteria dropdown now lists every selection criterion the scheduler offers. | expected the order list has no retrievability options while FSRS is off; observed Retrievability ascending and descending are listed in the order dropdown | none | 58 |
| featherline-0018 | Night owl mode in the group editor: the explanatory caption now builds its cut-off text separately from the remaining values. | expected the description shows 4:00 AM, matching the other times on the screen; observed the description shows 04:00 while the other times use AM and PM | none | 47 |
| idlefantasy-0001 | Shop header: large gold amounts now use a new short format for millions. | expected the coin balance of 2,567,890 is shown as 2.5M (floored); observed the coin balance is shown as 2.6M, rounded up | deepseek | 111 |
| idlefantasy-0005 | Bulk clearance for unused materials: which items count as useful is now decided from crafting recipes. | expected farming produce like pumpkin and tomato should not be listed in sell junk; observed sell junk lists pumpkin and tomato as junk to sell | none | 70 |
| idlefantasy-0006 | Gear tab slot chooser: candidate items are now ranked by their unlock threshold, with title as the tiebreak. | expected runite chainbody (60) should be listed before adamantite platebody (66), ordered by combined stat bonus; observed runite chainbody is listed after adamantite and slayer platebody, sorted by tier and name instead of stat | luna-med | 6 |
| idlefantasy-0008 | Profile milestones section: progress toward mission milestones is now computed from all finished progress records. | expected dedicated (complete 5 quests) should still be in the missing list because only 4 regular quests are done, guild quests do not count; observed dedicated is not in the missing list, it counts the 3 guild quests as completed quests | none | 9 |
| idlefantasy-0009 | Combat screen stats list: the stats shown outside a fight are now calculated from fewer inputs. | expected the attack row should show +9 prestige and hitpoints +4 prestige; observed no prestige bonus is shown, only the gear bonus is displayed | none | 74 |
| iris-0012 | Media tab blank-state illustration: its caption is now built from one constant string resource. | expected the Videos filter shows the message No videos found; observed the Videos filter shows the message No photos found | haiku, deepseek | 12 |
| tasks-0012 | Date badges on task rows: the badge for each date field is now built independently of the others. | expected only one date chip is shown when start and due are the same day; observed a start-date chip duplicates the due date | haiku | 123 |

### Needs multi-step state (1)

| Bug | Release-note line | Defect | Caught by | Most actions |
|---|---|---|---|---:|
| markor-0009 | File browser quick-access marking: the browser's marks are now kept up to date by its own handlers alone. | expected after favouriting Notes.md in the details dialog, the toolbar star is in sync and tapping it removes the favourite, so Favourites does not list Notes.md; observed the toolbar star was not updated after the dialog, tapping it added the favourite again and Notes.md is still listed under Favourites | deepseek, luna-max | 55 |

