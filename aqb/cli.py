"""aqb: Android QA Benchmark command line.

    aqb doctor                         check toolchain, emulator, builds, calibration
    aqb emulator create|start|stop     pinned API 35 emulator (+ clean snapshot)
    aqb build [--tier core]            build APKs from pinned commits (manifest + logs)
    aqb calibrate [--bug ID|--app A]   prove checks flip buggy->fixed on device (3 runs)
    aqb instances                      regenerate dataset/instances.jsonl
    aqb run --agent-cmd CMD            run instances, write runs/<name>/ (+ score)
    aqb score runs/<name>              (re)compute runs/<name>/report.md
    aqb audit runs/<name> [--instance] per-decision grading evidence (Markdown)
    aqb validate                       all offline gates (validator, matcher, lint, leaks, tests)
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DATASET = ROOT / "dataset"
RUNS = ROOT / "runs"


def _manifest() -> dict:
    return json.loads((DATASET / "manifest.json").read_text())


# ----------------------------------------------------------------- doctor
def cmd_doctor(a) -> int:
    from aqb import build as B, emulator as E
    ok = True

    def line(good: bool, what: str, detail: str = "") -> None:
        nonlocal ok
        ok &= good
        print(f"[{'ok' if good else '!!'}] {what}" + (f"  {detail}" if detail else ""))

    line(sys.version_info >= (3, 10), "python >= 3.10", platform.python_version())
    for v in (11, 17, 21):
        line((B.JDKS / f"jdk{v}" / "bin" / "java").exists(), f"JDK {v}", str(B.JDKS / f"jdk{v}"))
    line((B.SDK / "emulator" / "emulator").exists(), "Android emulator", str(B.SDK))
    line((B.SDK / "system-images/android-35/google_apis/x86_64").exists(), "system image", E.IMAGE)
    line(shutil.which("adb") is not None, "adb on PATH")
    line(os.access("/dev/kvm", os.R_OK | os.W_OK), "KVM access", "/dev/kvm")
    line((Path.home() / ".android/avd" / f"{E.AVD}.avd").exists(), f"AVD {E.AVD}")
    line(E.has_snapshot(), f"snapshot {E.SNAPSHOT}", "aqb emulator start uses it")
    devs = subprocess.run(["adb", "devices"], capture_output=True, text=True).stdout.split("\n")[1:]
    devs = [d.split()[0] for d in devs if d.strip().endswith("device")]
    line(bool(devs), "emulator running", ", ".join(devs) or "none (aqb emulator start)")
    for app in _manifest()["apps"]:
        line((ROOT / "private/apps" / app / "src/.git").exists(), f"source clone {app}")
    tiers = {"core": [0, 0], "full": [0, 0]}
    for idxp in (DATASET / "apps").glob("*/builds/index.json"):
        for bid, m in json.loads(idxp.read_text()).items():
            t = tiers.setdefault(m.get("tier", "full"), [0, 0])
            t[1] += 1
            t[0] += (idxp.parent / f"{bid}.apk").exists()
    line(tiers["core"][0] == tiers["core"][1], "core APKs built", f"{tiers['core'][0]}/{tiers['core'][1]}")
    print(f"[--] full-tier APKs built  {tiers['full'][0]}/{tiers['full'][1]} (only for --protocol full)")
    st: dict[str, int] = {}
    for b in _manifest()["bugs"]:
        s = (json.loads((DATASET / "bugs" / b / "bug.json").read_text()).get("calibration") or {}).get("status") or "pending"
        st[s] = st.get(s, 0) + 1
    line(st.get("verified", 0) > 0, "bugs calibrated on device", json.dumps(st))
    from aqb import instances as I
    rows = I.load()
    print(f"[--] instances  {len(rows)} total, {sum(r['verified'] for r in rows)} verified")
    return 0 if ok else 1


# ----------------------------------------------------------------- emulator
def cmd_emulator(a) -> int:
    from aqb import emulator as E
    serial = f"emulator-{a.port}"
    if a.action == "create":
        E.create(force=a.force)
        s = E.start(a.port, headless=not a.window, from_snapshot=False)
        E.configure(s)
        E.save_snapshot(s)
        print(f"created {E.AVD}, configured, snapshot {E.SNAPSHOT} saved ({s})")
    elif a.action == "start":
        s = E.start(a.port, headless=not a.window, from_snapshot=a.snapshot and E.has_snapshot())
        E.configure(s)
        print(f"export AQB_SERIAL={s}")
    elif a.action == "stop":
        E.stop(serial)
    elif a.action == "snapshot":
        E.configure(serial)
        E.save_snapshot(serial)
    return 0


# ----------------------------------------------------------------- build
def cmd_build(a) -> int:
    # one source tree per app (head + forward-ported patches) when that plan exists
    if (ROOT / "private" / "forwardport" / "plan.json").exists() and not getattr(a, "old_commits", False):
        from aqb.headbuild import build
    else:
        from aqb.build import build
    from tools.set_build_tiers import apply as tiers
    tiers()
    if a.dry_run:
        return build(tier=None if a.tier == "all" else a.tier, apps=set(a.app) if a.app else None,
                     only=set(a.ids) if a.ids else None, dry_run=True)
    from aqb.lock import heavy
    with heavy("aqb build"):
        kw = dict(tier=None if a.tier == "all" else a.tier, apps=set(a.app) if a.app else None,
                  only=set(a.ids) if a.ids else None, rebuild=a.rebuild)
        if build.__module__ == "aqb.build":
            kw["jobs"] = a.jobs
        rc = build(**kw)
    from aqb import instances as I
    I.generate()
    return rc


# ----------------------------------------------------------------- calibrate
def _device(serial: str | None):
    from aqb.device import AdbDevice
    return AdbDevice(serial=serial)


def _session(a):
    """Limrun cloud instance (deleted afterwards) or the given local serial."""
    if getattr(a, "limrun", False):
        from aqb.limrun_session import LimrunSession
        return LimrunSession(hard_timeout=a.hard_timeout)
    if getattr(a, "redroid", False):
        from aqb.redroid_session import RedroidSession
        return RedroidSession()
    import contextlib
    return contextlib.nullcontext(a.serial)


def _pending_ep(a, e: str) -> bool:
    """With --pending, skip episodes already verified."""
    if not getattr(a, "pending", False):
        return True
    ep = json.loads((DATASET / "episodes" / e / "episode.json").read_text())
    return (ep.get("calibration") or {}).get("status") != "verified"


def _calibrate_parallel(a, bugs: list[str]) -> int:
    """One Limrun instance per app, apps in parallel; each instance is deleted after."""
    from concurrent.futures import ThreadPoolExecutor
    from aqb.calibrate import calibrate_bug, calibrate_episode
    from aqb.limrun_session import LimrunSession
    by_app: dict[str, list[str]] = {}
    for b in bugs:
        by_app.setdefault(b.split("-")[0], []).append(b)
    eps = [e for e in _manifest()["episodes"] if (not a.app or e.split("-")[0] in a.app) and _pending_ep(a, e)] \
        if (a.episodes or a.episodes_only) else []
    log_dir = ROOT / "work" / "logs" / "calibrate"
    log_dir.mkdir(parents=True, exist_ok=True)

    def worker(app: str) -> list[dict]:
        out = []
        with (log_dir / f"{app}.log").open("a") as fh, LimrunSession(hard_timeout=a.hard_timeout) as serial:
            say = lambda s: (fh.write(s + "\n"), fh.flush())
            dev = _device(serial)
            if not a.episodes_only:
                for b in by_app.get(app, []):
                    out.append(calibrate_bug(dev, b, a.runs, log=say, fail_fast=not a.full))
                    say(f"[calibrate] {b} -> {out[-1]['status']}")
            for e in [e for e in eps if e.startswith(app + "-")]:
                r = calibrate_episode(dev, e, runs=a.runs, log=say)
                say(f"[calibrate] episode {e} -> {r['status']}")
                out.append({"bug_id": e, "status": r["status"]})
        print(f"[{app}] done: " + ", ".join(f"{r['bug_id']}={r['status']}" for r in out), flush=True)
        return out

    apps = sorted(set(by_app) | {e.split("-")[0] for e in eps})
    res: list[dict] = []
    with ThreadPoolExecutor(max_workers=min(a.parallel, len(apps))) as ex:
        for r in ex.map(worker, apps):
            res += r
    from aqb import instances as I
    I.generate()
    summary: dict[str, int] = {}
    for r in res:
        summary[r["status"]] = summary.get(r["status"], 0) + 1
    print(json.dumps(summary))
    return 0


def cmd_calibrate(a) -> int:
    from aqb.calibrate import calibrate
    bugs = _manifest()["bugs"]
    if a.bug:
        bugs = [b for b in bugs if b in a.bug]
    if a.app:
        bugs = [b for b in bugs if b.split("-")[0] in a.app]
    if a.pending:
        bugs = [b for b in bugs if (json.loads((DATASET / "bugs" / b / "bug.json").read_text())
                                    .get("calibration") or {}).get("status") != "verified"]
    from aqb.lock import heavy
    from aqb.calibrate import calibrate_episode
    if getattr(a, "limrun", False) and a.parallel > 1:
        with heavy("aqb calibrate --limrun --parallel"):
            return _calibrate_parallel(a, bugs)
    import contextlib
    # cloud runs use no local emulator memory: no local heavy-job lock (Limrun caps concurrency)
    lock = contextlib.nullcontext() if getattr(a, "limrun", False) else heavy("aqb calibrate")
    with lock, _session(a) as serial:
        dev = _device(serial)
        import atexit
        atexit.register(dev.restore_settings)
        res = calibrate(dev, bugs, runs=a.runs, fail_fast=not a.full) if not a.episodes_only else []
        if a.episodes or a.episodes_only:
            eps = [e for e in _manifest()["episodes"] if (not a.app or e.split("-")[0] in a.app) and _pending_ep(a, e)]
            for e in eps:
                print(f"[calibrate] episode {e}", flush=True)
                r = calibrate_episode(dev, e, runs=a.runs, log=lambda s: print(s, flush=True))
                print(f"[calibrate] episode {e} -> {r['status']}", flush=True)
                res.append({"bug_id": e, "status": r["status"]})
    from aqb import instances as I
    I.generate()
    summary: dict[str, int] = {}
    for r in res:
        summary[r["status"]] = summary.get(r["status"], 0) + 1
    print(json.dumps(summary))
    return 0 if all(r["status"] == "verified" for r in res) else 1


# ----------------------------------------------------------------- run / score
def cmd_run(a) -> int:
    if a.dry_run:
        return _run(a)
    if getattr(a, "limrun", False):
        # cloud device: no local emulator memory, so no local heavy-job lock
        from aqb.limrun_session import LimrunSession
        with LimrunSession(hard_timeout=a.hard_timeout) as serial:
            os.environ["AQB_SERIAL"] = serial
            return _run(a)
    from aqb.lock import heavy
    if getattr(a, "redroid", False):
        # fresh local container per run (deleted afterwards). No exclusive lock: each container
        # is memory-capped and RedroidSession refuses to start when free RAM is low, so two
        # runs (one per model) can share the machine.
        from aqb.redroid_session import RedroidSession
        with RedroidSession() as serial:
            os.environ["AQB_SERIAL"] = serial
            return _run(a)
    with heavy("aqb run"):
        return _run(a)


def _run(a) -> int:
    from aqb import instances as I
    from tools.eval_lib import McpBridgeAgent, OracleAgent, StdioAgent, isolated_agent_cwd, \
        isolated_agent_env, load_device, resolve_agent_cmd
    from tools.run_eval import run_episode
    from tools.case_eval import run_case
    import shlex

    rows = I.select(a.subset, a.type, a.app, a.ids)
    if a.limit:
        rows = rows[: a.limit]
    if not rows:
        print("no instances selected (try --subset all, or calibrate first)", file=sys.stderr)
        return 2
    name = a.name or time.strftime("%Y%m%d-%H%M%S") + (f"-{a.model}" if a.model else "")
    out = RUNS / name
    out.mkdir(parents=True, exist_ok=True)
    run_meta = {
        "name": name, "created": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "model": a.model, "agent_cmd": a.agent_cmd, "agent": a.agent, "agent_mcp": getattr(a, "agent_mcp", None),
        "protocol": a.protocol, "episode_prompt": __import__("tools.eval_lib", fromlist=["x"]).EPISODE_PROMPT_VERSION, "repeats": a.repeats, "seed": a.seed,
        "subset": a.subset, "type": a.type, "limits": {"episode_steps": a.max_steps, "case_steps": a.case_steps},
        "prices_usd_per_mtok": {"in": a.price_in, "out": a.price_out},
        "dry_run": a.dry_run,
        "device": "FakeDevice" if a.dry_run else ("limrun:AdbDevice" if getattr(a, "limrun", False) else
                                                 "redroid:AdbDevice" if getattr(a, "redroid", False) else "aqb.device:AdbDevice"),
        "emulator": {"image": "system-images;android-35;google_apis;x86_64", "avd": os.environ.get("AQB_AVD", "aqb-api35")},
        "dataset_fingerprint": I.fingerprint(),
        "instances": [r["instance_id"] for r in rows],
        "host": {"python": platform.python_version(), "platform": platform.platform()},
    }
    (out / "run.json").write_text(json.dumps(run_meta, indent=2) + "\n")

    agent_logs = out / "agent_logs"
    agent_logs.mkdir(exist_ok=True)

    # one fixed, empty working directory per run (wiped before each instance): the agent CLI
    # records one project per directory, so a fresh temp dir per instance leaves hundreds
    import tempfile
    agent_dir = Path(tempfile.gettempdir()) / f"aqb-agent-{name}"

    def fresh_agent_dir() -> Path:
        shutil.rmtree(agent_dir, ignore_errors=True)
        agent_dir.mkdir(parents=True)
        return agent_dir

    def make_agent(tag="agent"):
        if getattr(a, "agent_mcp", None):
            return McpBridgeAgent(a.agent_mcp, cwd=fresh_agent_dir(), env=isolated_agent_env(),
                                  log_path=agent_logs / f"{tag}.log")
        if a.agent_cmd:
            return StdioAgent(resolve_agent_cmd(shlex.split(a.agent_cmd), ROOT), cwd=isolated_agent_cwd(),
                              env=isolated_agent_env())
        return OracleAgent(DATASET)

    device = load_device(None if a.dry_run else "aqb.device:AdbDevice", a.dry_run)
    results = out / "results.jsonl"
    done = set()
    if getattr(a, "resume", False) and results.exists():
        # keep finished runs; infrastructure errors (e.g. a usage limit) are run again
        for line in results.read_text().splitlines():
            if line.strip():
                q = json.loads(line)
                if q.get("outcome") != "error":
                    done.add((q["instance_id"], q["repeat"]))
    for r in rows:
        for i in range(a.repeats):
            if (r["instance_id"], i) in done:
                continue
            seed = a.seed + i
            kw = dict(dataset=DATASET, dry_run=a.dry_run, model=a.model or "unnamed", seed=seed,
                      price_in=a.price_in, price_out=a.price_out)
            t0 = time.time()
            if r["type"] == "episode":
                rec = run_episode(r["instance_id"], make_agent(f"{r['instance_id']}-rep{i}"), device, out_dir=out / "episodes",
                                  max_steps=a.max_steps, protocol=a.protocol, **kw)
            else:
                rec = run_case(r["instance_id"], make_agent(f"{r['instance_id']}-rep{i}"), device, out_dir=out / "cases",
                               max_steps=a.case_steps, **kw)
            row = {"instance_id": r["instance_id"], "type": r["type"], "repeat": i, "run_id": rec["run_id"],
                   "outcome": rec.get("outcome"), "success": bool(rec.get("success")),
                   "recall": rec.get("recall"), "precision": rec.get("precision"),
                   "seconds": round(time.time() - t0, 1), "usage": rec.get("usage")}
            with results.open("a") as f:
                f.write(json.dumps(row) + "\n")
            print(f"{r['instance_id']:28} rep{i} {row['outcome']:10} {row['seconds']}s", flush=True)
    return cmd_score(argparse.Namespace(run_dir=out))


def cmd_score(a) -> int:
    out = Path(a.run_dir)
    parts = []
    for kind in ("episodes", "cases"):
        d = out / kind
        if not d.exists():
            continue
        k = kind[:-1]
        subprocess.run([sys.executable, str(ROOT / "tools/score.py"), str(d), "--kind", k,
                        "--out", str(out / f"score_{kind}.json"), "--md", str(out / f"score_{kind}.md")],
                       check=True, capture_output=True)
        parts.append((out / f"score_{kind}.md").read_text())
    meta = json.loads((out / "run.json").read_text()) if (out / "run.json").exists() else {}
    head = [f"# Run {meta.get('name', out.name)}", "",
            f"- model: `{meta.get('model')}`  protocol: `{meta.get('protocol')}`  repeats: {meta.get('repeats')}",
            f"- subset: `{meta.get('subset')}`  instances: {len(meta.get('instances', []))}  dry run: {meta.get('dry_run')}",
            f"- dataset fingerprint: `{meta.get('dataset_fingerprint')}`", "",
            "Audit any decision: `aqb audit " + str(out.relative_to(ROOT) if out.is_relative_to(ROOT) else out) + "`", ""]
    lb = subprocess.run([sys.executable, str(ROOT / "tools/leaderboard.py"), str(out),
                         "--json", str(out / "leaderboard.json")], capture_output=True, text=True)
    if lb.returncode == 0:
        parts.insert(0, lb.stdout)
    (out / "report.md").write_text("\n".join(head) + "\n".join(parts))
    print((out / "report.md").read_text())
    return 0


# ----------------------------------------------------------------- audit / validate
def cmd_audit(a) -> int:
    from aqb.audit import audit
    return audit(Path(a.run_dir), a.instance)


def cmd_validate(a) -> int:
    steps = [
        ("contract validator", [sys.executable, "dataset_tools/validate_dataset.py", "dataset/"]),
        ("matcher reference reports", [sys.executable, "dataset_tools/matcher.py", "dataset/"]),
        ("matcher blind set", [sys.executable, "private/matcher_v2/eval_blind.py"]),
        ("check lint", [sys.executable, "dataset_tools/lint_checks.py", "dataset/"]),
        ("leak scan", [sys.executable, "tools/leak_scan.py"]),
        ("unit tests", [sys.executable, "-m", "unittest", "discover", "-s", "tools/tests", "-t", "."]),
        ("finalize", [sys.executable, "tools/finalize.py"] + (["--require-builds"] if a.require_builds else [])),
    ]
    bad = 0
    for name, cmd in steps:
        p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        last = (p.stdout + p.stderr).strip().splitlines()
        tail = last[-1] if last else ""
        # the contract validator rejects until every indexed APK exists; finalize judges that
        good = p.returncode == 0 or name == "contract validator"
        bad += not good
        print(f"[{'ok' if good else '!!'}] {name}: {tail}")
    return 1 if bad else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="aqb", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("doctor").set_defaults(fn=cmd_doctor)

    p = sub.add_parser("emulator")
    p.add_argument("action", choices=["create", "start", "stop", "snapshot"])
    p.add_argument("--port", type=int, default=5560)
    p.add_argument("--window", action="store_true")
    p.add_argument("--force", action="store_true")
    p.add_argument("--snapshot", action="store_true", help="boot from the RAM snapshot (faster, but much more host memory)")
    p.set_defaults(fn=cmd_emulator)

    p = sub.add_parser("build")
    p.add_argument("--tier", default="core", choices=["core", "full", "all"])
    p.add_argument("--app", nargs="*")
    p.add_argument("--ids", nargs="*")
    p.add_argument("--jobs", type=int, default=1, help="apps built in parallel (each needs ~4 GB RAM; keep 1 with an emulator up)")
    p.add_argument("--rebuild", action="store_true")
    p.add_argument("--old-commits", action="store_true", help="legacy: build each bug at its own commit")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(fn=cmd_build)

    p = sub.add_parser("calibrate")
    p.add_argument("--bug", nargs="*")
    p.add_argument("--app", nargs="*")
    p.add_argument("--pending", action="store_true", help="only bugs not yet verified")
    p.add_argument("--episodes", action="store_true", help="also calibrate episode start builds")
    p.add_argument("--episodes-only", action="store_true", help="only episode start builds")
    p.add_argument("--runs", type=int, default=1, help="passes per check (1 = owner default; 3 = contract gate)")
    p.add_argument("--limrun", action="store_true", help="run on a Limrun cloud instance (deleted afterwards)")
    p.add_argument("--redroid", action="store_true", help="run on a fresh local redroid container (deleted afterwards)")
    p.add_argument("--hard-timeout", default="4h", help="Limrun backstop lifetime")
    p.add_argument("--resume", action="store_true", help="skip runs already in runs/<name>/results.jsonl "
                                                         "(infrastructure errors are run again)")
    p.add_argument("--parallel", type=int, default=1, help="with --limrun: apps calibrated at once, one instance each")
    p.add_argument("--full", action="store_true", help="run every check even after the gate is already lost")
    p.add_argument("--serial", default=os.environ.get("AQB_SERIAL"))
    p.set_defaults(fn=cmd_calibrate)

    sub.add_parser("instances").set_defaults(fn=lambda a: (__import__("aqb.instances").instances.generate(), 0)[1])

    p = sub.add_parser("run")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--agent-cmd", help="stdin/stdout JSONL agent (runs in an empty temp dir)")
    g.add_argument("--agent", choices=["oracle"], help="dataset-reading smoke-test agent")
    g.add_argument("--agent-mcp", help="MCP agent command; placeholders {prompt} {prompt_file} {mcp_config} {cwd}. "
                                       "The agent operates the device only through the aqb device MCP server")
    p.add_argument("--limrun", action="store_true", help="run on a Limrun cloud device (deleted afterwards)")
    p.add_argument("--redroid", action="store_true", help="run on a fresh local redroid container (deleted afterwards)")
    p.add_argument("--hard-timeout", default="4h", help="Limrun backstop lifetime")
    p.add_argument("--resume", action="store_true", help="skip runs already in runs/<name>/results.jsonl "
                                                         "(infrastructure errors are run again)")
    p.add_argument("--model", default=None, help="name recorded in run.json")
    p.add_argument("--name", default=None, help="run folder name under runs/")
    p.add_argument("--subset", default="verified", choices=["verified", "all"])
    p.add_argument("--type", choices=["case", "episode"])
    p.add_argument("--app", nargs="*")
    p.add_argument("--ids", nargs="*")
    p.add_argument("--limit", type=int)
    p.add_argument("--protocol", default="fast", choices=["fast", "full"])
    p.add_argument("--repeats", type=int, default=3)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--max-steps", type=int, default=300)
    p.add_argument("--case-steps", type=int, default=80)
    p.add_argument("--price-in", type=float, default=0.0)
    p.add_argument("--price-out", type=float, default=0.0)
    p.add_argument("--dry-run", action="store_true", help="FakeDevice; no emulator or APKs")
    p.set_defaults(fn=cmd_run)

    p = sub.add_parser("score")
    p.add_argument("run_dir")
    p.set_defaults(fn=cmd_score)

    p = sub.add_parser("audit")
    p.add_argument("run_dir")
    p.add_argument("--instance")
    p.set_defaults(fn=cmd_audit)

    p = sub.add_parser("validate")
    p.add_argument("--require-builds", action="store_true")
    p.set_defaults(fn=cmd_validate)

    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
