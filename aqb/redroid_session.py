"""Run calibration or benchmark jobs on a local redroid container (Android in Docker).

    with RedroidSession() as serial:         # starts a fresh container, connects adb
        dev = AdbDevice(serial=serial)
    # leaving the block deletes the container and everything in it

Reset model, matching a Limrun instance:
- Each session is a brand-new container with no volume. /data and /sdcard live in the
  container's writable layer, so `docker rm` throws away every app, seed file and
  setting. Nothing carries over from one run to the next.
- Within a session the harness resets per item, as on Limrun (prepare_app: clear the
  app, wipe all seed folders, re-seed, reset rotation and the shade).

The container runs under a memory cap (AQB_REDROID_MEM, default 3g) and binds adb to
127.0.0.1 only. Image: AQB_REDROID_IMAGE (default redroid/redroid:15.0.0_64only-latest).
"""
from __future__ import annotations

import os
import socket
import subprocess
import time
import uuid

IMAGE = os.environ.get("AQB_REDROID_IMAGE", "redroid/redroid:15.0.0_64only-latest")
MEM = os.environ.get("AQB_REDROID_MEM", "3g")
# redroid's init needs real root (binderfs, mounts): rootless Docker cannot run it.
DOCKER = ["docker", "--host", os.environ.get("AQB_DOCKER_HOST", "unix:///var/run/docker.sock")]

# Same screen as the Limrun phones and the AVD, so layouts and coordinates match.
BOOT_PROPS = [
    "androidboot.redroid_width=1080",
    "androidboot.redroid_height=2400",
    "androidboot.redroid_dpi=420",
    "androidboot.redroid_gpu_mode=guest",
    "androidboot.use_memfd=true",  # host kernel has no ashmem
]


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _adb(*args: str, timeout: float = 30) -> subprocess.CompletedProcess:
    """adb that never raises: `adb connect` blocks while the container's adbd is still starting."""
    try:
        return subprocess.run(["adb", *args], capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(["adb", *args], 124, "", "timeout")


class RedroidSession:
    def __init__(self, ready_timeout_s: float = 300, **_ignored):
        self.ready_timeout_s = ready_timeout_s
        self.name = f"aqb-redroid-{uuid.uuid4().hex[:8]}"
        self.port = _free_port()
        self.serial = f"127.0.0.1:{self.port}"
        self.started = False

    def __enter__(self) -> str:
        # `kill` (SIGTERM) must still remove the container: turn it into a normal exit so the
        # with-block's __exit__ runs.
        import signal
        import sys
        signal.signal(signal.SIGTERM, lambda *_: sys.exit(143))
        min_free = int(os.environ.get("AQB_REDROID_MIN_FREE_MB", "3000"))
        with open("/proc/meminfo") as fh:
            avail = next(int(l.split()[1]) // 1024 for l in fh if l.startswith("MemAvailable"))
        if avail < min_free:
            raise SystemExit(f"redroid: only {avail} MB RAM free (need {min_free}); not starting another container")
        # no --rm: a container that dies at boot keeps its logs until __exit__ removes it
        cmd = [*DOCKER, "run", "-d", "--privileged", "--name", self.name,
               "--memory", MEM, "--memory-swap", MEM,
               "-p", f"127.0.0.1:{self.port}:5555", IMAGE, *BOOT_PROPS]
        p = subprocess.run(cmd, capture_output=True, text=True)
        if p.returncode != 0:
            raise RuntimeError(f"redroid: docker run failed: {p.stderr.strip()[-400:]}")
        self.started = True
        deadline = time.monotonic() + self.ready_timeout_s
        while time.monotonic() < deadline:
            if not self._running():
                logs = subprocess.run([*DOCKER, "logs", "--tail", "30", self.name], capture_output=True, text=True)
                self.__exit__(None, None, None)
                raise RuntimeError(f"redroid container exited during boot: {(logs.stdout + logs.stderr)[-600:]}")
            _adb("connect", self.serial, timeout=10)
            r = _adb("-s", self.serial, "shell", "getprop", "sys.boot_completed", timeout=10)
            if r.stdout.strip() == "1":
                print(f"[redroid] container {self.name} ready at {self.serial}", flush=True)
                return self.serial
            time.sleep(2)
        self.__exit__(None, None, None)
        raise TimeoutError("redroid container did not finish booting in time")

    def _running(self) -> bool:
        r = subprocess.run([*DOCKER, "inspect", "-f", "{{.State.Running}}", self.name], capture_output=True, text=True)
        return r.stdout.strip() == "true"

    def __exit__(self, *exc) -> None:
        _adb("disconnect", self.serial, timeout=10)
        if self.started:
            # removing the container also removes its writable layer (/data, /sdcard)
            subprocess.run([*DOCKER, "rm", "-f", self.name], capture_output=True, text=True, timeout=120)
            self.started = False
