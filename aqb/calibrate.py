"""Device calibration: prove each bug's checks discriminate buggy from fixed.

Gate (every run must agree):
    buggy build: target FAIL, held-out FAIL, preservation PASS
    fixed build: target PASS, held-out PASS, preservation PASS

Evidence, per bug:
    dataset/bugs/<id>/calibration.json   every check result of every run (+ screenshot sha256)
    artifacts/calibration/<id>/*.png     the screen at the end of each check
bug.json `calibration` gets the agreed booleans (validator format) and
status: verified | gate_failed | flaky | error.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "dataset"
SHOTS = ROOT / "artifacts" / "calibration"
GATE = {"buggy": (False, False, True), "fixed": (True, True, True)}


def _load_checks(bug_id: str):
    spec = importlib.util.spec_from_file_location(f"checks_{bug_id}", DATASET / "bugs" / bug_id / "checks.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _one(dev, bug_id, role, run, name, fn, params) -> dict:
    t0 = time.time()
    try:
        r = fn(dev, params)
        row = {"check": name, "passed": bool(r.passed), "tier": r.tier, "observed": r.observed}
        # a UI step the check could not reach is an error, never a verdict: on a buggy
        # build it would otherwise look like "bug detected"
        if isinstance(r.observed, dict) and r.observed.get("step_missing"):
            row["passed"] = None
            row["error"] = f"step_missing: {r.observed['step_missing']}"
    except Exception as e:  # device trouble is an error, never a verdict
        row = {"check": name, "passed": None, "error": f"{type(e).__name__}: {e}",
               "trace": traceback.format_exc()[-1500:]}
    row["seconds"] = round(time.time() - t0, 1)
    try:
        png = dev.screenshot()
        d = SHOTS / bug_id
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{role}-run{run}-{name}.png").write_bytes(png)
        row["screenshot_sha256"] = hashlib.sha256(png).hexdigest()
    except Exception:
        pass
    return row


def calibrate_bug(dev, bug_id: str, runs: int = 3, log=print, fail_fast: bool = True) -> dict:
    """fail_fast: stop at the first check that errors, or when the target check gives the
    wrong answer for its build; the gate cannot be met anyway, and broken bugs then cost
    ~1 minute instead of ~5. Rows run so far are kept as evidence."""
    bp = DATASET / "bugs" / bug_id / "bug.json"
    bug = json.loads(bp.read_text())
    mod = _load_checks(bug_id)
    params = bug.get("params", {})
    checks = [("target", mod.CHECKS["target"])]
    checks += [(f"held_out_{i}", f) for i, f in enumerate(mod.CHECKS["held_out"])]
    checks += [(f"preservation_{i}", f) for i, f in enumerate(mod.CHECKS["preservation"])]
    evidence = {"bug_id": bug_id, "runs": runs, "started": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "device": type(dev).__name__, "results": []}
    agreed: dict[str, dict] = {}
    status = "verified"
    stopped = None
    for role in ("buggy", "fixed"):
        if stopped:
            break
        build_id = bug["builds"][role]
        try:
            dev.install(build_id)
        except Exception as e:
            evidence["results"].append({"role": role, "error": f"install: {e}"})
            status = "error"
            log(f"  {bug_id} {role}: install failed: {e}")
            continue
        per_check: dict[str, list] = {n: [] for n, _ in checks}
        for run in range(1, runs + 1):
            if stopped:
                break
            for name, fn in checks:
                row = _one(dev, bug_id, role, run, name, fn, params)
                row.update(role=role, run=run, build_id=build_id)
                evidence["results"].append(row)
                per_check[name].append(row["passed"])
                log(f"  {bug_id} {role} run{run} {name}: {row['passed']} ({row['seconds']}s)"
                    + (f" {row.get('error') or row.get('observed', {}).get('step_missing', '')}" if not row["passed"] else ""))
                if fail_fast:
                    want_target = role == "fixed"
                    if row["passed"] is None:
                        stopped = f"{role} {name} errored"
                    elif name == "target" and row["passed"] is not want_target:
                        stopped = f"{role} target {row['passed']} (want {want_target})"
                    if stopped:
                        log(f"  {bug_id}: fail-fast stop: {stopped}")
                        evidence["fail_fast_stop"] = stopped
                        break
        vals = {}
        for name, got in per_check.items():
            if not got:  # not run (fail-fast stop)
                vals[name] = None
                if status == "verified":
                    status = "error" if "errored" in (stopped or "") else "gate_failed"
                continue
            if None in got:
                status = "error" if status == "verified" else status
                vals[name] = None
            elif len(set(got)) > 1:
                status = "flaky" if status == "verified" else status
                vals[name] = None
            else:
                vals[name] = got[0]
        agreed[role] = {
            "target": vals["target"],
            "held_out": [vals[n] for n, _ in checks if n.startswith("held_out")],
            "preservation": [vals[n] for n, _ in checks if n.startswith("preservation")],
        }
    # single-pass calibration is allowed (owner decision 2026-11-10); runs is recorded
    if status == "verified":
        for role, (t, h, p) in GATE.items():
            a = agreed.get(role)
            if not a or a["target"] is not t or any(x is not h for x in a["held_out"]) \
                    or any(x is not p for x in a["preservation"]):
                status = "gate_failed"
    evidence["status"] = status
    evidence["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    (DATASET / "bugs" / bug_id / "calibration.json").write_text(json.dumps(evidence, indent=2, default=str) + "\n")
    cal = {"runs": runs, "status": status, "evidence": "calibration.json"}
    for role in ("buggy", "fixed"):
        cal[role] = agreed.get(role, {"target": None, "held_out": [], "preservation": []})
    bug["calibration"] = cal
    bug["status"] = "verified" if status == "verified" else f"calibration_{status}"
    bp.write_text(json.dumps(bug, indent=2) + "\n")
    return {"bug_id": bug_id, "status": status, **{r: agreed.get(r) for r in ("buggy", "fixed")}}


def calibrate(dev, bug_ids: list[str], runs: int = 3, fail_fast: bool = True) -> list[dict]:
    out = []
    for b in bug_ids:
        t0 = time.time()
        print(f"[calibrate] {b}", flush=True)
        r = calibrate_bug(dev, b, runs, log=lambda s: print(s, flush=True), fail_fast=fail_fast)
        print(f"[calibrate] {b} -> {r['status']} ({time.time() - t0:.0f}s)", flush=True)
        out.append(r)
    return out


def calibrate_episode(dev, ep_id: str, runs: int = 3, log=print) -> dict:
    """Episode start build (all episode bugs applied): every bug that the episode marks
    observable on the start build must fail its target check in every run, and every
    bug's preservation checks must pass. Masked bugs (observable false) are skipped.
    Writes dataset/episodes/<id>/calibration.json and episode.json `calibration`."""
    ep_path = DATASET / "episodes" / ep_id / "episode.json"
    ep = json.loads(ep_path.read_text())
    bits = "1" * len(ep["bugs"])
    start = ep["builds"][bits]
    observable = [b for b, v in (ep.get("observable") or {}).get(bits, {}).items() if v]
    evidence = {"episode_id": ep_id, "start_build": start, "runs": runs, "results": []}
    status = "verified"
    try:
        dev.install(start)
    except Exception as e:
        status = "error"
        evidence["results"].append({"error": f"install: {e}"})
    if status == "verified":
        for b in ep["bugs"]:
            mod = _load_checks(b)
            params = json.loads((DATASET / "bugs" / b / "bug.json").read_text()).get("params", {})
            checks = ([("target", mod.CHECKS["target"])] if b in observable else []) + \
                     [(f"preservation_{i}", f) for i, f in enumerate(mod.CHECKS["preservation"])]
            for run in range(1, runs + 1):
                for name, fn in checks:
                    row = _one(dev, f"{ep_id}", b, run, name, fn, params)
                    row.update(bug=b, run=run)
                    evidence["results"].append(row)
                    want = False if name == "target" else True
                    ok = row["passed"] is want
                    log(f"  {ep_id} {b} run{run} {name}: {row['passed']} (want {want})")
                    if row["passed"] is None:
                        status = "error"
                    elif not ok and status == "verified":
                        status = "gate_failed"
    evidence["status"] = status
    (DATASET / "episodes" / ep_id / "calibration.json").write_text(json.dumps(evidence, indent=2, default=str) + "\n")
    ep["calibration"] = {"runs": runs, "status": status, "evidence": "calibration.json"}
    ep["status"] = "verified" if status == "verified" else f"calibration_{status}"
    ep_path.write_text(json.dumps(ep, indent=2, ensure_ascii=False) + "\n")
    return {"episode_id": ep_id, "status": status}
