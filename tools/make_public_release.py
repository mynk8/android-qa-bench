#!/usr/bin/env python3
"""Export a public copy of the benchmark without the answer material.

    python3 tools/make_public_release.py <out_dir>

Copies the repository to <out_dir> without private/ (diffs, forward-port patches, release-note
key, review corpora), without git metadata and local run directories, then checks the copy:
no private/ directory, no local home paths, and tools/leak_scan.py passes on its dataset/.
Exit code 1 if any check fails. The source tree is never modified.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.scrub_paths import HOME, TEXT_SUFFIXES  # noqa: E402

EXCLUDE = {"private", ".git", "runs", "__pycache__", ".DS_Store"}


def export(out: Path) -> list[str]:
    """Copy the release tree to `out` and return a list of problems found in the copy."""
    if out.exists():
        return [f"{out} already exists; choose a new directory"]
    shutil.copytree(ROOT, out, ignore=lambda d, names: [n for n in names if n in EXCLUDE])
    problems = []
    if (out / "private").exists():
        problems.append("private/ was copied")
    for f in out.rglob("*"):
        if "tests" in f.relative_to(out).parts:
            continue  # test fixtures use made-up home paths on purpose
        if f.is_file() and f.suffix in TEXT_SUFFIXES and HOME.search(f.read_text(errors="replace")):
            problems.append(f"home path in {f.relative_to(out)} (run tools/scrub_paths.py --write)")
    # the leak scan needs private/ (original fixes, code identifiers) to know what must not leak,
    # so it runs on the source tree; the copy holds the same dataset/
    scan = subprocess.run([sys.executable, str(ROOT / "tools" / "leak_scan.py")], capture_output=True, text=True)
    if scan.returncode != 0 or "0 leaks" not in scan.stdout:
        last = scan.stdout.strip().splitlines()[-1] if scan.stdout.strip() else "no output"
        problems.append(f"leak_scan: {last}")
    return problems


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    problems = export(Path(sys.argv[1]).resolve())
    for p in problems[:20]:
        print("FAIL", p)
    print("release OK" if not problems else f"{len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
