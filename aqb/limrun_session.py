"""Run calibration or benchmark jobs on a Limrun cloud Android instance.

    with LimrunSession() as serial:          # creates the instance, opens the adb tunnel
        dev = AdbDevice(serial=serial)       # ordinary adb from here on
    # leaving the block deletes the instance (hardTimeout is a backstop)

The API key is read from .env (LIMRUN_API_KEY or LIM_API_KEY) and handed to the
Node helper (aqb/limrun/session.mjs) through its environment only; it is never
printed or logged. Requires Node >= 20 and `npm install` in aqb/limrun.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "aqb" / "limrun" / "session.mjs"


def load_key() -> str:
    for name in ("LIM_API_KEY", "LIMRUN_API_KEY"):
        if os.environ.get(name):
            return os.environ[name]
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            m = re.match(r"\s*(LIMRUN_API_KEY|LIM_API_KEY)\s*=\s*(.*?)\s*$", line)
            if m and m.group(2).strip("'\""):
                return m.group(2).strip("'\"")
    raise SystemExit("No Limrun API key: put LIMRUN_API_KEY=... in .env")


class LimrunSession:
    def __init__(self, hard_timeout: str = "4h", inactivity: str = "15m", region: str | None = None,
                 ready_timeout_s: float = 600):
        self.args = ["--hard-timeout", hard_timeout, "--inactivity", inactivity] + (["--region", region] if region else [])
        self.ready_timeout_s = ready_timeout_s
        self.proc: subprocess.Popen | None = None
        self.info: dict = {}

    def __enter__(self) -> str:
        """Start an instance; when the account's concurrency limit is full, wait for a
        free slot (up to ~30 minutes) instead of failing."""
        deadline = time.monotonic() + 1800
        while True:
            try:
                return self._start()
            except RuntimeError as e:
                if "concurrency limit" not in str(e) or time.monotonic() > deadline:
                    raise
                print("[limrun] all instance slots busy; retrying in 30s", flush=True)
                time.sleep(30)

    def _start(self) -> str:
        if not (HELPER.parent / "node_modules" / "@limrun" / "api").exists():
            raise SystemExit("Limrun SDK missing: run `npm install` in aqb/limrun")
        env = dict(os.environ, LIM_API_KEY=load_key())
        log = (ROOT / "work" / "logs" / "limrun.log").open("a")
        self.proc = subprocess.Popen(["node", str(HELPER), *self.args], cwd=HELPER.parent, env=env,
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=log, text=True)
        deadline = time.monotonic() + self.ready_timeout_s
        while time.monotonic() < deadline:
            line = self.proc.stdout.readline()
            if not line:
                if self.proc.poll() is not None:
                    raise RuntimeError(f"Limrun helper exited ({self.proc.returncode}); see work/logs/limrun.log")
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            if msg.get("event") == "ready":
                self.info = msg
                print(f"[limrun] instance {msg['id']} ready at {msg['serial']} (region {msg.get('region')})", flush=True)
                return msg["serial"]
            if msg.get("event") == "error":
                self.__exit__(None, None, None)
                raise RuntimeError(f"Limrun: {msg.get('message')}")
        self.__exit__(None, None, None)
        raise TimeoutError("Limrun instance was not ready in time")

    def __exit__(self, *exc) -> None:
        p = self.proc
        if p and p.poll() is None:
            try:
                p.stdin.close()  # helper deletes the instance on stdin EOF
                p.wait(timeout=60)
            except Exception:
                p.terminate()
                try:
                    p.wait(timeout=30)
                except Exception:
                    p.kill()
        serial = self.info.get("serial")
        if serial:
            subprocess.run(["adb", "disconnect", serial], capture_output=True)
