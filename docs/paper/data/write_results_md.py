#!/usr/bin/env python3
"""Write docs/RESULTS.md from results.json, analysis.json and hard28.json (run collect.py,
analysis.py and hard_core.py first).

    python3 docs/paper/data/write_results_md.py
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = HERE.parents[1] / "RESULTS.md"
R = json.loads((HERE / "results.json").read_text())
A = json.loads((HERE / "analysis.json").read_text())
H = json.loads((HERE / "hard28.json").read_text())
ORDER = sorted(R, key=lambda c: -c["episodes"]["bug_recall"])

# what a tester must do to expose each regression that Sol and Sonnet both missed
KIND = {
    "round trip: change, leave and reopen, check it was kept": [
        "ankidroid-0007", "ankidroid-0023", "featherline-0005", "markor-0018", "markor-0019", "minus-0007"],
    "a specific input or action": [
        "amaze-0011", "amaze-0015", "amaze-0016", "amaze-0019", "ankidroid-0027", "ankidroid-0030",
        "featherline-0016", "featherline-0019", "markor-0003", "markor-0014"],
    "knowing what the correct value is": [
        "ankidroid-0008", "ankidroid-0025", "featherline-0018", "idlefantasy-0001", "idlefantasy-0005",
        "idlefantasy-0006", "idlefantasy-0008", "idlefantasy-0009", "iris-0012", "tasks-0012"],
    "multi-step state": ["markor-0009"],
}


def name(c):
    return f"{c['label']} ({c['setting']})" if c["setting"] != "default" else c["label"]


def pct(x, ci=None):
    s = f"{100 * x:.1f}"
    return s + (f" [{100 * ci[0]:.1f}, {100 * ci[1]:.1f}]" if ci else "")


def main():
    n_ep = ORDER[0]["episodes"]["episodes"]
    n_obs = A["caught_by_any"]["observable"]
    n_lines = ORDER[0]["coverage"]["real"]["lines"]
    cap = json.loads((ROOT / "results" / ORDER[0]["runs"][0].split("/")[-1] / "run.json").read_text())["limits"]["episode_steps"]
    L = ["# Results", "",
         f"Six agent configurations on all {n_ep} episodes, one run each. Every number here is computed from",
         "`results/` by the scripts in `docs/paper/data/` (`collect.py`, `analysis.py`, `hard_core.py`,",
         "then `write_results_md.py`). Definitions: [METHODOLOGY.md](METHODOLOGY.md), section 6.", ""]

    L += ["## Main results", "",
          "| Configuration | Recall % | Strict pass % | Precision % | Episode Score | Catch credit | Actions / ep | Minutes / ep | $ / ep |",
          "|---|---|---|---|---|---|---:|---:|---:|"]
    for c in ORDER:
        e = c["episodes"]
        L.append(f"| {name(c)} | {pct(e['bug_recall'], e['bug_recall_ci95'])} | {pct(e['solve_rate'], e['solve_rate_ci95'])} | "
                 f"{pct(e['report_precision'], e['report_precision_ci95'])} | {e['episode_score']:.3f} "
                 f"[{e['episode_score_ci95'][0]:.2f}, {e['episode_score_ci95'][1]:.2f}] | {e['catch_credit']:.2f} | "
                 f"{e['steps_mean']:.0f} | {e['seconds_mean'] / 60:.1f} | {e['cost_usd_per_episode'] if e['cost_usd_per_episode'] is None else format(e['cost_usd_per_episode'], '.3f')}{'' if e['cost_episodes_logged'] == e['episodes'] else f" ({e['cost_episodes_logged']}/{e['episodes']} logged)"} |")
    L += ["", f"Recall counts the {n_obs} observable regressions; credited and false reports per configuration:", "",
          "| Configuration | Credited | False | Reports filed |", "|---|---:|---:|---:|"]
    for c in ORDER:
        e = c["episodes"]
        L.append(f"| {name(c)} | {e['reports_credited']} | {e['false_reports']} | {A['reports_filed'][c['key']]} |")

    L += ["", "## How episodes ended", "", f"| Configuration | Correct sign-off | Signed off, regressions missed | Stopped, no sign-off | Cut off at {cap} actions | Stopped at report limit |",
          "|---|---:|---:|---:|---:|---:|"]
    for c in ORDER:
        s = c["episodes"]["stopping"]
        L.append(f"| {name(c)} | {s['correct_signoff']:.0%} | {s['false_signoff']:.0%} | {s['gave_up']:.0%} | {s['cut_off']:.0%} | {s['report_cap']:.0%} |")
    L += ["", "Sign-off confidence reported by the agent, by whether every regression had been reported:", "",
          "| Configuration | Mean confidence, correct (n) | Mean confidence, regressions missed (n) | Actions at sign-off with regressions missed |",
          "|---|---|---|---:|"]
    for c in ORDER:
        k = A["signoff_confidence"][c["key"]]
        L.append(f"| {name(c)} | {k['correct_mean']} ({k['n_correct']}) | {k['missed_mean']} ({k['n_missed']}) | "
                 f"{A['mean_actions_at_signoff_with_regressions_missed'][c['key']]} |")

    p = A["sol_minus_sonnet_recall_per_episode"]
    o = A["overlap_sol_sonnet"]
    u = A["caught_by_any"]
    L += ["", "## Sol and Sonnet, paired by episode", "",
          f"- Per-episode recall, Sol minus Sonnet: {p['mean']:+.3f} (95% CI {p['ci95'][0]:+.3f} to {p['ci95'][1]:+.3f}).",
          f"- Sol caught more in {p['episodes_sol_more']} episodes, Sonnet in {p['episodes_sonnet_more']}, tie in {p['ties']}.",
          f"- Regressions caught by both {o['both']}, only Sol {o['only_sol']}, only Sonnet {o['only_sonnet']}, neither {o['neither']}.",
          f"- Over all six configurations: {u['caught']} of {u['observable']} observable regressions caught at least once; "
          f"{u['caught_by_none']} caught by none.", ""]

    L += [f"## Changelog coverage ({n_lines} release-note lines that hide a regression)", "",
          "| Configuration | Reached | Exercised (6+ actions) | Caught | Ignored | Shallow | Tested, not noticed | Caught with a short look | Decoys reached / exercised |",
          "|---|---:|---:|---:|---:|---:|---:|---:|---|"]
    for c in ORDER:
        r, d = c["coverage"]["real"], c["coverage"]["decoy"]
        q = A["short_look_catches"][c["key"]]
        L.append(f"| {name(c)} | {r['reached']} | {r['worked']} | {r['caught']} | {r['miss_ignored']} | {r['miss_shallow']} | "
                 f"{r['miss_tested_not_noticed']} | {q['caught_with_short_look']} | {d['reached']} / {d['worked']} of {d['lines']} |")

    NAMES = {c["key"]: name(c) for c in R}
    T = A["pairwise_tests"]
    L += ["", "## Pairwise differences", "",
          "Paired sign-flip permutation test over the 51 episodes (20,000 permutations); Holm correction over",
          "the 15 pairs of each metric. Difference = first minus second configuration, per-episode mean.", "",
          "| Pair | Recall diff | p (Holm) | Strict pass diff | p (Holm) | Episode Score diff | p (Holm) |",
          "|---|---:|---:|---:|---:|---:|---:|"]
    look = {m: {(r["a"], r["b"]): r for r in rows} for m, rows in T.items()}
    for (x, y) in look["recall"]:
        cells = []
        for m in ("recall", "strict_pass", "episode_score"):
            r = look[m][(x, y)]
            cells += [f"{r['mean_diff']:+.3f}", f"{r['p_holm']:.3f}" + (" *" if r["p_holm"] < 0.05 else "")]
        L.append(f"| {NAMES[x]} vs {NAMES[y]} | " + " | ".join(cells) + " |")
    L.append("")
    L.append("\\* significant at 0.05 after Holm correction.")

    # LaTeX table for the paper appendix
    tex = ["\\begin{tabular}{lrrrr}", "\\toprule",
           "Pair & Recall diff & $p_\\text{Holm}$ & Episode Score diff & $p_\\text{Holm}$ \\\\", "\\midrule"]
    short = {"sonnet": "Sonnet", "sol": "Sol", "haiku": "Haiku", "luna-max": "Luna max",
             "luna-med": "Luna medium", "deepseek": "DeepSeek"}
    for (x, y) in sorted(look["recall"], key=lambda k: look["recall"][k]["p_holm"]):
        r, e = look["recall"][(x, y)], look["episode_score"][(x, y)]
        f = lambda v: f"{v:.3f}" if v >= 0.001 else "$<$0.001"
        tex.append(f"{short[x]} vs {short[y]} & {r['mean_diff']:+.3f} & {f(r['p_holm'])} & {e['mean_diff']:+.3f} & {f(e['p_holm'])} \\\\")
    tex += ["\\bottomrule", "\\end{tabular}"]
    (HERE.parent / "pairwise.tex").write_text("\n".join(tex) + "\n")

    L += ["", "## Use of the actions the QA method calls for", "",
          "Episodes (of 51) with at least one such action; `open_app` only (re-opening a file inside the app is not counted).", "",
          "| Configuration | Rotate | Re-open app | Long-press | Type text |", "|---|---:|---:|---:|---:|"]
    for c in ORDER:
        u = A["action_use"][c["key"]]
        L.append(f"| {name(c)} | {u['rotate']['episodes']} | {u['open_app']['episodes']} | "
                 f"{u['long_press']['episodes']} | {u['type']['episodes']} |")
    L += ["", "## Recall by app, family and fix date", "",
          "| App | " + " | ".join(name(c) for c in ORDER) + " |", "|---|" + "---:|" * len(ORDER)]
    for app in sorted(ORDER[0]["by_app"]):
        L.append(f"| {app} ({ORDER[0]['by_app'][app]['found'].split('/')[1]}) | " +
                 " | ".join(c["by_app"][app]["found"].split("/")[0] for c in ORDER) + " |")
    for fam in ("display", "interaction", "state"):
        L.append(f"| family: {fam} ({ORDER[0]['by_family'][fam]['found'].split('/')[1]}) | " +
                 " | ".join(c["by_family"][fam]["found"].split("/")[0] for c in ORDER) + " |")
    for k, lab in (("before_2026", "fixed before 2026"), ("2026", "fixed in 2026")):
        L.append(f"| {lab} ({A['recall_by_fix_date']['sonnet'][k].split('/')[1]}) | " +
                 " | ".join(A["recall_by_fix_date"][c["key"]][k].split("/")[0] for c in ORDER) + " |")

    L += ["", f"## Regressions both Sol and Sonnet missed ({len(H)})", "",
          "Grouped by what a tester must do to expose them. *Caught by*: other configurations that caught it.",
          "*Most actions*: the most actions any of Sonnet, Sol, Haiku or DeepSeek spent with the feature on screen.", ""]
    info = {h["bug"]: h for h in H}
    assert sorted(b for v in KIND.values() for b in v) == sorted(info), "KIND must cover the hard set"
    for kind, bugs in KIND.items():
        L += [f"### Needs {kind} ({len(bugs)})", "", "| Bug | Release-note line | Defect | Caught by | Most actions |", "|---|---|---|---|---:|"]
        for b in bugs:
            h = info[b]
            L.append(f"| {b} | {h['line']} | expected {h['expected']}; observed {h['observed']} | "
                     f"{', '.join(h['caught_by']) or 'none'} | {max((v or 0) for v in h['depth'].values())} |")
        L.append("")
    OUT.write_text("\n".join(L) + "\n")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
