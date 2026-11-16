#!/usr/bin/env python3
"""Run single-case clean/faulty evaluations.

    python tools/case_eval.py --case tasks-0001-faulty-spec --agent oracle --dry-run --out logs/eval/cases
    python tools/case_eval.py --all --agent oracle --dry-run
    python tools/case_eval.py --pair tasks-0001 --agent-cmd "..." --device my_sandbox:AdbDevice
"""
from __future__ import annotations

import argparse
import json
import shlex
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.eval_lib import (
    DATASET, OracleAgent, StdioAgent, opaque_id, apk_path, apply_action, dump_json,
    isolated_agent_cwd, isolated_agent_env, load_app, load_bug, load_case,
    load_device, load_manifest, merge_usage, new_run_id, prepare_app, resolve_agent_cmd,
    secret_access, usage_from_prices, annotate_report, start_seen,
)


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--case", help="case id, e.g. tasks-0001-faulty-spec")
    g.add_argument("--pair", help="bug id; runs the clean and faulty specified cases")
    g.add_argument("--all", action="store_true")
    ap.add_argument("--dataset", type=Path, default=DATASET)
    ap.add_argument("--agent", default=None, help="'oracle' or omit and use --agent-cmd")
    ap.add_argument("--agent-cmd", default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--device", default=None)
    ap.add_argument("--out", type=Path, default=ROOT / "logs" / "eval" / "cases")
    ap.add_argument("--model", default="dummy")
    ap.add_argument("--max-steps", type=int, default=80)
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--repeats", type=int, default=1)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--price-in", type=float, default=0.0)
    ap.add_argument("--price-out", type=float, default=0.0)
    ap.add_argument("--agent-cwd", type=Path, default=None)
    return ap.parse_args()


def make_agent(args):
    if args.agent_cmd:
        cwd = args.agent_cwd or isolated_agent_cwd()
        cmd = resolve_agent_cmd(shlex.split(args.agent_cmd), ROOT)
        return StdioAgent(cmd, cwd=cwd, env=isolated_agent_env())
    if (args.agent or "oracle") == "oracle":
        return OracleAgent(args.dataset)
    raise SystemExit(f"unknown --agent {args.agent!r}")


def list_cases(dataset: Path, pair: str | None, all_: bool, one: str | None) -> list[str]:
    if one:
        return [one]
    if pair:
        ids = []
        for suffix in ("clean-spec", "faulty-spec"):
            cid = f"{pair}-{suffix}"
            if (dataset / "cases" / cid / "case.json").is_file():
                ids.append(cid)
        if not ids:
            raise SystemExit(f"no clean/faulty-spec cases for {pair}")
        return ids
    man = load_manifest(dataset)
    if man.get("cases"):
        return list(man["cases"])
    return sorted(p.name for p in (dataset / "cases").iterdir() if p.is_dir())


def extract_verdict(msg: dict | None) -> dict | None:
    if not isinstance(msg, dict):
        return None
    if "verdict" in msg:
        return msg
    return None


