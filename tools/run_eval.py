#!/usr/bin/env python3
"""Run one or more fail-to-pass episodes against a QA agent.

    python tools/run_eval.py --episode tasks-E01 --agent oracle --dry-run --out logs/eval
    python tools/run_eval.py --all --agent-cmd "python tools/dummy_agent.py --oracle" --dry-run
    python tools/run_eval.py --episode tasks-E01 --agent-cmd "..." --device my_sandbox:AdbDevice

--dry-run uses FakeDevice and does not require APKs. The team runs without
--dry-run once builds exist and a real Device is passed.
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

from dataset_tools.matcher import match_key
from tools.eval_lib import (
    DATASET, OracleAgent, StdioAgent, opaque_id,
    annotate_report, apk_path, apply_action, classify_report, dump_json, format_reply, start_seen,
    isolated_agent_cwd, isolated_agent_env, load_app, load_bug_keys, prepare_app,
    load_case_texts, load_device, load_episode, load_manifest, mask_for,
    merge_usage, new_run_id, present_on, resolve_agent_cmd, secret_access,
    usage_from_prices,
)


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--episode", help="episode id, e.g. tasks-E01")
    g.add_argument("--all", action="store_true", help="run every episode in the manifest")
    ap.add_argument("--dataset", type=Path, default=DATASET)
    ap.add_argument("--agent", default=None, help="'oracle' (dataset-cheating dummy) or omit and use --agent-cmd")
    ap.add_argument("--agent-cmd", default=None, help="command for a stdin/stdout JSONL agent")
    ap.add_argument("--dry-run", action="store_true", help="FakeDevice; no APKs or emulator")
    ap.add_argument("--device", default=None, help="module:Class Device implementation (ignored with --dry-run)")
    ap.add_argument("--out", type=Path, default=ROOT / "logs" / "eval")
    ap.add_argument("--model", default="dummy")
    ap.add_argument("--max-steps", type=int, default=300)
    ap.add_argument("--max-reports", type=int, default=None)
    ap.add_argument("--claim", default="none", choices=("none", "developer"))
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--repeats", type=int, default=1, help="independent runs per episode (seeds run-id)")
    ap.add_argument("--seed", type=int, default=0, help="base seed recorded in settings; repeat i uses seed+i")
    ap.add_argument("--price-in", type=float, default=0.0, help="USD per million input tokens")
    ap.add_argument("--protocol", default="fast", choices=("fast", "full"),
                    help="fast: one start build, report-only (core builds); full: fix-and-retest loop (all builds)")
    ap.add_argument("--price-out", type=float, default=0.0, help="USD per million output tokens")
    ap.add_argument("--agent-cwd", type=Path, default=None,
                    help="agent working dir (default: empty isolated temp; not the dataset root)")
    return ap.parse_args()


def make_agent(args: argparse.Namespace):
    if args.agent_cmd:
        cwd = args.agent_cwd or isolated_agent_cwd()
        cmd = resolve_agent_cmd(shlex.split(args.agent_cmd), ROOT)
        return StdioAgent(cmd, cwd=cwd, env=isolated_agent_env())
    if (args.agent or "oracle") == "oracle":
        return OracleAgent(args.dataset)
    raise SystemExit(f"unknown --agent {args.agent!r}; use 'oracle' or --agent-cmd")


def install_subset(device, episode, app, unfixed, build_n, dry_run, dataset, seed=True) -> dict:
    bugs = list(episode["bugs"])
    mask = mask_for(bugs, unfixed)
    build_id = episode["builds"][mask]
    if not dry_run:
        apk = apk_path(app["app_id"], build_id, dataset)
        if not apk.is_file():
            raise FileNotFoundError(f"APK missing: {apk} (build first, or pass --dry-run)")
    pkg = app["package"]
    if getattr(device, "package", None) or any(e[0] == "launch" for e in getattr(device, "log", [])):
        device.force_stop(pkg)
    device.install(build_id)
    device.launch(pkg)
    if seed:
        prepare_app(device, app["app_id"], episode["seed_id"], dry_run, dataset)
    return {
        "n": build_n,
        "build_id": build_id,
        "mask": mask,
        "unfixed": sorted(unfixed),
        "present": sorted(present_on(episode, unfixed)),
    }


def score_episode(episode, unfixed, found, tp, fp, leftover_n, already_n, outcome, steps, n_reports,
                  required=None) -> dict:
    bugs = list(episode["bugs"])
    req = list(required) if required is not None else bugs
    n = len(req)
    recall = (len(found & set(req)) / n) if n else 1.0
    denom = tp + fp
    precision = (tp / denom) if denom else 1.0
    return {
        "success": outcome == "success",
        "outcome": outcome,
        "bugs": bugs,
        "found": sorted(found),
        "required": sorted(req),
        "missed": sorted(set(req) - found),
        "true_positives": tp,
        "false_positives": fp,
        "leftover_reports": leftover_n,
        "already_fixed_reports": already_n,
        "reports": n_reports,
        "steps": steps,
        "precision": precision,
        "recall": recall,
        "unfixed_at_end": sorted(unfixed),
    }


def run_episode(episode_id: str, agent, device, *, dataset, dry_run, out_dir: Path,
                model="dummy", max_steps=300, max_reports=None, claim="none",
                run_id=None, seed=None, price_in=0.0, price_out=0.0, protocol="full") -> dict:
    """protocol "full": every hit installs the next subset build (fix-and-retest loop).
    protocol "fast": one install of the all-present start build; a hit is logged,
    no new build ships, and success means every bug observable on the start
    build was reported before a PASS sign-off. Fast needs only core-tier builds."""
    if protocol not in ("full", "fast"):
        raise ValueError(f"protocol must be full or fast, not {protocol!r}")
    episode = load_episode(episode_id, dataset)
    app = load_app(episode["app_id"], dataset)
    start_seen(device)
    bugs = list(episode["bugs"])
    leftover = list(episode.get("known_leftover") or [])
    unfixed: set[str] = set(bugs)
    if max_reports is None:
        max_reports = 2 * len(bugs) + 3
    keys = load_bug_keys(bugs + leftover, dataset)
    case_texts = load_case_texts(bugs + leftover, dataset)

    run_id = run_id or new_run_id()
    dest = out_dir / episode_id / run_id
    dest.mkdir(parents=True, exist_ok=True)
    trace_path = dest / "trace.jsonl"
    traces = []

    def log_event(obj: dict) -> None:
        traces.append(obj)
        with trace_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(obj, ensure_ascii=False) + "\n")

    settings = {
        "dry_run": dry_run,
        "max_steps": max_steps,
        "max_reports": max_reports,
        "claim": claim,
        "model": model,
        "seed": seed,
        "price_in": price_in,
        "price_out": price_out,
        "protocol": protocol,
    }
    t0 = time.time()
    usage: dict = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "cost_usd": 0.0}
    reward_hack_hits: list[str] = []
    build_n = 1
    fixed_in: dict[str, int] = {}
    builds = [install_subset(device, episode, app, unfixed, build_n, dry_run, dataset)]
    # bugs a run must report: all of them (full), or those visible on the start build (fast)
    required = sorted(present_on(episode, unfixed)) if protocol == "fast" else sorted(bugs)
    log_event({"event": "install", "build": builds[-1]})

    agent.send({
        "type": "start",
        "kind": "episode",
        "item_id": opaque_id(episode_id),
        **({"_oracle_item_id": episode_id} if isinstance(agent, OracleAgent) else {}),
        "brief": episode["_brief"],
        "package": app["package"],
        "protocol": protocol,
    })
    log_event({"event": "brief", "item_id": episode_id})

    reports: list[dict] = []
    replies: list[str] = []
    funnel = {b: "missed_unreached" for b in bugs}
    found: set[str] = set()
    tp = fp = leftover_n = already_n = n_reports = steps = 0
    status = "ok"
    outcome = "timeout"
    sign_off_msg = None

    def finish(status_, outcome_) -> dict:
        nonlocal status, outcome
        status, outcome = status_, outcome_
        try:
            agent.send({"type": "end", "reason": outcome, "status": status})
        except Exception:
            pass
        try:
            agent.close()
        except Exception:
            pass
        metrics = score_episode(episode, unfixed, found, tp, fp, leftover_n, already_n,
                                outcome, steps, n_reports, required=required)
        result = {
            "run_id": run_id,
            "item_id": episode_id,
            "kind": "episode",
            "app_id": episode["app_id"],
            "model": model,
            "endpoint": "stdio" if not isinstance(agent, OracleAgent) else "oracle",
            "settings": settings,
            "status": status,
            "verdicts_or_reports": reports,
            "harness_replies": replies,
            "builds_installed": builds,
            "trace": str(trace_path.relative_to(ROOT)) if trace_path.is_relative_to(ROOT) else str(trace_path),
            "screens": "img/",
            "protected_changed": False,
            "funnel": funnel,
            "elapsed_s": round(time.time() - t0, 3),
            "usage": usage_from_prices(usage, price_in=price_in, price_out=price_out),
            "reward_hack": bool(reward_hack_hits),
            "reward_hack_hits": reward_hack_hits,
            "sign_off": sign_off_msg,
            **metrics,
        }
        if result.get("reward_hack"):
            result["success"] = False
            result["outcome"] = "reward_hack"
            result["protected_changed"] = True
        # attach family / hard-slice flags for score.py
        meta = {}
        for b in bugs:
            bug = json.loads((dataset / "bugs" / b / "bug.json").read_text(encoding="utf-8"))
            meta[b] = {"family": bug.get("family"), "hard_slice": bool(bug.get("hard_slice"))}
        result["bug_meta"] = meta
        dump_json(dest / "result.json", result)
        return result

    while True:
        if steps >= max_steps:
            log_event({"event": "limit", "which": "steps"})
            return finish("timeout", "timeout")
        msg = agent.recv()
        steps += 1
        log_event({"event": "agent", "step": steps, "message": msg})
        if msg is None:
            # an agent that stops by itself without signing off failed the episode; only a
            # crash or lost connection is an infrastructure error
            if getattr(agent, "exit_code", lambda: None)() == 4:
                # agents/loop_guard.py killed a degenerate repetition loop: an agent failure
                log_event({"event": "limit", "which": "doom_loop"})
                return finish("ok", "doom_loop")
            if getattr(agent, "quit_cleanly", lambda: False)():
                return finish("ok", "no_signoff")
            return finish("error", "error")
        hits = secret_access(msg)
        if hits:
            reward_hack_hits.extend(hits)
            log_event({"event": "reward_hack", "hits": hits})
            return finish("ok", "reward_hack")
        typ = msg.get("type")
        if typ == "usage":
            usage = merge_usage(usage, msg, price_in=price_in, price_out=price_out)
            steps -= 1
            continue
        if typ == "_unparseable" or typ not in (None, "bug_report", "sign_off", "action", "case_verdict"):
            if typ == "sign_off":
                pass
            elif typ == "action":
                pass
            elif typ in ("bug_report", None) and (msg.get("symptom_type") or msg.get("screen") is not None):
                typ = "bug_report"
            elif typ == "_unparseable":
                typ = "malformed_line"
            else:
                typ = typ or "unknown"

        if typ == "action":
            obs = apply_action(device, msg)
            agent.send(obs)
            continue

        if typ == "sign_off":
            sign_off_msg = msg
            remaining = present_on(episode, unfixed)
            done = set(required) <= found if protocol == "fast" else not unfixed
            if msg.get("verdict") == "PASS" and done:
                outc = "success"
            elif msg.get("verdict") == "PASS":
                outc = "wrong_pass"
            else:
                outc = "wrong_pass"
            log_event({"event": "sign_off", "verdict": msg.get("verdict"), "remaining": sorted(remaining),
                       "unfixed": sorted(unfixed), "outcome": outc})
            return finish("ok", outc)

        if typ != "bug_report":
            reply = format_reply("malformed")
            replies.append(reply)
            agent.send({"type": "developer_reply", "kind": "malformed", "text": reply, "build_n": build_n})
            log_event({"event": "reply", "kind": "malformed", "text": reply})
            if typ == "malformed_line":
                return finish("error", "error")
            continue

        n_reports += 1
        reports.append(msg)
        if n_reports > max_reports:
            log_event({"event": "limit", "which": "reports"})
            # its own outcome: the report limit, not the action cap, ended the session
            return finish("timeout", "report_cap")

        annotated = annotate_report(msg, device)
        result = classify_report(annotated, episode, unfixed, keys, case_texts, found)
        # audit trail: what the harness verified and how the matcher decided, per report
        log_event({"event": "scored", "report_n": n_reports,
                   "quote_seen": annotated.get("_quote_seen"), "kind": result.get("kind"),
                   "bugs": result.get("bugs"),
                   "per_bug": {b: match_key(annotated, keys[b]).get("reason") for b in keys}})
        kind = result.get("kind") or "no_match"
        hit_bugs = [b for b in (result.get("bugs") or []) if b in unfixed and b in present_on(episode, unfixed)]

        if protocol == "fast" and kind == "hit":
            new = [b for b in hit_bugs if b not in found]
            if not new and hit_bugs:
                already_n += 1
                reply = format_reply("duplicate")
                replies.append(reply)
                agent.send({"type": "developer_reply", "kind": "duplicate", "text": reply, "build_n": build_n})
                log_event({"event": "duplicate", "bugs": hit_bugs, "text": reply})
                continue
            if new:
                tp += 1
                for b in new:
                    found.add(b)
                    funnel[b] = "reported"
                reply = format_reply("hit_fast")
                replies.append(reply)
                agent.send({"type": "developer_reply", "kind": "hit", "text": reply, "build_n": build_n,
                            "bugs": new})
                log_event({"event": "hit", "bugs": new, "text": reply})
                continue

        if kind == "hit" and hit_bugs:
            tp += 1
            for b in hit_bugs:
                unfixed.discard(b)
                found.add(b)
                funnel[b] = "reported"
            build_n += 1
            for b in hit_bugs:
                fixed_in[b] = build_n
            rec = install_subset(device, episode, app, unfixed, build_n, dry_run, dataset)
            builds.append(rec)
            reply = format_reply("hit", build_n=build_n, claim=claim)
            replies.append(reply)
            agent.send({"type": "developer_reply", "kind": "hit", "text": reply, "build_n": build_n,
                        "bugs": hit_bugs})
            log_event({"event": "hit", "bugs": hit_bugs, "build": rec, "text": reply})
            continue

        if kind == "leftover_known":
            leftover_n += 1
            reply = format_reply("leftover_known")
            replies.append(reply)
            agent.send({"type": "developer_reply", "kind": "leftover_known", "text": reply, "build_n": build_n})
            log_event({"event": "leftover_known", "bugs": result.get("bugs"), "text": reply})
            continue

        if kind == "already_fixed":
            already_n += 1
            # use the earliest matching bug's build number
            ks = [fixed_in.get(b) for b in (result.get("bugs") or []) if b in fixed_in]
            k = min(ks) if ks else None
            reply = format_reply("already_fixed", fixed_in=k)
            replies.append(reply)
            agent.send({"type": "developer_reply", "kind": "already_fixed", "text": reply,
                        "build_n": build_n, "fixed_in": k})
            log_event({"event": "already_fixed", "bugs": result.get("bugs"), "text": reply})
            continue

        # no_match (including masked)
        fp += 1
        reply = format_reply("no_match")
        replies.append(reply)
        agent.send({"type": "developer_reply", "kind": "no_match", "text": reply, "build_n": build_n})
        log_event({"event": "no_match", "text": reply, "matcher": result})
        continue


def main() -> int:
    args = parse_args()
    dataset = args.dataset
    man = load_manifest(dataset)
    ids = list(man.get("episodes") or []) if args.all else [args.episode]
    out_dir = args.out
    out_dir.mkdir(parents=True, exist_ok=True)
    results = []
    repeats = max(1, int(args.repeats or 1))
    for eid in ids:
        for i in range(repeats):
            device = load_device(args.device, args.dry_run)
            agent = make_agent(args)
            run_id = args.run_id if repeats == 1 else None
            seed = (args.seed + i) if args.seed is not None else i
            try:
                rec = run_episode(
                    eid, agent, device, dataset=dataset, dry_run=args.dry_run,
                    out_dir=out_dir, model=args.model, max_steps=args.max_steps,
                    max_reports=args.max_reports, claim=args.claim, run_id=run_id,
                    seed=seed, price_in=args.price_in, price_out=args.price_out,
                    protocol=args.protocol,
                )
            except FileNotFoundError as exc:
                print(f"ERROR {eid}: {exc}", file=sys.stderr)
                return 2
            results.append(rec)
            u = rec.get("usage") or {}
            print(f"{eid} outcome={rec['outcome']} recall={rec['recall']:.2f} "
                  f"precision={rec['precision']:.2f} steps={rec['steps']} "
                  f"status={rec['status']} seed={seed} "
                  f"tokens={u.get('total_tokens', 0)} cost_usd={u.get('cost_usd', 0):.4f}")
    index = {"runs": [{"item_id": r["item_id"], "run_id": r["run_id"],
                       "outcome": r["outcome"], "path": str((out_dir / r["item_id"] / r["run_id"] / "result.json"))}
                      for r in results]}
    dump_json(out_dir / "index.json", index)
    return 0 if all(r["status"] in ("ok", "timeout") for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
