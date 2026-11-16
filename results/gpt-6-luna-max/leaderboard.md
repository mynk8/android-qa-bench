# Leaderboard entry (results/gpt-6-luna-max)

**Episode Bug F1: 0.284** (95% CI [0.195, 0.376]) - recall 0.341 (31/91), precision 0.244 (31 credited, 96 false)

**Episode Score: 0.209** (95% CI [0.134, 0.291]) - hit rate 0.471 [0.341, 0.605] (runs with at least one bug caught); catch credit before the precision and cut-off penalties 0.35; finished on its own 0.961 (signed off 0.961)

**Stopping** (refusals made only because reported bugs remained count as sign-offs; tools/hesitations.py): signed off 0.961 - correctly 0.118, with bugs missed 0.843; gave up 0.0; cut off 0.02. Counting mixed refusals too: correct 0.118, false 0.843. No-sign-off reasons: {}

| metric | value |
|---|---|
| episode solve rate | 0.118 [0.055, 0.234] |
| pass_at_1 | 0.118 |
| pass_hat_1 | 0.118 |
| false sign-off rate | 0.878 |
| no sign-off / infra errors | 0 / 0 |
| doom loops killed | 0 |
| unspec cases balanced accuracy | None (faulty 0/0, clean 0/0) |
| spec cases balanced accuracy | None (faulty 0/0, clean 0/0) |
| episode cost / $ per bug found | $7.81 / None |
| case cost (unspec + spec) | $0.00 |
| steps / seconds per episode | 165.9 / 961.0 |

Episode bug recall by contamination risk: older (fixed < 2026): 14/33 (0.424); recent (fixed >= 2026-01-01): 17/58 (0.293)

Changelog coverage (worked = 6+ actions on the feature): real lines reached 82/92, worked 66, caught 31; decoys reached 89/93, worked 77. Real-line misses: ignored 5, shallow 10, tested but not noticed 46
