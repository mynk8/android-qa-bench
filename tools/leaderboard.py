#!/usr/bin/env python3
"""Benchmark scores for one model from one or more run dirs (deterministic).

    python3 tools/leaderboard.py runs/<name> [runs/<name2> ...] [--json out.json] [--md out.md]

Headline
  Episode Bug F1        pooled over episodes and repeats: recall = planted bugs credited /
                        planted bugs present; precision = credited reports / (credited + false
                        reports; duplicates and known-issue reports excluded); F1 of the two.
  Episode Score         per episode: 0 if no planted bug is credited; the first credited bug earns
                        1 point and each further one a 0.5 bonus, scaled so all bugs = 1.0
                        (1 of 2 bugs = 0.67, 1 of 3 = 0.5, 2 of 3 = 0.75); then multiplied by
                        that run's report precision (credited / (credited + false)), and halved
                        when the agent did not finish on its own (cut off by the action cap or the
                        time limit). Ending the session with a written handover instead of
                        sign_off counts as finishing: under the PASS-only sign_off, an agent that
                        still suspects a bug the developer could not reproduce cannot sign off;
                        mean over runs. Catch credit alone (before the two penalties) is also
                        reported. Hit rate = share of runs with at least one bug credited.
Secondary
  Episode solve rate    every present bug credited AND a PASS sign-off (pass@k, pass^k over repeats)
  False sign-off rate   PASS sign-off while present bugs were still unreported
  Case balanced acc.    unspec and spec separately: mean of (faulty: FAIL with a matched failure
                        description) and (clean: PASS)
  Cost / effort         $ per instance, $ per bug found, steps, wall seconds
Splits
  by app, by bug family, and by contamination risk: bugs fixed upstream on or after 2026-01-01
  ("recent", after most training cutoffs) vs earlier ("older").
Uncertainty
  Bootstrap 95% CI (2,000 resamples of episodes) for F1, recall, precision and the Episode
  Score; Wilson 95% CI for per-episode rates (solve rate, hit rate) and the splits.
"""
from __future__ import annotations

import argparse
import collections
import glob
import json
import math
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys  # noqa: E402
sys.path.insert(0, str(ROOT))
D = ROOT / "dataset"
RECENT = "2026-01-01"


def wilson(k: int, n: int, z: float = 1.96) -> list[float] | None:
    if not n:
        return None
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return [round(max(0.0, c - h), 3), round(min(1.0, c + h), 3)]


def f1(tp: int, fp: int, found: int, present: int) -> tuple[float, float, float]:
    p = tp / (tp + fp) if tp + fp else 0.0
    r = found / present if present else 0.0
    return p, r, (2 * p * r / (p + r) if p + r else 0.0)


def agent_result(text: str) -> dict:
    """Claude Code's final result from an agent log: the last {"type":"result"} line of a
    stream-json transcript, or the single JSON object of the older json output format."""
    res = {}
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("{") and '"type":"result"' in line.replace(" ", ""):
            try:
                res = json.loads(line)
            except Exception:
                pass
    if res:
        return res
    try:
        return json.loads(text[text.index("{"):])
    except Exception:
        return {}


# DeepSeek Harness list prices, USD per million tokens (same defaults as agents/dsh_agent.sh)
DSH_PRICE = {"in": 0.0507, "cached": 0.001014, "out": 0.2028}


def dsh_cost_from_steps(text: str) -> float:
    """API-price cost summed from DeepSeek Harness step_end usage events. A session stopped from
    outside (the action cap) ends before agents/dsh_agent.sh writes its result line with the cost."""
    use = {"in": 0, "cached": 0, "write": 0, "out": 0}
    for line in text.splitlines():
        if '"step_end"' not in line:
            continue
        try:
            u = (json.loads(line).get("usage") or {})
        except ValueError:
            continue
        use["in"] += int(u.get("inputTokens") or 0)
        use["cached"] += int(u.get("cacheReadTokens") or 0)
        use["write"] += int(u.get("cacheWriteTokens") or 0)
        use["out"] += int(u.get("outputTokens") or 0)
    return ((use["in"] + use["write"]) * DSH_PRICE["in"] + use["cached"] * DSH_PRICE["cached"]
            + use["out"] * DSH_PRICE["out"]) / 1e6


