#!/usr/bin/env python3
"""Replace absolute home-directory paths (/home/<user>, /Users/<user>) in released files with a
placeholder, so agent logs and traces do not carry a local user name.

    python3 tools/scrub_paths.py            # report what would change
    python3 tools/scrub_paths.py --write    # rewrite the files in place

Scope: results/, dataset/, docs/. private/ is answer material and is not released.
Only a path that starts at a path root is changed: /tmp/x/home/sessions stays as it is.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCOPE = ("results", "dataset", "docs")
TEXT_SUFFIXES = {".log", ".json", ".jsonl", ".md", ".txt", ".tex", ".py", ".sh", ".yml", ".csv"}
# the placeholder itself (/home/USER) is not a home path, so a second run changes nothing
HOME = re.compile(r"(?:(?<=file://)|(?<![\w./-]))/(home|Users)/(?!USER(?![A-Za-z0-9._-]))[A-Za-z0-9._-]+")


def scrub(text: str) -> tuple[str, int]:
    """Return the text with home paths replaced, and the number of replacements."""
    return HOME.subn(lambda m: f"/{m.group(1)}/USER", text)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    files = changes = 0
    for top in SCOPE:
        for f in sorted((ROOT / top).rglob("*")):
            if not f.is_file() or f.suffix not in TEXT_SUFFIXES:
                continue
            text = f.read_text(errors="surrogateescape")
            new, n = scrub(text)
            if n:
                files += 1
                changes += n
                if a.write:
                    f.write_text(new, errors="surrogateescape")
    print(f"{'scrubbed' if a.write else 'would scrub'} {changes} path(s) in {files} file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
