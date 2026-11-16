#!/usr/bin/env python3
"""Every number the paper states beyond the leaderboard, computed from results/.

    python3 docs/paper/data/analysis.py      # writes docs/paper/data/analysis.json and prints it

Paired Sol-vs-Sonnet comparison, catch overlap and the union over all configurations, catches made
with a short look, sign-off confidence by correctness, actions at sign-off when regressions were
missed, and recall by upstream fix date.
"""
from __future__ import annotations

import collections
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from tools import changelog_coverage as cc  # noqa: E402
from tools.leaderboard import RECENT  # noqa: E402

CONFIGS = json.loads((HERE / "configs.json").read_text())


def episodes(run: Path) -> dict:
    keep = cc.scored_run_ids(run)
    out = {}
    for p in run.glob("episodes/*/*/result.json"):
        d = json.loads(p.read_text())
        if d["run_id"] in keep:
            out[d["item_id"]] = d
    return out


def signoff(d: dict) -> dict | None:
    s = d.get("sign_off")
    if isinstance(s, str):
        try:
            s = json.loads(s.replace("'", '"'))
        except ValueError:
            import ast
            try:
                s = ast.literal_eval(s)
            except (ValueError, SyntaxError):
                return None
    return s if isinstance(s, dict) else None


def main():
    notes = json.loads(cc.NOTES.read_text())
    anchors = json.loads(cc.ANCHORS.read_text())
    E = {c["key"]: episodes(ROOT / c["runs"][0]) for c in CONFIGS}
    found = {k: {b for d in v.values() for b in d["found"]} for k, v in E.items()}
    bugs = {b for d in E["sonnet"].values() for b in d["required"]}
    out = {}

    # paired: Sol vs Sonnet per-episode recall
    A, B = E["sonnet"], E["sol"]
    diffs, win, loss = [], 0, 0
    for ep in sorted(A):
        n = len(A[ep]["required"])
        a, b = len(A[ep]["found"]), len(B[ep]["found"])
        diffs.append((b - a) / n)
        win += b > a
        loss += b < a
    rnd = random.Random(0)
    boots = sorted(sum(rnd.choice(diffs) for _ in diffs) / len(diffs) for _ in range(2000))
    out["sol_minus_sonnet_recall_per_episode"] = {
        "mean": round(sum(diffs) / len(diffs), 3), "ci95": [round(boots[50], 3), round(boots[1949], 3)],
        "episodes_sol_more": win, "episodes_sonnet_more": loss, "ties": len(diffs) - win - loss}
    out["reports_filed"] = {k: sum(d["reports"] for d in v.values()) for k, v in E.items()}
    fs, fo = found["sonnet"], found["sol"]
    out["overlap_sol_sonnet"] = {"both": len(fs & fo), "only_sol": len(fo - fs), "only_sonnet": len(fs - fo),
                                 "neither": len(bugs - fs - fo)}
    union = set().union(*found.values())
    out["caught_by_any"] = {"caught": len(union), "observable": len(bugs), "caught_by_none": len(bugs - union)}

    # catches with a short look (fewer than WORK_MIN actions with the feature on screen)
    quick = {}
    for c in CONFIGS:
        rows = [x for x in cc.episode_lines(ROOT / c["runs"][0], notes, anchors) if x["kind"] == "real"]
        quick[c["key"]] = {"caught": sum(x["caught"] for x in rows),
                           "caught_with_short_look": sum(x["caught"] and not x["worked"] for x in rows)}
    out["short_look_catches"] = quick

    # sign-off confidence by correctness; actions at sign-off when regressions were missed
    conf, steps_missed = {}, {}
    for k, v in E.items():
        ok, bad, st = [], [], []
        for d in v.values():
            s = signoff(d)
            if not s or s.get("confidence") is None:
                continue
            (ok if set(d["found"]) >= set(d["required"]) else bad).append(float(s["confidence"]))
            if not set(d["found"]) >= set(d["required"]):
                st.append(d.get("steps") or 0)
        conf[k] = {"correct_mean": round(sum(ok) / len(ok), 2) if ok else None, "n_correct": len(ok),
                   "missed_mean": round(sum(bad) / len(bad), 2) if bad else None, "n_missed": len(bad)}
        steps_missed[k] = round(sum(st) / len(st), 1) if st else None
    out["signoff_confidence"] = conf
    out["mean_actions_at_signoff_with_regressions_missed"] = steps_missed

    # pairwise differences: paired sign-flip permutation test over the 51 episodes (20,000
    # permutations), Holm correction over the 15 pairs of each metric
    import itertools
    sys.path.insert(0, str(ROOT / "tools"))
    from leaderboard import episode_score
    metrics = {
        "recall": lambda d: len(set(d["found"]) & set(d["required"])) / len(d["required"]),
        "strict_pass": lambda d: float(bool(d.get("success"))),
        "episode_score": episode_score,
    }
    prng = random.Random(1)

    def perm_p(diffs, B=20000):
        obs = abs(sum(diffs))
        hits = sum(abs(sum(x if prng.random() < 0.5 else -x for x in diffs)) >= obs - 1e-12 for _ in range(B))
        return (hits + 1) / (B + 1)

    keys = [c["key"] for c in CONFIGS]
    tests = {}
    for m, fn in metrics.items():
        rows = []
        for x, y in itertools.combinations(keys, 2):
            diffs = [fn(E[x][ep]) - fn(E[y][ep]) for ep in sorted(E[x])]
            rows.append({"a": x, "b": y, "mean_diff": round(sum(diffs) / len(diffs), 3), "p": perm_p(diffs)})
        rows.sort(key=lambda r: r["p"])
        prev = 0.0
        for i, r in enumerate(rows):  # Holm step-down
            prev = max(prev, min(1.0, (len(rows) - i) * r["p"]))
            r["p_holm"] = round(prev, 4)
            r["p"] = round(r["p"], 4)
        tests[m] = rows
    out["pairwise_tests"] = tests

    # how often each configuration uses the actions the QA method calls for: rotation (device),
    # re-opening the app (state), long-press (hidden actions), typing (input values)
    mix = {}
    for c in CONFIGS:
        tot, eps, n = collections.Counter(), collections.Counter(), 0
        for t in (ROOT / c["runs"][0]).glob("episodes/*/*/trace.jsonl"):
            n += 1
            cnt = collections.Counter()
            for line in t.read_text().splitlines():
                e = json.loads(line)
                m = e.get("message") or {}
                if e.get("event") == "agent" and m.get("type") == "action":
                    name = m.get("name") or ""
                    cnt["long_press" if name.startswith("long_press") else name] += 1
            tot += cnt
            for k in ("rotate", "open_app", "long_press", "type"):
                eps[k] += bool(cnt[k])
        s = sum(tot.values())
        mix[c["key"]] = {k: {"episodes": eps[k], "share_of_actions": round(tot[k] / s, 3)}
                         for k in ("rotate", "open_app", "long_press", "type")}
    out["action_use"] = mix

    # recall by upstream fix date
    fix = {b: json.loads((ROOT / "dataset" / "bugs" / b / "bug.json").read_text())["fix_date"] for b in bugs}
    old = {b for b in bugs if fix[b] < RECENT}
    out["recall_by_fix_date"] = {k: {"before_2026": f"{len(found[k] & old)}/{len(old)}",
                                     "2026": f"{len(found[k] - old)}/{len(bugs - old)}"} for k in found}
    (HERE / "analysis.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