def agent_cost(run: Path, item: str, rep: int) -> float | None:
    """API-price cost of one session: the harness's own total, or for DeepSeek Harness sessions
    stopped from outside, the sum of its step usage. None when the log holds no cost data at all
    (a missing cost is unknown, not $0)."""
    f = run / "agent_logs" / f"{item}-rep{rep}.log"
    if not f.exists():
        return None
    text = f.read_text(errors="replace")
    cost = agent_result(text).get("total_cost_usd")
    if cost is None and '"phase":"step_end"' in text.replace(" ", ""):
        return dsh_cost_from_steps(text)
    return None if cost is None else float(cost)


def cost_summary(rs: list[dict]) -> dict:
    """Total and mean cost over the sessions that have a cost, and how many do."""
    logged = [r["_cost"] for r in rs if r.get("_cost") is not None]
    return {"total": sum(logged), "n": len(logged),
            "mean": round(sum(logged) / len(logged), 4) if logged else None}


def hesitation(run: Path, r: dict, rep: int) -> str | None:
    """For a no_signoff episode: why the agent stopped without signing off (tools/hesitations.py)."""
    if r.get("outcome") != "no_signoff":
        return None
    from tools import hesitations as H
    f = run / "agent_logs" / f"{r['item_id']}-rep{rep}.log"
    return H.classify(r["item_id"], H.final_text(f.read_text(errors="replace")) if f.exists() else "")


def signed_off(r: dict, count_mixed: bool = False) -> bool:
    """Signed off, or refused only because reported bugs remained (prompt v4's sign-off rule made
    that refusal the truthful answer; under v4.1 the same agents sign off). With count_mixed, also
    the refusals that cite remaining bugs and untested areas (sensitivity row)."""
    if r.get("outcome") in ("success", "wrong_pass"):
        return True
    h = r.get("_hesitation")
    return h == "blocked" or (count_mixed and h == "mixed")


def _current_instances() -> set[str]:
    p = D / "instances.jsonl"
    return {json.loads(l)["instance_id"] for l in p.read_text().splitlines() if l.strip()} if p.exists() else set()


def _requote(r: dict) -> None:
    """Before 2026-11-14 a FAIL whose failure had no observed_quote was rejected as an unverified
    quote. A missing quote is not an invented one: re-check those with the prose matcher."""
    if r.get("kind") != "case" or r.get("localize_reason") != "unverified_quote":
        return
    v = (r.get("verdicts_or_reports") or [{}])[0] or {}
    fail = v.get("failure") if isinstance(v, dict) else None
    if not fail:
        return
    # quotes were also rejected when the screen text carried invisible format characters
    # (fixed 2026-11-14); the screen set is not stored, so these fall back to the prose matcher
    import sys
    sys.path.insert(0, str(ROOT))
    from dataset_tools.matcher import load_key, match_key
    m = match_key(fail, load_key(D / "bugs" / r["bug_id"]))
    r["localized"], r["localize_reason"] = bool(m["match"]), m["reason"] + " (rescored)"
    r["success"] = bool(r.get("verdict_correct")) and r["localized"]


def _legacy_localize(r: dict) -> None:
    """Results written before the description-match rule: re-check a faulty FAIL's failure text
    with the matcher (no quote check; the harness did not record the screen then)."""
    if r.get("kind") != "case" or "localized" in r or r.get("true_verdict") != "FAIL":
        return
    import sys
    sys.path.insert(0, str(ROOT))
    from dataset_tools.matcher import load_key, match_key
    v = (r.get("verdicts_or_reports") or [{}])[0] or {}
    fail = v.get("failure") if isinstance(v, dict) else None
    r["verdict_correct"] = r.get("predicted_verdict") == "FAIL"
    ok = bool(fail) and r["verdict_correct"] and match_key(fail, load_key(D / "bugs" / r["bug_id"]))["match"]
    r["localized"] = ok
    r["success"] = bool(r.get("success")) and ok


