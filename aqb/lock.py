"""One heavy job at a time (Gradle build, calibration, on-device run).

A build plus an emulator plus calibration together can exhaust 16 GB of RAM.
"""
from __future__ import annotations

import fcntl
import os
from contextlib import contextmanager
from pathlib import Path

LOCK = Path(__file__).resolve().parents[1] / "work" / ".heavy.lock"


@contextmanager
def heavy(name: str):
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    fh = LOCK.open("a+")
    try:
        fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        fh.seek(0)
        held = fh.read().strip() or "another aqb job"
        raise SystemExit(f"busy: {held} is running (one build/calibrate/run at a time). Wait for it to finish.")
    fh.seek(0)
    fh.truncate()
    fh.write(f"{name} (pid {os.getpid()})")
    fh.flush()
    try:
        yield
    finally:
        fh.seek(0)
        fh.truncate()
        fcntl.flock(fh, fcntl.LOCK_UN)
        fh.close()


def mem_available_gb() -> float:
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) / 1024 / 1024
    return 0.0
