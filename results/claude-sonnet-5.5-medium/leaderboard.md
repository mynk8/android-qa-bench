# Leaderboard entry (results/claude-sonnet-5.5-medium)

**Episode Bug F1: 0.452** (95% CI [0.349, 0.551]) - recall 0.462 (42/91), precision 0.442 (42 credited, 53 false)

**Episode Score: 0.39** (95% CI [0.289, 0.5]) - hit rate 0.647 [0.51, 0.764] (runs with at least one bug caught); catch credit before the precision and cut-off penalties 0.502; finished on its own 1.0 (signed off 1.0)

**Stopping** (refusals made only because reported bugs remained count as sign-offs; tools/hesitations.py): signed off 1.0 - correctly 0.235, with bugs missed 0.765; gave up 0.0; cut off 0.0. Counting mixed refusals too: correct 0.235, false 0.765. No-sign-off reasons: {}

| metric | value |
|---|---|
| episode solve rate | 0.235 [0.14, 0.368] |
| pass_at_1 | 0.235 |
| pass_hat_1 | 0.235 |
| false sign-off rate | 0.765 |
| no sign-off / infra errors | 0 / 0 |
| doom loops killed | 0 |
| unspec cases balanced accuracy | None (faulty 0/0, clean 0/0) |
| spec cases balanced accuracy | None (faulty 0/0, clean 0/0) |
| episode cost / $ per bug found | $27.48 / 0.65 |
| case cost (unspec + spec) | $0.00 |
| steps / seconds per episode | 66.7 / 171.4 |

Episode bug recall by contamination risk: older (fixed < 2026): 17/33 (0.515); recent (fixed >= 2026-01-01): 25/58 (0.431)

Changelog coverage (worked = 6+ actions on the feature): real lines reached 78/92, worked 44, caught 42; decoys reached 85/93, worked 56. Real-line misses: ignored 6, shallow 19, tested but not noticed 25