def load(runs: list[Path]) -> tuple[list[dict], list[dict]]:
    """Merge run dirs; a later dir replaces an earlier one for the same (instance, repeat)."""
    merged: dict[tuple, dict] = {}
    current = _current_instances()
    for run in runs:
        reps = {}
        rp = run / "results.jsonl"
        if rp.exists():
            for n, line in enumerate(rp.read_text().splitlines()):
                if line.strip():
                    r = json.loads(line)
                    reps[r["run_id"]] = (r["repeat"], r.get("seconds"), n)
        found = []
        for kind in ("episodes", "cases"):
            for f in glob.glob(str(run / kind / "*" / "*" / "result.json")):
                r = json.loads(Path(f).read_text())
                if r["run_id"] in reps:  # else stale or aborted
                    found.append(r)
        # results.jsonl order: a retried (instance, repeat) replaces the earlier attempt
        for r in sorted(found, key=lambda q: reps[q["run_id"]][2]):
                rep, secs, _ = reps[r["run_id"]]
                r["_cost"] = agent_cost(run, r["item_id"], rep)
                r["_hesitation"] = hesitation(run, r, rep)
                r["_secs"] = secs or r.get("elapsed_s") or 0
                if current and r["item_id"] not in current:
                    continue  # instance since removed or moved (e.g. to spec-only)
                _legacy_localize(r)
                _requote(r)
                merged[(r["item_id"], rep)] = r
    eps = [r for r in merged.values() if r.get("kind") == "episode"]
    cases = [r for r in merged.values() if r.get("kind") == "case"]
    return eps, cases


def fix_date(bug: str) -> str:
    try:
        return json.loads((D / "bugs" / bug / "bug.json").read_text()).get("fix_date") or ""
    except FileNotFoundError:
        return ""


def catch_credit(r: dict) -> float:
    """First caught bug = 1 point, each further one +0.5, scaled to 1.0 for all bugs caught."""
    req = set(r.get("required") or [])
    k = len(set(r.get("found") or []) & req)
    n = len(req)
    if not n or not k:
        return 0.0
    return (1 + 0.5 * (k - 1)) / (1 + 0.5 * (n - 1))


def finished(r: dict) -> bool:
    """The agent ended the session itself: signed off, or stopped with a handover (no_signoff)."""
    return r.get("outcome") in ("success", "wrong_pass", "no_signoff")


def episode_score(r: dict) -> float:
    """Catch credit x report precision x (0.5 if the agent was cut off instead of finishing)."""
    c = catch_credit(r)
    if not c:
        return 0.0
    tp = r.get("true_positives") or 0
    fp = r.get("false_positives") or 0
    prec = tp / (tp + fp) if tp + fp else 1.0
    return c * prec * (1.0 if finished(r) else 0.5)


