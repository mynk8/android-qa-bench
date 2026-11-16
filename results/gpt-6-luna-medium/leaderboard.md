# Leaderboard entry (results/gpt-6-luna-medium)

**Episode Bug F1: 0.235** (95% CI [0.139, 0.331]) - recall 0.154 (14/91), precision 0.5 (14 credited, 14 false)

**Episode Score: 0.144** (95% CI [0.072, 0.22]) - hit rate 0.255 [0.155, 0.389] (runs with at least one bug caught); catch credit before the precision and cut-off penalties 0.181; finished on its own 1.0 (signed off 0.941)

**Stopping** (refusals made only because reported bugs remained count as sign-offs; tools/hesitations.py): signed off 0.941 - correctly 0.039, with bugs missed 0.902; gave up 0.059; cut off 0.0. Counting mixed refusals too: correct 0.039, false 0.902. No-sign-off reasons: {'unfinished': 2, 'other': 1}

| metric | value |
|---|---|
| episode solve rate | 0.039 [0.011, 0.132] |
| pass_at_1 | 0.039 |
| pass_hat_1 | 0.039 |
| false sign-off rate | 0.958 |
| no sign-off / infra errors | 3 / 0 |
| doom loops killed | 0 |
| unspec cases balanced accuracy | None (faulty 0/0, clean 0/0) |
| spec cases balanced accuracy | None (faulty 0/0, clean 0/0) |
| episode cost / $ per bug found | $0.78 / 0.06 |
| case cost (unspec + spec) | $0.00 |
| steps / seconds per episode | 39.0 / 134.7 |

Episode bug recall by contamination risk: older (fixed < 2026): 3/33 (0.091); recent (fixed >= 2026-01-01): 11/58 (0.19)

Changelog coverage (worked = 6+ actions on the feature): real lines reached 68/92, worked 27, caught 14; decoys reached 76/93, worked 30. Real-line misses: ignored 20, shallow 35, tested but not noticed 23
