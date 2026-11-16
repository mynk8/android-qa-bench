# Leaderboard entry (results/gpt-6.1-sol-low)

**Episode Bug F1: 0.432** (95% CI [0.365, 0.496]) - recall 0.593 (54/91), precision 0.34 (54 credited, 105 false)

**Episode Score: 0.289** (95% CI [0.219, 0.358]) - hit rate 0.804 [0.675, 0.89] (runs with at least one bug caught); catch credit before the precision and cut-off penalties 0.657; finished on its own 0.863 (signed off 0.843)

**Stopping** (refusals made only because reported bugs remained count as sign-offs; tools/hesitations.py): signed off 0.843 - correctly 0.294, with bugs missed 0.549; gave up 0.02; cut off 0.137. Counting mixed refusals too: correct 0.294, false 0.549. No-sign-off reasons: {'unfinished': 1}

| metric | value |
|---|---|
| episode solve rate | 0.294 [0.187, 0.43] |
| pass_at_1 | 0.294 |
| pass_hat_1 | 0.294 |
| false sign-off rate | 0.651 |
| no sign-off / infra errors | 1 / 0 |
| doom loops killed | 0 |
| unspec cases balanced accuracy | None (faulty 0/0, clean 0/0) |
| spec cases balanced accuracy | None (faulty 0/0, clean 0/0) |
| episode cost / $ per bug found | $33.1 / 0.61 |
| case cost (unspec + spec) | $0.00 |
| steps / seconds per episode | 201.5 / 442.8 |

Episode bug recall by contamination risk: older (fixed < 2026): 19/33 (0.576); recent (fixed >= 2026-01-01): 35/58 (0.603)

Changelog coverage (worked = 6+ actions on the feature): real lines reached 88/92, worked 68, caught 54; decoys reached 92/93, worked 85. Real-line misses: ignored 0, shallow 9, tested but not noticed 29
