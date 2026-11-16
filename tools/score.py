#!/usr/bin/env python3
"""Aggregate eval result.json files into per-episode, per-app, per-family and
hard-slice metrics (JSON + Markdown).

    python tools/score.py logs/eval --out logs/eval/score.json --md logs/eval/score.md
    python tools/score.py logs/eval/cases --kind case --out logs/eval/cases/score.json
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("inputs", nargs="+", type=Path, help="result.json files or directories to walk")
    ap.add_argument("--kind", choices=("auto", "episode", "case"), default="auto")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--md", type=Path, default=None)
    ap.add_argument("--k", type=int, default=None, help="k for pass@k and pass^k (default: min runs per item)")
    return ap.parse_args()


def find_results(paths: list[Path]) -> list[dict]:
    files: list[Path] = []
    for p in paths:
        if p.is_file() and p.name.endswith(".json") and p.name != "index.json" and p.name != "score.json":
            files.append(p)
        elif p.is_dir():
            files.extend(q for q in p.rglob("result.json"))
    rows = []
    for f in sorted(set(files)):
        try:
            obj = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if obj.get("kind") in ("episode", "case") and "item_id" in obj:
            obj["_path"] = str(f)
            rows.append(obj)
    return rows


def _prf(rows: list[dict]) -> dict:
    n = len(rows)
    success = sum(1 for r in rows if r.get("success"))
    steps = [r.get("steps") or 0 for r in rows]
    tp = sum(r.get("true_positives") or 0 for r in rows)
    fp = sum(r.get("false_positives") or 0 for r in rows)
    # episode recall is over bugs; case recall is over faulty cases
    if rows and rows[0].get("kind") == "case":
        faulty = [r for r in rows if r.get("true_verdict") == "FAIL"]
        rec = (sum(1 for r in faulty if r.get("predicted_verdict") == "FAIL") / len(faulty)) if faulty else None
        prec = (sum(1 for r in rows if r.get("predicted_verdict") == "FAIL" and r.get("true_verdict") == "FAIL")
                / max(1, sum(1 for r in rows if r.get("predicted_verdict") == "FAIL"))) if any(r.get("predicted_verdict") == "FAIL" for r in rows) else (1.0 if not any(r.get("predicted_verdict") == "FAIL" for r in rows) else 0.0)
        if not any(r.get("predicted_verdict") == "FAIL" for r in rows):
            prec = 1.0 if not faulty else 0.0
        return {
            "n": n,
            "success_rate": (success / n) if n else 0.0,
            "precision": prec,
            "recall": rec if rec is not None else 0.0,
            "false_positives": sum(r.get("false_positives") or 0 for r in rows),
            "false_negatives": sum(r.get("false_negatives") or 0 for r in rows),
            "steps_mean": (sum(steps) / n) if n else 0.0,
            "steps_total": sum(steps),
        }
    # episode: micro-average precision; macro recall over bugs also reported via found
    found = 0
    total_bugs = 0
    for r in rows:
        found += len(r.get("found") or [])
        total_bugs += len(r.get("bugs") or [])
    denom = tp + fp
    return {
        "n": n,
        "success_rate": (success / n) if n else 0.0,
        "precision": (tp / denom) if denom else 1.0,
        "recall": (found / total_bugs) if total_bugs else 1.0,
        "false_positives": fp,
        "true_positives": tp,
        "steps_mean": (sum(steps) / n) if n else 0.0,
        "steps_total": sum(steps),
        "bugs": total_bugs,
        "bugs_found": found,
    }


def _per_item(rows: list[dict]) -> list[dict]:
    out = []
    for r in rows:
        rec = {
            "item_id": r.get("item_id"),
            "kind": r.get("kind"),
            "app_id": r.get("app_id"),
            "outcome": r.get("outcome"),
            "success": r.get("success"),
            "status": r.get("status"),
            "precision": r.get("precision"),
            "recall": r.get("recall"),
            "false_positives": r.get("false_positives") or 0,
            "steps": r.get("steps") or 0,
        }
        if r.get("kind") == "episode":
            rec["bugs"] = r.get("bugs")
            rec["found"] = r.get("found")
        else:
            rec["true_verdict"] = r.get("true_verdict")
            rec["predicted_verdict"] = r.get("predicted_verdict")
            rec["variant"] = r.get("variant")
        out.append(rec)
    return out



def wilson_ci(successes: int, n: int, z: float = 1.96) -> dict:
    """95% Wilson score interval for a Bernoulli success rate."""
    if n <= 0:
        return {"low": 0.0, "high": 1.0, "n": 0, "method": "wilson"}
    p = successes / n
    z2 = z * z
    denom = 1.0 + z2 / n
    centre = (p + z2 / (2 * n)) / denom
    half = (z * math.sqrt((p * (1 - p) + z2 / (4 * n)) / n)) / denom
    return {"low": max(0.0, centre - half), "high": min(1.0, centre + half),
            "n": n, "method": "wilson"}


def _comb(n: int, k: int) -> float:
    if k < 0 or k > n:
        return 0.0
    return float(math.comb(n, k))


def pass_at_k_unbiased(c: int, n: int, k: int) -> float:
    """Chen et al. unbiased pass@k: P(at least one of k samples is correct)."""
    if n <= 0 or k <= 0:
        return 0.0
    if k > n:
        k = n
    if n - c < k:
        return 1.0
    return 1.0 - (_comb(n - c, k) / _comb(n, k))


def pass_hat_k(c: int, n: int, k: int) -> float:
    """pass^k: P(all of k samples are correct). 1 only if every run in the k-set passed."""
    if n <= 0 or k <= 0:
        return 0.0
    if k > n:
        k = n
    if c < k:
        return 0.0
    return _comb(c, k) / _comb(n, k)


def reliability(rows: list[dict], k: int | None = None) -> dict:
    by: dict[tuple, list] = {}
    for r in rows:
        by.setdefault((r.get("item_id"), r.get("model") or "unknown"), []).append(r)
    if not by:
        return {"k": 0, "items": 0, "pass_at_k": 0.0, "pass_hat_k": 0.0,
                "success_rate_ci95": wilson_ci(0, 0), "runs_per_item_min": 0,
                "runs_per_item_max": 0}
    ns = [len(v) for v in by.values()]
    k_use = k if k is not None else min(ns)
    pass_at, pass_hat = [], []
    for group in by.values():
        c = sum(1 for r in group if r.get("success"))
        n = len(group)
        pass_at.append(pass_at_k_unbiased(c, n, k_use))
        pass_hat.append(pass_hat_k(c, n, k_use))
    succ = sum(1 for r in rows if r.get("success"))
    return {
        "k": k_use,
        "items": len(by),
        "runs": len(rows),
        "runs_per_item_min": min(ns),
        "runs_per_item_max": max(ns),
        "pass_at_k": sum(pass_at) / len(pass_at),
        "pass_hat_k": sum(pass_hat) / len(pass_hat),
        "success_rate_ci95": wilson_ci(succ, len(rows)),
    }


def usage_rollup(rows: list[dict]) -> dict:
    elapsed = [float(r.get("elapsed_s") or 0) for r in rows]
    inn = out = cost = 0.0
    for r in rows:
        u = r.get("usage") or {}
        inn += int(u.get("input_tokens") or 0)
        out += int(u.get("output_tokens") or 0)
        cost += float(u.get("cost_usd") or 0)
    n = len(rows)
    return {
        "elapsed_s_total": sum(elapsed),
        "elapsed_s_mean": (sum(elapsed) / n) if n else 0.0,
        "input_tokens": int(inn),
        "output_tokens": int(out),
        "total_tokens": int(inn + out),
        "cost_usd_total": cost,
        "cost_usd_mean": (cost / n) if n else 0.0,
        "reward_hack_runs": sum(1 for r in rows if r.get("reward_hack")),
    }


def aggregate(rows: list[dict], k: int | None = None) -> dict:
    if not rows:
        return {"n": 0, "overall": _prf([]), "per_episode": [], "per_case": [],
                "per_app": {}, "per_family": {}, "hard_slice": {},
                "reliability": reliability([]), "usage": usage_rollup([])}
    kind = rows[0].get("kind")
    overall = _prf(rows)
    per_app = {}
    by_app = defaultdict(list)
    for r in rows:
        by_app[r.get("app_id") or "unknown"].append(r)
    for app, group in sorted(by_app.items()):
        per_app[app] = _prf(group)

    # family / hard-slice: for episodes, attribute bugs; for cases, the case's bug
    by_fam = defaultdict(list)
    hard_rows = []
    hard_bug_found = hard_bug_total = 0
    fam_bug = defaultdict(lambda: {"found": 0, "total": 0, "fp": 0, "tp": 0, "steps": []})

    if kind == "episode":
        for r in rows:
            meta = r.get("bug_meta") or {}
            found = set(r.get("found") or [])
            has_hard = False
            for b in r.get("bugs") or []:
                fam = (meta.get(b) or {}).get("family") or "unknown"
                fam_bug[fam]["total"] += 1
                if b in found:
                    fam_bug[fam]["found"] += 1
                if (meta.get(b) or {}).get("hard_slice"):
                    has_hard = True
                    hard_bug_total += 1
                    if b in found:
                        hard_bug_found += 1
            # attach report-level fp to the run only (not split by family cleanly)
            for fam in {((meta.get(b) or {}).get("family") or "unknown") for b in (r.get("bugs") or [])}:
                by_fam[fam].append(r)
                fam_bug[fam]["fp"] += r.get("false_positives") or 0
                fam_bug[fam]["tp"] += r.get("true_positives") or 0
                fam_bug[fam]["steps"].append(r.get("steps") or 0)
            if has_hard:
                hard_rows.append(r)
        per_family = {}
        for fam, st in sorted(fam_bug.items()):
            denom = st["tp"] + st["fp"]
            per_family[fam] = {
                "bugs": st["total"],
                "bugs_found": st["found"],
                "recall": (st["found"] / st["total"]) if st["total"] else 1.0,
                "precision": (st["tp"] / denom) if denom else 1.0,
                "false_positives": st["fp"],
                "n_episodes_touching": len(by_fam[fam]),
                "steps_mean": (sum(st["steps"]) / len(st["steps"])) if st["steps"] else 0.0,
            }
        hard = {
            "n_episodes": len(hard_rows),
            "success_rate": (sum(1 for r in hard_rows if r.get("success")) / len(hard_rows)) if hard_rows else 0.0,
            "bugs": hard_bug_total,
            "bugs_found": hard_bug_found,
            "recall": (hard_bug_found / hard_bug_total) if hard_bug_total else 1.0,
            "precision": _prf(hard_rows)["precision"] if hard_rows else 1.0,
            "false_positives": sum(r.get("false_positives") or 0 for r in hard_rows),
            "steps_mean": _prf(hard_rows)["steps_mean"] if hard_rows else 0.0,
        }
    else:
        for r in rows:
            fam = r.get("family") or "unknown"
            by_fam[fam].append(r)
            if r.get("hard_slice"):
                hard_rows.append(r)
        per_family = {fam: _prf(group) for fam, group in sorted(by_fam.items())}
        hard = _prf(hard_rows) if hard_rows else _prf([])

    overall = dict(overall)
    overall.update(usage_rollup(rows))
    rel = reliability(rows, k=k)
    overall["success_rate_ci95"] = rel["success_rate_ci95"]
    overall["pass_at_k"] = rel["pass_at_k"]
    overall["pass_hat_k"] = rel["pass_hat_k"]
    overall["k"] = rel["k"]
    return {
        "kind": kind,
        "n": len(rows),
        "overall": overall,
        "reliability": rel,
        "usage": usage_rollup(rows),
        "per_episode": _per_item([r for r in rows if r.get("kind") == "episode"]),
        "per_case": _per_item([r for r in rows if r.get("kind") == "case"]),
        "per_app": per_app,
        "per_family": per_family,
        "hard_slice": hard,
    }


def to_markdown(agg: dict) -> str:
    def fmt(x):
        if isinstance(x, float):
            return f"{x:.3f}"
        return str(x)

    lines = ["# Eval scores", ""]
    ov = agg.get("overall") or {}
    lines.append(f"Kind: **{agg.get('kind')}**. Runs: **{agg.get('n', 0)}**.")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---:|")
    for k in ("success_rate", "precision", "recall", "false_positives", "steps_mean", "steps_total",
              "bugs", "bugs_found", "pass_at_k", "pass_hat_k", "k",
              "elapsed_s_mean", "elapsed_s_total", "total_tokens", "cost_usd_total", "cost_usd_mean",
              "reward_hack_runs"):
        if k in ov:
            lines.append(f"| {k.replace('_', ' ')} | {fmt(ov[k])} |")
    ci = ov.get("success_rate_ci95") or (agg.get("reliability") or {}).get("success_rate_ci95")
    if ci:
        lines.append(f"| success rate 95% CI (Wilson) | {fmt(ci.get('low', 0))}–{fmt(ci.get('high', 1))} |")
    lines.append("")
    rel = agg.get("reliability") or {}
    if rel:
        lines.append("Reliability uses every independent run of the same item. "
                     f"**pass@k** (k={rel.get('k')}) is the unbiased chance at least one of k runs succeeds; "
                     "**pass^k** is the chance all k succeed.")
        lines.append("")
    items = agg.get("per_episode") or agg.get("per_case") or []
    label = "episode" if agg.get("per_episode") else "case"
    if items:
        lines.append(f"## Per {label}")
        lines.append("")
        cols = ["item_id", "app_id", "outcome", "precision", "recall", "false_positives", "steps"]
        lines.append("| " + " | ".join(cols) + " |")
        lines.append("|" + "|".join(["---"] * len(cols)) + "|")
        for r in items:
            lines.append("| " + " | ".join(fmt(r.get(c, "")) for c in cols) + " |")
        lines.append("")
    if agg.get("per_app"):
        lines.append("## Per app")
        lines.append("")
        lines.append("| app | n | success rate | precision | recall | false positives | steps mean |")
        lines.append("|---|---:|---:|---:|---:|---:|---:|")
        for app, st in agg["per_app"].items():
            lines.append(
                f"| {app} | {st.get('n', '')} | {fmt(st.get('success_rate', 0))} | "
                f"{fmt(st.get('precision', 0))} | {fmt(st.get('recall', 0))} | "
                f"{st.get('false_positives', 0)} | {fmt(st.get('steps_mean', 0))} |"
            )
        lines.append("")
    if agg.get("per_family"):
        lines.append("## Per family")
        lines.append("")
        lines.append("| family | recall | precision | false positives |")
        lines.append("|---|---:|---:|---:|")
        for fam, st in agg["per_family"].items():
            lines.append(f"| {fam} | {fmt(st.get('recall', 0))} | {fmt(st.get('precision', 0))} | {st.get('false_positives', 0)} |")
        lines.append("")
    if agg.get("hard_slice"):
        hs = agg["hard_slice"]
        lines.append("## Hard slice")
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("|---|---:|")
        for k, v in hs.items():
            lines.append(f"| {k.replace('_', ' ')} | {fmt(v)} |")
        lines.append("")
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    rows = find_results(args.inputs)
    if args.kind != "auto":
        rows = [r for r in rows if r.get("kind") == args.kind]
    agg = aggregate(rows, k=args.k)
    text = json.dumps(agg, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    if args.md:
        args.md.parent.mkdir(parents=True, exist_ok=True)
        args.md.write_text(to_markdown(agg), encoding="utf-8")
    print(f"scored {agg.get('n', 0)} runs kind={agg.get('kind')}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
