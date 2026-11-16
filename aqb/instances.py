"""dataset/instances.jsonl: one line per benchmark instance (the public index).

Agent-safe fields only (no verdicts, bug ids for cases, match keys or commits):
  instance_id, type (case|episode), app_id, package, prompt (path), seed_id,
  build_id (case) / start_build (episode), n_bugs (episode),
  verified (all needed builds built AND bugs device-calibrated), split.

A run selects instances from this file (`--subset verified|all`, `--type`,
`--app`, `--ids`). Gold answers stay in dataset/cases/*/case.json and
dataset/bugs/*/; the harness reads them, the agent never does.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "dataset"
PATH = DATASET / "instances.jsonl"


def _j(p: Path) -> dict:
    return json.loads(p.read_text())


def _built(app: str, bid: str, cache: dict) -> bool:
    if app not in cache:
        cache[app] = _j(DATASET / "apps" / app / "builds" / "index.json")
    m = cache[app].get(bid) or {}
    return m.get("sha256") not in (None, "UNBUILT") and (DATASET / "apps" / app / "builds" / f"{bid}.apk").exists()


def generate() -> list[dict]:
    man = _j(DATASET / "manifest.json")
    idx: dict = {}
    bugs = {b: _j(DATASET / "bugs" / b / "bug.json") for b in man["bugs"]}
    apps = {a: _j(DATASET / "apps" / a / "app.json") for a in man["apps"]}
    calibrated = {b: (v.get("calibration") or {}).get("status") == "verified" for b, v in bugs.items()}
    out = []
    for case_dir in sorted((DATASET / "cases").iterdir()):
        c = _j(case_dir / "case.json")
        b = bugs.get(c["bug_id"])
        if b is None:
            continue
        app = b["app_id"]
        out.append({
            "instance_id": c["case_id"], "type": "case", "app_id": app, "package": apps[app]["package"],
            "prompt": str((case_dir / c.get("agent_input", "agent_input.md")).relative_to(ROOT)),
            "seed_id": c.get("seed_id") or b["seed_id"], "build_id": c["_build_id"],
            "conditions": c.get("_conditions", {}),
            "verified": _built(app, c["_build_id"], idx) and calibrated[c["bug_id"]],
        })
    for e_id in man["episodes"]:
        e = _j(DATASET / "episodes" / e_id / "episode.json")
        start = e["builds"]["1" * len(e["bugs"])]
        out.append({
            "instance_id": e_id, "type": "episode", "app_id": e["app_id"], "package": apps[e["app_id"]]["package"],
            "prompt": str((DATASET / "episodes" / e_id / "brief.md").relative_to(ROOT)),
            "seed_id": e["seed_id"], "start_build": start, "n_bugs": len(e["bugs"]),
            "verified": _built(e["app_id"], start, idx) and all(calibrated[b] for b in e["bugs"])
                        and (e.get("calibration") or {}).get("status") == "verified",
        })
    for r in out:
        r["split"] = "test"
    PATH.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in out))
    return out


def load() -> list[dict]:
    if not PATH.exists():
        return generate()
    return [json.loads(l) for l in PATH.read_text().splitlines() if l.strip()]


def select(subset: str = "verified", type_: str | None = None, apps: list[str] | None = None,
           ids: list[str] | None = None) -> list[dict]:
    rows = load()
    if subset == "verified":
        rows = [r for r in rows if r["verified"]]
    if type_:
        rows = [r for r in rows if r["type"] == type_]
    if apps:
        rows = [r for r in rows if r["app_id"] in apps]
    if ids:
        want = set(ids)
        rows = [r for r in rows if r["instance_id"] in want]
    return rows


def fingerprint() -> str:
    """Hash of everything that decides a score: instances, keys, checks, builds, matcher."""
    h = hashlib.sha256()
    files = [PATH, ROOT / "dataset_tools" / "matcher.py", ROOT / "tools" / "run_eval.py", ROOT / "tools" / "case_eval.py"]
    files += sorted((DATASET / "bugs").glob("*/match.json")) + sorted((DATASET / "bugs").glob("*/checks.py"))
    files += sorted((DATASET / "apps").glob("*/builds/index.json"))
    for f in files:
        if f.exists():
            h.update(f.relative_to(ROOT).as_posix().encode())
            h.update(f.read_bytes())
    return h.hexdigest()[:16]