def episode_block(eps: list[dict]) -> dict:
    tp = sum(r.get("true_positives") or 0 for r in eps)
    fp = sum(r.get("false_positives") or 0 for r in eps)
    present = sum(len(r.get("required") or []) for r in eps)
    found = sum(len(set(r.get("found") or []) & set(r.get("required") or [])) for r in eps)
    p, rc, f = f1(tp, fp, found, present)
    solved = sum(bool(r.get("success")) for r in eps)
    signed = [r for r in eps if (r.get("sign_off") or {}).get("verdict") == "PASS"]
    false_so = sum(1 for r in signed if set(r.get("required") or []) - set(r.get("found") or []))
    # bootstrap over episodes (the unit that is sampled): F1, recall and precision. Bugs and reports
    # within an episode are not independent, so their intervals are resampled by episode too.
    rnd = random.Random(0)
    boots, rboots, pboots = [], [], []
    for _ in range(2000 if eps else 0):
        s = [rnd.choice(eps) for _ in eps]
        bt = sum(r.get("true_positives") or 0 for r in s)
        bf = sum(r.get("false_positives") or 0 for r in s)
        bp = sum(len(r.get("required") or []) for r in s)
        bfo = sum(len(set(r.get("found") or []) & set(r.get("required") or [])) for r in s)
        bpr, brc, bf1 = f1(bt, bf, bfo, bp)
        boots.append(bf1)
        rboots.append(brc)
        pboots.append(bpr)
    boots.sort()
    rboots.sort()
    pboots.sort()
    pct = lambda b: [round(b[50], 3), round(b[1949], 3)] if b else None
    scores = [episode_score(r) for r in eps]
    sboots = sorted(sum(rnd.choice(scores) for _ in scores) / len(scores) for _ in range(2000 if scores else 0))
    credits = [catch_credit(r) for r in eps]
    hits = sum(1 for x in credits if x > 0)
    n_signed = sum(1 for r in eps if r.get("sign_off"))
    n_finished = sum(1 for r in eps if finished(r))
    by_item = collections.defaultdict(list)
    for r in eps:
        by_item[r["item_id"]].append(bool(r.get("success")))
    k = min((len(v) for v in by_item.values()), default=0)
    pass_at = sum(any(v[:k]) for v in by_item.values()) / len(by_item) if by_item and k else None
    pass_hat = sum(all(v[:k]) for v in by_item.values()) / len(by_item) if by_item and k else None
    found_total = found
    costs = cost_summary(eps)
    cost = costs["total"]

    # Stopping: how each episode ended, independent of prompt v4's contradictory sign-off rule
    def stop_block(count_mixed: bool) -> dict:
        n = len(eps)
        so = [r for r in eps if signed_off(r, count_mixed)]
        ok = sum(1 for r in so if not set(r.get("required") or []) - set(r.get("found") or []))
        # cut off = the harness ended the session at the action cap (or a doom loop);
        # report_cap = the report limit ended it (both forfeit half the Episode Score)
        cut = sum(1 for r in eps if r.get("outcome") in ("timeout", "doom_loop"))
        capped = sum(1 for r in eps if r.get("outcome") == "report_cap")
        rate = lambda k: round(k / n, 3) if n else None
        return {"signed_off": rate(len(so)), "correct_signoff": rate(ok), "false_signoff": rate(len(so) - ok),
                "gave_up": rate(n - len(so) - cut - capped - sum(1 for r in eps if r.get("outcome") == "error")),
                "cut_off": rate(cut), "report_cap": rate(capped)}
    hes = collections.Counter(r["_hesitation"] for r in eps if r.get("_hesitation"))
    return {
        "stopping": stop_block(False), "stopping_with_mixed": stop_block(True),
        "no_signoff_reasons": dict(hes),
        "episode_score": round(sum(scores) / len(scores), 3) if scores else None,
        "episode_score_ci95": [round(sboots[50], 3), round(sboots[1949], 3)] if sboots else None,
        "catch_credit": round(sum(credits) / len(credits), 3) if credits else None,
        "sign_off_rate": round(n_signed / len(eps), 3) if eps else None,
        "finished_rate": round(n_finished / len(eps), 3) if eps else None,
        "hit_rate": round(hits / len(eps), 3) if eps else None, "hit_rate_ci95": wilson(hits, len(eps)),
        "runs": len(eps), "episodes": len(by_item), "bugs_present": present, "bugs_found": found,
        "reports_credited": tp, "false_reports": fp,
        "bug_f1": round(f, 3), "bug_f1_ci95": [round(boots[50], 3), round(boots[1949], 3)] if boots else None,
        "bug_recall": round(rc, 3), "bug_recall_ci95": pct(rboots),
        "report_precision": round(p, 3), "report_precision_ci95": pct(pboots),
        "solve_rate": round(solved / len(eps), 3) if eps else None, "solve_rate_ci95": wilson(solved, len(eps)),
        f"pass_at_{k}": round(pass_at, 3) if pass_at is not None else None,
        f"pass_hat_{k}": round(pass_hat, 3) if pass_hat is not None else None,
        "false_signoff_rate": round(false_so / len(signed), 3) if signed else None,
        "no_signoff_runs": sum(1 for r in eps if r.get("outcome") == "no_signoff"),
        "doom_loop_runs": sum(1 for r in eps if r.get("outcome") == "doom_loop"),
        "infra_errors": sum(1 for r in eps if r.get("outcome") == "error"),
        "cost_usd": round(cost, 2), "cost_usd_per_episode": costs["mean"],
        "cost_episodes_logged": costs["n"],
        "usd_per_bug_found": round(cost / found_total, 2) if found_total and costs["n"] == len(eps) else None,
        "steps_mean": round(sum(r.get("steps") or 0 for r in eps) / len(eps), 1) if eps else None,
        "seconds_mean": round(sum(r["_secs"] for r in eps) / len(eps), 1) if eps else None,
    }