def run_case(case_id: str, agent, device, *, dataset, dry_run, out_dir: Path,
             model="dummy", max_steps=80, run_id=None, seed=None,
             price_in=0.0, price_out=0.0) -> dict:
    case = load_case(case_id, dataset)
    bug = load_bug(case["bug_id"], dataset)
    app = load_app(bug["app_id"], dataset)
    build_id = case["_build_id"]
    truth = case["_true_verdict"]
    run_id = run_id or new_run_id()
    dest = out_dir / case_id / run_id
    dest.mkdir(parents=True, exist_ok=True)
    trace_path = dest / "trace.jsonl"

    def log_event(obj):
        with trace_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(obj, ensure_ascii=False) + "\n")

    if not dry_run:
        apk = apk_path(app["app_id"], build_id, dataset)
        if not apk.is_file():
            raise FileNotFoundError(f"APK missing: {apk} (build first, or pass --dry-run)")
    t0 = time.time()
    usage: dict = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "cost_usd": 0.0}
    reward_hack_hits: list[str] = []
    device.install(build_id)
    start_seen(device)
    device.launch(app["package"])
    prepare_app(device, app["app_id"], case.get("seed_id") or bug["seed_id"], dry_run, dataset)
    log_event({"event": "install", "build_id": build_id, "seed_id": case.get("seed_id") or bug["seed_id"]})
    agent.send({
        "type": "start",
        "kind": "case",
        "item_id": opaque_id(case_id),
        **({"_oracle_item_id": case_id} if isinstance(agent, OracleAgent) else {}),
        "brief": case["_agent_input"],
        "package": app["package"],
    })
    steps = 0
    status = "ok"
    agent_verdict = None
    raw = None
    while steps < max_steps:
        msg = agent.recv()
        steps += 1
        log_event({"event": "agent", "step": steps, "message": msg})
        if msg is None:
            status = "no_verdict" if getattr(agent, "quit_cleanly", lambda: False)() else "error"
            break
        hits = secret_access(msg)
        if hits:
            reward_hack_hits.extend(hits)
            log_event({"event": "reward_hack", "hits": hits})
            status = "ok"
            break
        typ = msg.get("type")
        if typ == "usage":
            usage = merge_usage(usage, msg, price_in=price_in, price_out=price_out)
            steps -= 1
            continue
        if typ == "action":
            agent.send(apply_action(device, msg))
            continue
        raw = msg
        agent_verdict = extract_verdict(msg)
        break
    else:
        status = "timeout"

    predicted = (agent_verdict or {}).get("verdict")
    verdict_correct = bool(predicted and predicted == truth)
    # A FAIL on a faulty build counts only when its failure description matches the bug
    # (same deterministic matcher as episodes, with the harness's quote check): a lucky FAIL
    # with a wrong or vague description is not a find.
    localized, loc_reason = None, None
    if predicted == "FAIL" and truth == "FAIL":
        from dataset_tools.matcher import load_key, match_key
        failure = (agent_verdict or {}).get("failure") or {}
        m = match_key(annotate_report(failure, device), load_key(dataset / "bugs" / case["bug_id"]),
                      case.get("_agent_input")) if isinstance(failure, dict) and failure else \
            {"match": False, "reason": "no_failure_details"}
        localized, loc_reason = bool(m["match"]), m["reason"]
    correct = verdict_correct and (truth != "FAIL" or bool(localized))
    fp = int(truth == "PASS" and predicted == "FAIL")
    fn = int(truth == "FAIL" and predicted != "FAIL")
    try:
        agent.send({"type": "end", "reason": "verdict" if agent_verdict else status, "status": status})
    except Exception:
        pass
    try:
        agent.close()
    except Exception:
        pass

    result = {
        "run_id": run_id,
        "item_id": case_id,
        "kind": "case",
        "app_id": bug["app_id"],
        "bug_id": case["bug_id"],
        "family": bug.get("family"),
        "hard_slice": bool(bug.get("hard_slice")),
        "variant": case.get("_variant"),
        "conditions": case.get("_conditions"),
        "model": model,
        "settings": {"dry_run": dry_run, "max_steps": max_steps, "seed": seed,
                     "price_in": price_in, "price_out": price_out},
        "status": status,
        "true_verdict": truth,
        "predicted_verdict": predicted,
        "verdict_correct": verdict_correct,
        "localized": localized,
        "localize_reason": loc_reason,
        "success": correct and status == "ok",
        "outcome": "success" if correct and status == "ok" else (status if status in ("timeout", "error", "no_verdict") else "wrong"),
        "false_positives": fp,
        "false_negatives": fn,
        "precision": None,
        "recall": None,
        "steps": steps,
        "reports": 1 if agent_verdict else 0,
        "verdicts_or_reports": [raw] if raw is not None else [],
        "harness_replies": [],
        "builds_installed": [build_id],
        "trace": str(trace_path.relative_to(ROOT)) if trace_path.is_relative_to(ROOT) else str(trace_path),
        "screens": "img/",
        "protected_changed": False,
        "elapsed_s": round(time.time() - t0, 3),
        "usage": usage_from_prices(usage, price_in=price_in, price_out=price_out),
        "reward_hack": bool(reward_hack_hits),
        "reward_hack_hits": reward_hack_hits,
        "bug_meta": {case["bug_id"]: {"family": bug.get("family"), "hard_slice": bool(bug.get("hard_slice"))}},
    }
    if result["reward_hack"]:
        result["success"] = False
        result["outcome"] = "reward_hack"
        result["protected_changed"] = True
    dump_json(dest / "result.json", result)
    return result


def main() -> int:
    args = parse_args()
    ids = list_cases(args.dataset, args.pair, args.all, args.case)
    args.out.mkdir(parents=True, exist_ok=True)
    results = []
    repeats = max(1, int(args.repeats or 1))
    for cid in ids:
        for i in range(repeats):
            device = load_device(args.device, args.dry_run)
            agent = make_agent(args)
            run_id = args.run_id if repeats == 1 else None
            seed = (args.seed + i) if args.seed is not None else i
            rec = run_case(cid, agent, device, dataset=args.dataset, dry_run=args.dry_run,
                           out_dir=args.out, model=args.model, max_steps=args.max_steps,
                           run_id=run_id, seed=seed,
                           price_in=args.price_in, price_out=args.price_out)
            results.append(rec)
            u = rec.get("usage") or {}
            print(f"{cid} truth={rec['true_verdict']} pred={rec['predicted_verdict']} "
                  f"outcome={rec['outcome']} steps={rec['steps']} seed={seed} "
                  f"cost_usd={u.get('cost_usd', 0):.4f}")
    dump_json(args.out / "index.json", {
        "runs": [{"item_id": r["item_id"], "run_id": r["run_id"], "outcome": r["outcome"],
                  "path": str(args.out / r["item_id"] / r["run_id"] / "result.json")}
                 for r in results]
    })
    return 0 if all(r["status"] in ("ok", "timeout") for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
