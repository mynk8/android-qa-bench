# Leaderboard entry (results/claude-haiku-5.5)

**Episode Bug F1: 0.336** (95% CI [0.244, 0.425]) - recall 0.429 (39/91), precision 0.277 (39 credited, 102 false)

**Episode Score: 0.237** (95% CI [0.16, 0.319]) - hit rate 0.569 [0.433, 0.695] (runs with at least one bug caught); catch credit before the precision and cut-off penalties 0.471; finished on its own 0.784 (signed off 0.373)

**Stopping** (refusals made only because reported bugs remained count as sign-offs; tools/hesitations.py): signed off 0.431 - correctly 0.176, with bugs missed 0.255; gave up 0.353; cut off 0.216. Counting mixed refusals too: correct 0.235, false 0.431. No-sign-off reasons: {'unfinished': 6, 'mixed': 12, 'blocked': 3}

| metric | value |
|---|---|
| episode solve rate | 0.137 [0.068, 0.257] |
| pass_at_1 | 0.137 |
| pass_hat_1 | 0.137 |
| false sign-off rate | 0.632 |
| no sign-off / infra errors | 21 / 0 |
| doom loops killed | 0 |
| unspec cases balanced accuracy | None (faulty 0/0, clean 0/0) |
| spec cases balanced accuracy | None (faulty 0/0, clean 0/0) |
| episode cost / $ per bug found | $32.5 / 0.83 |
| case cost (unspec + spec) | $0.00 |
| steps / seconds per episode | 216.6 / 330.9 |

Episode bug recall by contamination risk: older (fixed < 2026): 14/33 (0.424); recent (fixed >= 2026-01-01): 25/58 (0.431)

Changelog coverage (worked = 6+ actions on the feature): real lines reached 83/92, worked 72, caught 39; decoys reached 87/93, worked 81. Real-line misses: ignored 4, shallow 6, tested but not noticed 43
