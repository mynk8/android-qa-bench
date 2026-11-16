#!/usr/bin/env python3
"""Lint checks.py / repro.py / seed.py for non-determinism and Device-API use."""
from __future__ import annotations

import ast
import sys
from pathlib import Path

BANNED_CALLS = {"sleep", "time", "random", "uniform", "gauss", "choice", "randint"}
BANNED_ATTR = {"sleep", "time", "monotonic", "perf_counter", "random"}
BANNED_IMPORTS = {"random", "numpy", "requests"}


def lint_file(path: Path) -> list[str]:
    probs = []
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError as e:
        return [f"{path}: syntax error: {e}"]
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for a in n.names:
                if a.name.split(".")[0] in BANNED_IMPORTS:
                    probs.append(f"{path}:{n.lineno}: banned import {a.name}")
        if isinstance(n, ast.ImportFrom) and (n.module or "").split(".")[0] in BANNED_IMPORTS:
            probs.append(f"{path}:{n.lineno}: banned import {n.module}")
        if isinstance(n, ast.Call):
            name = None
            if isinstance(n.func, ast.Name):
                name = n.func.id
            elif isinstance(n.func, ast.Attribute):
                name = n.func.attr
            if name in BANNED_CALLS or name in BANNED_ATTR:
                # allow datetime/date parsing named "time" only if not time.sleep style — still flag
                probs.append(f"{path}:{n.lineno}: possibly non-deterministic call {name}()")
    return probs


def main(root: Path) -> int:
    probs = []
    for p in list(root.glob("apps/*/seed.py")) + list(root.glob("bugs/*/checks.py")) + list(root.glob("bugs/*/repro.py")) + [root.parent / "dataset_tools" / "check_helpers.py"]:
        probs.extend(lint_file(p))
    for p in probs:
        print("ERROR", p)
    print(f"{len(probs)} lint problems")
    return 1 if probs else 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]) if len(sys.argv) > 1 else Path("dataset")))