def case_block(cases: list[dict]) -> dict:
    out = {}
    for tier in ("unspecified", "specified"):
        rs = [r for r in cases if (r.get("conditions") or {}).get("instruction") == tier]
        faulty = [r for r in rs if r.get("true_verdict") == "FAIL"]
        clean = [r for r in rs if r.get("true_verdict") == "PASS"]
        tpr = sum(bool(r.get("success")) for r in faulty) / len(faulty) if faulty else None
        tnr = sum(bool(r.get("success")) for r in clean) / len(clean) if clean else None
        bal = (tpr + tnr) / 2 if tpr is not None and tnr is not None else None
        out["unspec" if tier == "unspecified" else "spec"] = {
            "runs": len(rs), "balanced_accuracy": round(bal, 3) if bal is not None else None,
            "faulty_found": f"{sum(bool(r.get('success')) for r in faulty)}/{len(faulty)}",
            "faulty_found_ci95": wilson(sum(bool(r.get('success')) for r in faulty), len(faulty)),
            "faulty_fail_but_unlocalized": sum(1 for r in faulty if r.get("verdict_correct") and not r.get("success")),
            "clean_passed": f"{sum(bool(r.get('success')) for r in clean)}/{len(clean)}",
            "clean_passed_ci95": wilson(sum(bool(r.get('success')) for r in clean), len(clean)),
            "cost_usd": round(cost_summary(rs)["total"], 2),
        }
    return out


def split_episodes(eps: list[dict], by) -> dict:
    """Per-bug split: recall of bugs grouped by `by(bug)` (contamination, app, family)."""
    g = collections.defaultdict(lambda: [0, 0])
    for r in eps:
        found = set(r.get("found") or [])
        for b in r.get("required") or []:
            key = by(b)
            g[key][1] += 1
            g[key][0] += b in found
    return {k: {"found": f"{v[0]}/{v[1]}", "recall": round(v[0] / v[1], 3), "ci95": wilson(*v)} for k, v in sorted(g.items())}


