"""Pinned emulator: create, boot, configure, snapshot.

Pin: system-images;android-35;google_apis;x86_64, pixel_6 (1080x2400), density 420,
en-US, font scale 1.0, animations off, 3 GB RAM. Snapshot `aqb-clean` is taken
right after configuration; `aqb emulator start` boots from it (seconds, not minutes).
"""
from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path

SDK = Path(os.environ.get("ANDROID_HOME") or Path.home() / "Android" / "Sdk")
JDK = Path(os.environ.get("AQB_JDKS", Path.home() / ".local" / "jdks")) / "jdk17"
IMAGE = "system-images;android-35;google_apis;x86_64"
AVD = os.environ.get("AQB_AVD", "aqb-api35")
SNAPSHOT = "aqb-clean"
ROOT = Path(__file__).resolve().parents[1]

SETTINGS = [
    "settings put global window_animation_scale 0",
    "settings put global transition_animation_scale 0",
    "settings put global animator_duration_scale 0",
    "settings put system font_scale 1.0",
    "settings put system accelerometer_rotation 0",
    "settings put system user_rotation 0",
    "settings put secure show_ime_with_hard_keyboard 0",
    "settings put global stay_on_while_plugged_in 7",
    "settings put system screen_off_timeout 2147483647",
    "wm density 420",
    "setprop persist.sys.locale en-US",
    "cmd locale set-app-locales android --locales en-US 2>/dev/null; true",
]


def adb(serial: str, *args: str, check: bool = True) -> str:
    p = subprocess.run(["adb", "-s", serial, *args], capture_output=True, text=True, timeout=300)
    if check and p.returncode != 0:
        raise RuntimeError(p.stderr.strip())
    return p.stdout


def create(force: bool = False) -> None:
    avd_dir = Path.home() / ".android" / "avd" / f"{AVD}.avd"
    if avd_dir.exists() and not force:
        return
    env = dict(os.environ, JAVA_HOME=str(JDK), ANDROID_HOME=str(SDK))
    subprocess.run([str(SDK / "cmdline-tools/latest/bin/sdkmanager"), IMAGE, "platform-tools", "emulator"],
                   env=env, input="y\n" * 20, text=True, check=True)
    subprocess.run([str(SDK / "cmdline-tools/latest/bin/avdmanager"), "create", "avd", "-n", AVD, "-k", IMAGE,
                    "-d", "pixel_6", "--force"], env=env, input="no\n", text=True, check=True)
    cfg = avd_dir / "config.ini"
    lines = [l for l in cfg.read_text().splitlines()
             if not l.startswith(("hw.ramSize=", "hw.lcd.density=", "hw.keyboard="))]
    lines += ["hw.ramSize=3072", "hw.lcd.density=420", "hw.keyboard=yes"]
    cfg.write_text("\n".join(lines) + "\n")


def wait_boot(serial: str, timeout: float = 300) -> None:
    t0 = time.time()
    while time.time() - t0 < timeout:
        if adb(serial, "shell", "getprop sys.boot_completed", check=False).strip() == "1":
            return
        time.sleep(2)
    raise TimeoutError(f"{serial} did not boot")


def start(port: int = 5560, headless: bool = True, from_snapshot: bool = True) -> str:
    serial = f"emulator-{port}"
    scope = (["systemd-run", "--user", "--scope", "--quiet", "-p", f"MemoryMax={os.environ.get('AQB_EMU_MEM', '7G')}",
              "-p", "MemorySwapMax=0"] if shutil.which("systemd-run") else [])
    # Small footprint: 2 GB guest RAM, 2 cores, rendering inside the guest (-gpu guest):
    # host-side swiftshader_indirect grew qemu by ~27 MB/s during checks. Loading a RAM snapshot made qemu's
    # resident memory grow past 7 GB for a 3 GB guest, so cold boot is the default
    # (settings persist on the AVD's userdata disk; boot takes ~30 s).
    cmd = scope + [str(SDK / "emulator" / "emulator"), "-avd", AVD, "-port", str(port), "-no-audio",
           "-no-boot-anim", "-gpu", os.environ.get("AQB_EMU_GPU", "guest"),
           "-memory", os.environ.get("AQB_EMU_RAM_MB", "2048"), "-cores", os.environ.get("AQB_EMU_CORES", "2")]
    if headless:
        cmd.append("-no-window")
    cmd += ["-snapshot", SNAPSHOT, "-no-snapshot-save"] if from_snapshot else ["-no-snapshot-load"]
    log = (ROOT / "work" / "logs" / f"emulator-{port}.log")
    log.parent.mkdir(parents=True, exist_ok=True)
    subprocess.Popen(cmd, stdout=log.open("w"), stderr=subprocess.STDOUT, start_new_session=True)
    subprocess.run(["adb", "-s", serial, "wait-for-device"], timeout=300)
    wait_boot(serial)
    return serial


def configure(serial: str) -> None:
    adb(serial, "root", check=False)
    time.sleep(2)
    adb(serial, "wait-for-device")
    for c in SETTINGS:
        adb(serial, "shell", c, check=False)


def save_snapshot(serial: str) -> None:
    adb(serial, "emu", "avd", "snapshot", "save", SNAPSHOT)


def load_snapshot(serial: str) -> None:
    adb(serial, "emu", "avd", "snapshot", "load", SNAPSHOT)
    wait_boot(serial)
    adb(serial, "root", check=False)
    adb(serial, "wait-for-device")


def stop(serial: str) -> None:
    adb(serial, "emu", "kill", check=False)


def has_snapshot() -> bool:
    return (Path.home() / ".android" / "avd" / f"{AVD}.avd" / "snapshots" / SNAPSHOT).exists()
