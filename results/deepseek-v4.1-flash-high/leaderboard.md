# Leaderboard entry (results/deepseek-v4.1-flash-high)

**Episode Bug F1: 0.407** (95% CI [0.329, 0.481]) - recall 0.505 (46/91), precision 0.341 (46 credited, 89 false)

**Episode Score: 0.183** (95% CI [0.121, 0.251]) - hit rate 0.686 [0.55, 0.797] (runs with at least one bug caught); catch credit before the precision and cut-off penalties 0.541; finished on its own 0.176 (signed off 0.176)

**Stopping** (refusals made only because reported bugs remained count as sign-offs; tools/hesitations.py): signed off 0.176 - correctly 0.118, with bugs missed 0.059; gave up 0.0; cut off 0.784. Counting mixed refusals too: correct 0.118, false 0.059. No-sign-off reasons: {}

| metric | value |
|---|---|
| episode solve rate | 0.118 [0.055, 0.234] |
| pass_at_1 | 0.118 |
| pass_hat_1 | 0.118 |
| false sign-off rate | 0.333 |
| no sign-off / infra errors | 0 / 0 |
| doom loops killed | 0 |
| unspec cases balanced accuracy | None (faulty 0/0, clean 0/0) |
| spec cases balanced accuracy | None (faulty 0/0, clean 0/0) |
| episode cost / $ per bug found | $3.13 / 0.07 |
| case cost (unspec + spec) | $0.00 |
| steps / seconds per episode | 293.8 / 1244.2 |

Episode bug recall by contamination risk: older (fixed < 2026): 16/33 (0.485); recent (fixed >= 2026-01-01): 30/58 (0.517)

Changelog coverage (worked = 6+ actions on the feature): real lines reached 87/92, worked 79, caught 46; decoys reached 92/93, worked 87. Real-line misses: ignored 0, shallow 3, tested but not noticed 43
