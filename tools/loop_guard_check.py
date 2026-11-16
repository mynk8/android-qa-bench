#!/usr/bin/env python3
"""Replay saved agent transcripts through agents/loop_guard.py's detector (no agent is run).

    python3 tools/loop_guard_check.py [runs/<name> ...]     (default: every run under runs/)

Prints, per transcript set, how many transcripts would have been killed (should be 0 for normal
runs) and the closest call: the lowest compression ratio and longest repeat seen. Also checks that
synthetic doom loops are caught.
"""
from __future__ import annotations

import glob
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "agents"))
import loop_guard as lg  # noqa: E402


def scan(log: Path) -> tuple[str | None, float, int]:
    tap, w = lg.TextTap(), lg.Watch()
    low, rep = 1.0, 0
    for line in log.open(errors="replace"):
        for s in tap.texts(line):
            v = w.feed(s)
            tail = re.sub(r"\s+", " ", w.buf)[-lg.WINDOW:]
            if len(tail) >= lg.WINDOW:
                low = min(low, lg.ratio(tail))
            pr = lg.periodic(tail)
            if pr:
                rep = max(rep, pr[1])
            if v:
                return v, low, rep
    return None, low, rep


def synthetic() -> None:
    cases = {
        "same word": "Let me think. " + "wait " * 400,
        "same sentence": "I will tap the button. " * 60,
        "near repeat with counter": "".join(f"Checking row {i % 3} of the list now, then the next row. " for i in range(120)),
        "dash fill": "思考中" + "——**" * 300,
        "short CJK sentence": "开始。" + "好。执行。" * 40,
        "normal prose": " ".join(f"The {w} screen shows item {i} with value {i * 7 % 13}." for i, w in
                                 zip(range(200), ["home", "list", "detail", "settings", "dialog"] * 40)),
    }
    for name, text in cases.items():
        w, v = lg.Watch(), None
        for i in range(0, len(text), 50):
            v = w.feed(text[i:i + 50]) or v
            if v:
                break
        print(f"  synthetic {name:26} -> {'KILLED: ' + v if v else 'not killed'}")


def main() -> int:
    runs = [Path(a) for a in sys.argv[1:]] or [Path(p) for p in sorted(glob.glob(str(ROOT / "runs" / "**" / "agent_logs"), recursive=True))]
    total = killed = 0
    worst_ratio, worst_rep = 1.0, 0
    for r in runs:
        d = r if r.name == "agent_logs" else r / "agent_logs"
        for log in sorted(d.glob("*.log")):
            v, low, rep = scan(log)
            total += 1
            worst_ratio, worst_rep = min(worst_ratio, low), max(worst_rep, rep)
            if v:
                killed += 1
                print(f"  WOULD KILL {log.relative_to(ROOT)}: {v}")
    print(f"{total} transcripts, {killed} would be killed; lowest compression ratio {worst_ratio:.3f} "
          f"(limit {lg.MAX_RATIO}), longest exact repeat {worst_rep} chars (limit {lg.MIN_REPEAT_CHARS})")
    synthetic()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
