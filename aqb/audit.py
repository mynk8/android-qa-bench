"""Explain every grading decision in a run (deterministic: re-derived from the frozen keys).

Writes runs/<name>/audit/<instance>__<run_id>.md and audit/README.md (index).
For each episode report: the matcher decision against every key in the
episode (its bugs and known leftovers) with the reason a key did not match,
plus the developer reply the agent got. For each case: truth vs verdict and
the agent's evidence. Links point at the trace and screenshots.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "dataset"


def _rel(p: Path, base: Path) -> str:
    try:
        return str(p.relative_to(base))
    except ValueError:
        return str(p)


def _episode_md(res: dict, path: Path, out_dir: Path) -> list[str]:
    from dataset_tools.matcher import match_key
    ep = json.loads((DATASET / "episodes" / res["item_id"] / "episode.json").read_text())
    ids = list(ep["bugs"]) + list(ep.get("known_leftover") or [])
    keys = {b: json.loads((DATASET / "bugs" / b / "match.json").read_text()) for b in ids}
    L = [f"# {res['item_id']} · run {res['run_id']}", "",
         f"**Outcome: {res['outcome']}** · protocol `{res['settings'].get('protocol', 'full')}` · "
         f"required {res.get('required', ep['bugs'])} · found {res['found']} · missed {res['missed']}",
         f"· reports {res['reports']} (tp {res['true_positives']}, fp {res['false_positives']}, "
         f"known-issue {res['leftover_reports']}, duplicate/already-fixed {res['already_fixed_reports']}) · steps {res['steps']}",
         "", "Why: " + {
             "success": "signed off PASS after every required bug was reported and matched.",
             "wrong_pass": "signed off while a required bug was still unreported (see missed).",
             "timeout": "hit the action cap before signing off.",
             "report_cap": "filed more reports than the report limit (2n+3) allows; the session ended.",
             "reward_hack": "named a protected path (gold answers); disqualified.",
         }.get(res["outcome"], res["outcome"]), "",
         f"Trace: `{_rel(path.parent / 'trace.jsonl', out_dir)}`", ""]
    replies = res.get("harness_replies") or []
    for i, rep in enumerate(res.get("verdicts_or_reports") or [], 1):
        L += [f"## Report {i}", "", "```json", json.dumps(rep, indent=2, ensure_ascii=False), "```", "",
              "| key | role | decision |", "|---|---|---|"]
        for b in ids:
            m = match_key(rep, keys[b])
            role = "episode bug" if b in ep["bugs"] else "known leftover"
            L.append(f"| {b} | {role} | {'**match**' if m['match'] else 'no: ' + m['reason']} |")
        if i - 1 < len(replies):
            L += ["", f"Developer reply: _{replies[i - 1]}_"]
        L.append("")
    return L


def _case_md(res: dict, path: Path, out_dir: Path) -> list[str]:
    case = json.loads((DATASET / "cases" / res["item_id"] / "case.json").read_text())
    L = [f"# {res['item_id']} · run {res['run_id']}", "",
         f"**Outcome: {res.get('outcome')}** · truth `{case.get('_true_verdict')}` · "
         f"predicted `{res.get('predicted') or res.get('verdict')}` · build `{case.get('_build_id')}`", "",
         f"Trace: `{_rel(path.parent / 'trace.jsonl', out_dir)}`", "", "## Agent answer", "", "```json",
         json.dumps(res.get("agent_verdict") or res.get("raw") or res.get("verdicts_or_reports"), indent=2,
                    ensure_ascii=False, default=str), "```", ""]
    return L


def audit(run_dir: Path, instance: str | None = None) -> int:
    run_dir = Path(run_dir)
    out = run_dir / "audit"
    out.mkdir(exist_ok=True)
    index = ["# Audit index", "", "| instance | run | kind | outcome | file |", "|---|---|---|---|---|"]
    n = 0
    for path in sorted(run_dir.glob("*/*/*/result.json")):
        res = json.loads(path.read_text())
        if instance and res.get("item_id") != instance:
            continue
        kind = res.get("kind")
        md = _episode_md(res, path, run_dir) if kind == "episode" else _case_md(res, path, run_dir)
        f = out / f"{res['item_id']}__{res['run_id']}.md"
        f.write_text("\n".join(md) + "\n")
        index.append(f"| {res['item_id']} | {res['run_id']} | {kind} | {res.get('outcome')} | [{f.name}]({f.name}) |")
        n += 1
    (out / "README.md").write_text("\n".join(index) + "\n")
    print(f"wrote {n} audit pages to {out}")
    return 0 if n else 1
