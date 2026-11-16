#!/usr/bin/env python3
"""Tag every build in dataset/apps/*/builds/index.json with a tier.

core: needed by cases, calibration and the fast episode protocol:
      each bug's buggy and fixed build, plus each episode's start build
      (all episode bugs present).
full: the other episode subsets; only the full fix-and-retest protocol
      (`run_eval.py --protocol full`) installs them. Build on demand.

Re-run after adding bugs or episodes (aqb build runs it automatically).
"""
from __future__ import annotations

import json
from pathlib import Path

DATASET = Path(__file__).resolve().parents[1] / "dataset"


def core_builds(dataset: Path = DATASET) -> set[str]:
    man = json.loads((dataset / "manifest.json").read_text())
    core: set[str] = set()
    for b in man["bugs"]:
        core |= set(json.loads((dataset / "bugs" / b / "bug.json").read_text())["builds"].values())
    for e in man["episodes"]:
        ep = json.loads((dataset / "episodes" / e / "episode.json").read_text())
        core.add(ep["builds"]["1" * len(ep["bugs"])])
    return core


def apply(dataset: Path = DATASET) -> dict[str, int]:
    core = core_builds(dataset)
    n = {"core": 0, "full": 0}
    for idxp in sorted((dataset / "apps").glob("*/builds/index.json")):
        idx = json.loads(idxp.read_text())
        for bid, meta in idx.items():
            meta["tier"] = "core" if bid in core else "full"
            n[meta["tier"]] += 1
        idxp.write_text(json.dumps(idx, indent=2) + "\n")
    return n


if __name__ == "__main__":
    print(apply())