def family(bug: str) -> str:
    try:
        return json.loads((D / "bugs" / bug / "bug.json").read_text()).get("family") or "?"
    except FileNotFoundError:
        return "?"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", nargs="+", type=Path)
    ap.add_argument("--json", type=Path)
    ap.add_argument("--md", type=Path)
    a = ap.parse_args()
    eps, cases = load(a.runs)
    res = {
        "runs": [str(r) for r in a.runs],
        "headline_episode_bug_f1": None,
        "episodes": episode_block(eps),
        "cases": case_block(cases),
        "episode_bug_recall_by_contamination": split_episodes(
            eps, lambda b: "recent (fixed >= 2026-01-01)" if fix_date(b) >= RECENT else "older (fixed < 2026)"),
        "episode_bug_recall_by_app": split_episodes(eps, lambda b: b.split("-")[0]),
        "episode_bug_recall_by_family": split_episodes(eps, family),
        "case_faulty_found_by_contamination": {
            k: f"{sum(bool(r.get('success')) for r in v)}/{len(v)}" for k, v in sorted(collections.defaultdict(list, {
                lab: [r for r in cases if r.get("true_verdict") == "FAIL"
                      and (fix_date(r.get("bug_id", "")) >= RECENT) == (lab == "recent")]
                for lab in ("recent", "older")}).items())},
    }
    res["headline_episode_bug_f1"] = res["episodes"]["bug_f1"]
    e, c = res["episodes"], res["cases"]
    md = [f"# Leaderboard entry ({', '.join(str(r) for r in a.runs)})", "",
          f"**Episode Bug F1: {e['bug_f1']}** (95% CI {e['bug_f1_ci95']}) - recall {e['bug_recall']} "
          f"({e['bugs_found']}/{e['bugs_present']}), precision {e['report_precision']} "
          f"({e['reports_credited']} credited, {e['false_reports']} false)", "",
          f"**Episode Score: {e['episode_score']}** (95% CI {e['episode_score_ci95']}) - hit rate "
          f"{e['hit_rate']} {e['hit_rate_ci95']} (runs with at least one bug caught); catch credit before the "
          f"precision and cut-off penalties {e['catch_credit']}; finished on its own {e['finished_rate']} "
          f"(signed off {e['sign_off_rate']})", "",
          f"**Stopping** (refusals made only because reported bugs remained count as sign-offs; "
          f"tools/hesitations.py): signed off {e['stopping']['signed_off']} - correctly "
          f"{e['stopping']['correct_signoff']}, with bugs missed {e['stopping']['false_signoff']}; gave up "
          f"{e['stopping']['gave_up']}; cut off {e['stopping']['cut_off']}. Counting mixed refusals too: "
          f"correct {e['stopping_with_mixed']['correct_signoff']}, false {e['stopping_with_mixed']['false_signoff']}. "
          f"No-sign-off reasons: {e['no_signoff_reasons']}", "",
          "| metric | value |", "|---|---|",
          f"| episode solve rate | {e['solve_rate']} {e['solve_rate_ci95']} |",
          *[f"| {k} | {v} |" for k, v in e.items() if k.startswith("pass_")],
          f"| false sign-off rate | {e['false_signoff_rate']} |",
          f"| no sign-off / infra errors | {e['no_signoff_runs']} / {e['infra_errors']} |",
          f"| doom loops killed | {e['doom_loop_runs']} |",
          f"| unspec cases balanced accuracy | {c['unspec']['balanced_accuracy']} (faulty {c['unspec']['faulty_found']}, clean {c['unspec']['clean_passed']}) |",
          f"| spec cases balanced accuracy | {c['spec']['balanced_accuracy']} (faulty {c['spec']['faulty_found']}, clean {c['spec']['clean_passed']}) |",
          f"| episode cost / $ per bug found | ${e['cost_usd']} / {e['usd_per_bug_found']} |",
          f"| case cost (unspec + spec) | ${c['unspec']['cost_usd'] + c['spec']['cost_usd']:.2f} |",
          f"| steps / seconds per episode | {e['steps_mean']} / {e['seconds_mean']} |", "",
          "Episode bug recall by contamination risk: " + "; ".join(
              f"{k}: {v['found']} ({v['recall']})" for k, v in res["episode_bug_recall_by_contamination"].items())]
    # Changelog coverage (diagnostic): did the agent regression-test each release-note line?
    try:
        from tools import changelog_coverage as CC
        notes = json.loads(CC.NOTES.read_text())
        anchors = json.loads(CC.ANCHORS.read_text()) if CC.ANCHORS.exists() else {}
        cov = CC.summarize([r for run in a.runs for r in CC.episode_lines(run, notes, anchors)])
    except Exception as exc:  # notes are private; a public checkout scores without them
        cov = {"error": str(exc)}
    res["changelog_coverage"] = cov
    if cov.get("real"):
        rl, dl = cov["real"], cov.get("decoy") or {}
        md += ["", f"Changelog coverage (worked = {CC.WORK_MIN}+ actions on the feature): real lines reached "
               f"{rl['reached']}/{rl['lines']}, worked {rl['worked']}, caught {rl['caught']}; decoys reached "
               f"{dl.get('reached')}/{dl.get('lines')}, worked {dl.get('worked')}. Real-line misses: ignored "
               f"{rl['miss_ignored']}, shallow {rl['miss_shallow']}, tested but not noticed {rl['miss_tested_not_noticed']}"]
    text = "\n".join(md) + "\n"
    if a.json:
        a.json.write_text(json.dumps(res, indent=1) + "\n")
    if a.md:
        a.md.write_text(text)
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
