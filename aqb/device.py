"""AdbDevice: the reference Device implementation (dataset_tools/device_api.py + device_ext.py).

Talks to one emulator over adb. Needs a userdebug/google_apis image (adb root) so
checks can read app databases. Every method is synchronous and deterministic
from the caller's view; waiting happens here, never in checks.

Use from the harness:  --device aqb.device:AdbDevice   (serial from $AQB_SERIAL)
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import subprocess
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from dataset_tools.device_ext import ExtendedDevice

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "dataset"
EXT = "/sdcard"
_BOUNDS = re.compile(r"\[(-?\d+),(-?\d+)\]\[(-?\d+),(-?\d+)\]")



def input_text_pieces(text: str) -> list[str]:
    """Encode text for `adb shell input text`, one string per call.

    `input text` turns "%s" into a space and passes every other character, "%" included,
    unchanged (verified on Android 15). So spaces become "%s", "%" is NOT doubled, and a
    literal "%s" in the text is sent as two calls ("...%", "s...") so it is not read as a space.
    """
    import re as _re
    return [p.replace(" ", "%s") for p in _re.split(r"(?<=%)(?=s)", str(text or "")) if p]

class AdbError(RuntimeError):
    pass


def _sql_literal(v: Any) -> str:
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, (int, float)):
        return repr(v)
    return "'" + str(v).replace("'", "''") + "'"


def bind(query: str, params: tuple) -> str:
    """Inline positional ? parameters as SQL literals (sqlite3 CLI has no binding)."""
    out, i, quote = [], 0, None
    for ch in query:
        if quote:
            out.append(ch)
            if ch == quote:
                quote = None
        elif ch in ("'", '"'):
            quote = ch
            out.append(ch)
        elif ch == "?":
            if i >= len(params):
                raise ValueError("too few SQL parameters")
            out.append(_sql_literal(params[i]))
            i += 1
        else:
            out.append(ch)
    if i != len(params):
        raise ValueError("too many SQL parameters")
    return "".join(out)


def parse_ui(xml_text: str) -> list[dict]:
    nodes = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return nodes
    for n in root.iter("node"):
        m = _BOUNDS.match(n.get("bounds", ""))
        x1, y1, x2, y2 = (int(g) for g in m.groups()) if m else (0, 0, 0, 0)
        rid = n.get("resource-id") or ""
        nodes.append({
            "id": rid,
            "text": n.get("text") or "",
            "desc": n.get("content-desc") or "",
            "class": n.get("class") or "",
            "package": n.get("package") or "",
            "bounds": [x1, y1, x2, y2],
            "clickable": n.get("clickable") == "true",
            "checked": n.get("checked") == "true",
            "enabled": n.get("enabled") == "true",
            "focused": n.get("focused") == "true",
            "selected": n.get("selected") == "true",
            "visible": x2 > x1 and y2 > y1,
        })
    return nodes


def node_matches(node: dict, sel: dict) -> bool:
    if "id" in sel:
        v = node.get("id") or ""
        return v == sel["id"] or v.endswith("/" + sel["id"])
    for k in ("text", "desc"):
        if k in sel:
            return (node.get(k) or "") == sel[k]
    return False


def is_virtual(serial: str) -> bool:
    """True when the device says it is an emulator or a cloud virtual device
    (local AVD, Limrun, Cuttlefish), as opposed to someone's phone."""
    def prop(name):
        return subprocess.run(["adb", "-s", serial, "shell", "getprop", name],
                              capture_output=True, text=True).stdout.strip()
    if prop("ro.kernel.qemu") == "1" or prop("ro.boot.qemu") == "1":
        return True
    return prop("ro.hardware") in ("ranchu", "goldfish", "cutf_cvm", "vsoc_x86_64", "vsoc_x86", "redroid")


def resolve_serial(serial: str | None) -> str:
    """Pick the target device. Only emulators, never a physical phone, unless
    AQB_ALLOW_PHYSICAL=1: the harness clears app data and installs builds."""
    out = subprocess.run(["adb", "devices"], capture_output=True, text=True).stdout.splitlines()[1:]
    online = [l.split()[0] for l in out if l.strip().endswith("device")]
    emus = [d for d in online if d.startswith("emulator-")]
    if serial:
        if serial not in online:
            raise AdbError(f"device {serial} is not online (adb devices: {online})")
        if not serial.startswith("emulator-") and not is_virtual(serial) \
                and os.environ.get("AQB_ALLOW_PHYSICAL") != "1":
            raise AdbError(f"{serial} is a physical device; refusing (set AQB_ALLOW_PHYSICAL=1 to override)")
        return serial
    if len(emus) != 1:
        raise AdbError(f"need exactly one emulator or --serial / AQB_SERIAL; emulators online: {emus}")
    return emus[0]


class AdbDevice(ExtendedDevice):
    def __init__(self, serial: str | None = None, dataset: Path = DATASET, apk_dir: Path | None = None):
        self.serial = resolve_serial(serial or os.environ.get("AQB_SERIAL"))
        self.dataset = Path(dataset)
        self.apk_dir = apk_dir
        self.package: str | None = None
        self._ui_cache: list[dict] | None = None
        self._db_paths: dict[tuple[str, str], str] = {}
        self.log: list[tuple] = []
        out = self._adb("root", check=False).decode(errors="replace")
        self._adb("wait-for-device")
        # production builds (Limrun, phones): no root; app data goes through the aqb probe
        self.rooted = self.sh("id -u", check=False).strip() == "0"
        # on a physical device, remember the user's settings that checks may change
        self.physical = not self.serial.startswith("emulator-")
        self._saved_settings = {}
        if self.physical:
            for k in ("accelerometer_rotation", "user_rotation"):
                self._saved_settings[("system", k)] = self.sh(f"settings get system {k}", check=False).strip()

    def restore_settings(self) -> None:
        """Put back the user's settings recorded at connect time (physical devices)."""
        for (ns, k), v in self._saved_settings.items():
            if v and v != "null":
                self.sh(f"settings put {ns} {k} {shlex.quote(v)}", check=False)

    # ------------------------------------------------------------- plumbing
    def _adb(self, *args: str, check: bool = True, input_bytes: bytes | None = None, timeout: float = 120) -> bytes:
        cmd = ["adb"] + (["-s", self.serial] if self.serial else []) + list(args)
        p = subprocess.run(cmd, input=input_bytes, capture_output=True, timeout=timeout)
        if check and p.returncode != 0:
            raise AdbError(f"{' '.join(cmd[:6])}: {p.stderr.decode(errors='replace').strip()}")
        return p.stdout

    def sh(self, cmd: str, check: bool = True, input_bytes: bytes | None = None, timeout: float = 120) -> str:
        return self._adb("shell", cmd, check=check, input_bytes=input_bytes, timeout=timeout).decode("utf-8", "replace")

    def _dirty(self) -> None:
        self._ui_cache = None

    def _pkg_for_build(self, build_id: str) -> tuple[str, str]:
        app_id = build_id.split("-")[0]
        app = json.loads((self.dataset / "apps" / app_id / "app.json").read_text())
        return app_id, app["package"]

    # ------------------------------------------------------------- lifecycle
    def install(self, build_id: str) -> None:
        app_id, pkg = self._pkg_for_build(build_id)
        apk = (self.apk_dir or (self.dataset / "apps" / app_id / "builds")) / f"{build_id}.apk"
        if not apk.is_file():
            raise FileNotFoundError(apk)
        self._adb("uninstall", pkg, check=False)
        remote = self._staged_apk(apk)
        out = self.sh(f"pm install -g -t {shlex.quote(remote)}", check=False, timeout=300)
        if "Success" not in out:
            raise AdbError(f"install {build_id}: {out.strip()[-300:]}")
        self.package = pkg
        self._db_paths.clear()
        self._grant(pkg)
        self.log.append(("install", build_id))
        self._dirty()

    def _staged_apk(self, apk: Path) -> str:
        """Upload each distinct APK to the device once (keyed by content hash) and install
        from device storage afterwards. Every bug's clean build is the same APK, so over a
        cloud tunnel this saves one large upload per bug."""
        h = hashlib.sha256(apk.read_bytes()).hexdigest()[:16]
        remote = f"/data/local/tmp/aqb-{h}.apk"
        staged = self.__dict__.setdefault("_staged", set())
        if h not in staged and self.sh(f"test -f {remote} && echo y", check=False).strip() != "y":
            # one upload at a time across all local runs: parallel uploads share the
            # uplink and each then hits its timeout; serialized, each gets full bandwidth
            import fcntl
            lock = ROOT / "work" / ".upload.lock"
            lock.parent.mkdir(parents=True, exist_ok=True)
            with lock.open("a") as fh:
                fcntl.flock(fh, fcntl.LOCK_EX)
                try:
                    self._adb("push", str(apk), remote, timeout=1800)
                finally:
                    fcntl.flock(fh, fcntl.LOCK_UN)
        staged.add(h)
        return remote

    def _grant(self, pkg: str) -> None:
        for op in ("MANAGE_EXTERNAL_STORAGE", "READ_MEDIA_IMAGES", "WRITE_SETTINGS"):
            self.sh(f"appops set {pkg} {op} allow", check=False)
        dump = self.sh(f"dumpsys package {pkg}", check=False)
        perms = set(re.findall(r"(android\.permission\.[A-Z_]+)", dump))
        for perm in sorted(perms):
            self.sh(f"pm grant {pkg} {perm}", check=False)

    def reset_device_state(self) -> None:
        """Phone-wide state an earlier run may have left behind (app data is reset per app):
        portrait orientation, no open notification shade or dialog, home screen."""
        self.sh("settings put system accelerometer_rotation 0", check=False)
        self.sh("settings put system user_rotation 0", check=False)
        self.sh("cmd statusbar collapse", check=False)
        self.sh("input keyevent KEYCODE_HOME", check=False)
        self._dirty()

    def reset_app(self, package: str) -> None:
        """Clear app data and shared-storage app dir; re-grant permissions."""
        self.sh(f"am force-stop {package}", check=False)
        self.sh(f"pm clear {package}", check=False)
        self._grant(package)
        self._db_paths.clear()
        self.package = package
        self._dirty()

    def launcher_component(self, package: str) -> str | None:
        """The app's own MAIN/LAUNCHER activity, found without the system chooser.

        resolve-activity can answer with android/...ResolverActivity on some builds
        (Limrun/redroid), e.g. when the launcher filter lacks CATEGORY_DEFAULT, so
        list the matching activities and keep the first one inside the package."""
        cache = self.__dict__.setdefault("_launcher_cache", {})
        if package in cache:
            return cache[package]
        pat = re.compile(re.escape(package) + r"/[\w.$]+")
        comp = None
        for cmd in (f"cmd package query-activities --brief -a android.intent.action.MAIN "
                    f"-c android.intent.category.LAUNCHER {package}",
                    f"cmd package resolve-activity --brief -a android.intent.action.MAIN "
                    f"-c android.intent.category.LAUNCHER {package}",
                    f"dumpsys package {package}"):
            m = pat.search(self.sh(cmd, check=False))
            if m:
                comp = m.group(0)
                break
        cache[package] = comp
        return comp

    def launch(self, package: str) -> None:
        self.package = package
        comp = self.launcher_component(package)
        if not comp:
            raise AdbError(f"no launcher activity found for {package}")
        self.sh(f"am start -W -a android.intent.action.MAIN -c android.intent.category.LAUNCHER -n {comp}", check=False)
        self.log.append(("launch", package))
        self._dirty()
        self.wait_idle()

    def force_stop(self, package: str) -> None:
        self.sh(f"am force-stop {package}", check=False)
        self.log.append(("force_stop", package))
        self._dirty()

    def rotate(self, landscape: bool) -> None:
        self.sh("settings put system accelerometer_rotation 0")
        self.sh(f"settings put system user_rotation {1 if landscape else 0}")
        self._dirty()
        self.wait_idle()

    # ------------------------------------------------------------- input
    def _find_node(self, sel: dict) -> dict | None:
        for n in self.ui():
            if n["visible"] and node_matches(n, sel):
                return n
        return None

    def _centre(self, sel: dict) -> tuple[int, int]:
        n = self._find_node(sel)
        if n is None:
            raise LookupError(f"no node for {sel}")
        x1, y1, x2, y2 = n["bounds"]
        return (x1 + x2) // 2, (y1 + y2) // 2

    def tap(self, selector: dict) -> None:
        x, y = self._centre(selector)
        self.sh(f"input tap {x} {y}")
        self.log.append(("tap", selector))
        self._dirty()

    def input_text(self, selector: dict, text: str) -> None:
        self.tap(selector)
        self.wait_idle()
        self.sh("input keycombination KEYCODE_CTRL_LEFT KEYCODE_A", check=False)
        self.sh("input keyevent KEYCODE_DEL", check=False)
        for piece in input_text_pieces(text):
            self.sh("input text " + shlex.quote(piece))
        self.log.append(("input_text", selector, text))
        self._dirty()

    def tap_xy(self, x: int, y: int) -> None:
        self.sh(f"input tap {int(x)} {int(y)}")
        self._dirty()

    def key(self, name: str) -> None:
        name = name.upper().removeprefix("KEYCODE_")
        if not name.replace("_", "").isalnum():
            raise ValueError(f"bad key name {name!r}")
        self.sh(f"input keyevent KEYCODE_{name}")
        self._dirty()

    def back(self) -> None:
        self.sh("input keyevent KEYCODE_BACK")
        self._dirty()

    def home(self) -> None:
        self.sh("input keyevent KEYCODE_HOME")
        self._dirty()

    def _screen_size(self) -> tuple[int, int]:
        m = re.search(r"(\d+)x(\d+)", self.sh("wm size"))
        return (int(m.group(1)), int(m.group(2))) if m else (1080, 2400)

    def scroll_to(self, selector: dict) -> bool:
        w, h = self._screen_size()
        for _ in range(10):
            if self._find_node(selector) is not None:
                return True
            self.sh(f"input swipe {w // 2} {int(h * 0.75)} {w // 2} {int(h * 0.3)} 300")
            self._dirty()
            self.wait_idle()
        return self._find_node(selector) is not None

    def long_press(self, selector: dict) -> None:
        x, y = self._centre(selector)
        self.sh(f"input swipe {x} {y} {x} {y} 900")
        self._dirty()

    def swipe(self, selector: dict, direction: str = "left") -> None:
        n = self._find_node(selector)
        if n is None:
            raise LookupError(f"no node for {selector}")
        x1, y1, x2, y2 = n["bounds"]
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
        dx = {"left": -1, "right": 1}.get(direction, 0) * max(200, (x2 - x1) // 2)
        dy = {"up": -1, "down": 1}.get(direction, 0) * max(200, (y2 - y1) // 2)
        self.sh(f"input swipe {cx} {cy} {cx + dx} {cy + dy} 250")
        self._dirty()

    def wait_idle(self, timeout_s: float = 5) -> None:
        """Wait until two consecutive UI dumps are identical (or timeout)."""
        deadline = time.monotonic() + timeout_s
        prev = None
        time.sleep(0.15)
        while True:
            xml = self._dump()
            h = hashlib.sha1(xml.encode()).hexdigest()
            if h == prev or time.monotonic() > deadline:
                self._ui_cache = parse_ui(xml)
                return
            prev = h
            time.sleep(0.15)

    # ------------------------------------------------------------- observation
    def _u2(self):
        """Persistent on-device UI server (uiautomator2): ~80 ms per dump vs ~2 s."""
        if getattr(self, "_u2dev", None) is None and not getattr(self, "_u2_failed", False):
            try:
                import uiautomator2
                self._u2dev = uiautomator2.connect(self.serial)
            except Exception:
                self._u2_failed = True
                self._u2dev = None
        return getattr(self, "_u2dev", None)

    def _dump(self) -> str:
        u = self._u2()
        if u is not None:
            try:
                return u.dump_hierarchy(compressed=False)
            except Exception:
                pass
        for _ in range(3):
            out = self.sh("uiautomator dump /sdcard/.aqb_ui.xml >/dev/null 2>&1; cat /sdcard/.aqb_ui.xml", check=False)
            if "<hierarchy" in out:
                return out[out.index("<"):]
            time.sleep(0.5)
        return "<hierarchy/>"

    def ui(self) -> list[dict]:
        if self._ui_cache is None:
            self._ui_cache = parse_ui(self._dump())
        return self._ui_cache

    def screenshot(self) -> bytes:
        return self._adb("exec-out", "screencap", "-p")

    # ------------------------------------------------------------- app data
    # Rooted emulators: sqlite3/cat as root. Production builds (Limrun, phones): the
    # aqb probe instrumentation runs inside the target app's process and does the work
    # (aqb/probe; built by aqb/probe/build.sh, signed with the apps' debug key).
    PROBE_DIR = ROOT / "aqb" / "probe" / "out"

    def _private(self, path: str) -> bool:
        return path.startswith("/data/")

    def _ensure_probe(self) -> None:
        pkg = self.package or ""
        if pkg in getattr(self, "_probed", set()):
            return
        apk = self.PROBE_DIR / f"probe-{pkg}.apk"
        if not apk.exists():
            raise FileNotFoundError(f"{apk} missing: run aqb/probe/build.sh")
        out = self._adb("install", "-r", "-t", str(apk), check=False, timeout=180).decode(errors="replace")
        if "Success" not in out:
            raise AdbError(f"probe install for {pkg}: {out.strip()[-200:]}")
        self._probed = getattr(self, "_probed", set()) | {pkg}

    def probe(self, op: str, **arg) -> dict:
        """Run one probe operation inside the current app's process."""
        import base64
        self._ensure_probe()
        a = base64.b64encode(json.dumps(arg).encode("utf-8")).decode("ascii")
        out = self.sh(f"am instrument -w -r -e op {op} -e arg {a} aqb.probe.{self.package}/aqb.probe.Probe",
                      check=False, timeout=180)
        m = re.search(r"INSTRUMENTATION_RESULT: out=(\S+)", out)
        if not m:
            raise AdbError(f"probe {op} gave no result: {out.strip()[-300:]}")
        res = json.loads(base64.b64decode(m.group(1)).decode("utf-8"))
        if res.get("error"):
            raise AdbError(f"probe {op}: {res['error']}")
        return res

    def _pull_ext(self, path: str) -> bytes | None:
        if self.sh(f"test -f {shlex.quote(path)} && echo y", check=False).strip() != "y":
            return None
        return self._adb("exec-out", f"cat {shlex.quote(path)}")

    def _ext_db_local(self, path: str) -> Path:
        """Copy a shared-storage SQLite database (with -wal/-shm) to a temp dir."""
        import tempfile
        d = Path(tempfile.mkdtemp(prefix="aqb-db-"))
        name = path.rsplit("/", 1)[-1]
        for suffix in ("", "-wal", "-shm"):
            data = self._pull_ext(path + suffix)
            if data is not None:
                (d / (name + suffix)).write_bytes(data)
        if not (d / name).exists():
            raise FileNotFoundError(path)
        return d / name

    def _db_path(self, db_name: str) -> str:
        pkg = self.package or ""
        key = (pkg, db_name)
        if key in self._db_paths:
            return self._db_paths[key]
        # shared storage first (AnkiDroid keeps its collection there)
        for c in (f"{EXT}/Android/data/{pkg}/files/AnkiDroid/{db_name}", f"{EXT}/AnkiDroid/{db_name}"):
            if self.sh(f"test -f {shlex.quote(c)} && echo y", check=False).strip() == "y":
                self._db_paths[key] = c
                return c
        if self.rooted:
            for c in (f"/data/data/{pkg}/databases/{db_name}", f"/data/data/{pkg}/files/{db_name}"):
                if self.sh(f"test -f {shlex.quote(c)} && echo y", check=False).strip() == "y":
                    self._db_paths[key] = c
                    return c
            found = self.sh(f"find /data/data/{pkg} -name {shlex.quote(db_name)} -type f 2>/dev/null", check=False).split()
            if found:
                self._db_paths[key] = found[0]
                return found[0]
        else:
            r = self.probe("find", name=db_name)
            if r.get("ok"):
                self._db_paths[key] = r["path"]
                return r["path"]
        raise FileNotFoundError(f"database {db_name} for {pkg}")

    def sql(self, db_name: str, query: str, params: tuple = ()) -> list[dict[str, Any]]:
        path = self._db_path(db_name)
        q = bind(query, tuple(params))
        if self.rooted:
            out = self.sh(f"sqlite3 -json {shlex.quote(path)}", input_bytes=q.encode("utf-8"), check=False).strip()
            return json.loads(out) if out.startswith("[") else []
        if self._private(path):
            return self.probe("sql", db=path, query=q)["rows"]
        import shutil as _sh
        import sqlite3
        local = self._ext_db_local(path)
        try:
            con = sqlite3.connect(str(local))
            con.row_factory = sqlite3.Row
            rows = [dict(r) for r in con.execute(q).fetchall()]
            con.close()
            return rows
        finally:
            _sh.rmtree(local.parent, ignore_errors=True)

    def write_seed_sql(self, db_name: str, statements: list[str]) -> None:
        pkg = self.package or ""
        self.force_stop(pkg)
        path = self._db_path(db_name)
        stmts = [s.rstrip().rstrip(";") for s in statements if s.strip()]
        if not self.rooted and self._private(path):
            self.probe("exec", db=path, statements=stmts)
            self.force_stop(pkg)
            return
        script = "PRAGMA foreign_keys=OFF;\nBEGIN;\n" + "\n".join(s + ";" for s in stmts) + "\nCOMMIT;\n"
        if not self.rooted:  # shared-storage database without root: edit a copy and push it back
            import shutil as _sh
            import sqlite3
            local = self._ext_db_local(path)
            try:
                con = sqlite3.connect(str(local))
                con.executescript(script)
                con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                con.close()
                data = local.read_bytes()
            finally:
                _sh.rmtree(local.parent, ignore_errors=True)
            qp = shlex.quote(path)
            self.sh(f"cat > {qp} && rm -f {qp}-wal {qp}-shm", input_bytes=data)
            return
        self.sh(f"sqlite3 {shlex.quote(path)}", input_bytes=script.encode("utf-8"))
        d = path.rsplit("/", 1)[0]  # files touched by root must stay readable by the app
        self.sh(f"own=$(stat -c %u:%g {shlex.quote(d)}); chown $own {shlex.quote(path)}* ; restorecon {shlex.quote(path)}* 2>/dev/null",
                check=False)

    def read_file(self, app_relative_path: str) -> bytes:
        if self.rooted:
            p = f"/data/data/{self.package}/{app_relative_path}"
            if self.sh(f"test -f {shlex.quote(p)} && echo y", check=False).strip() != "y":
                raise FileNotFoundError(app_relative_path)
            return self._adb("exec-out", f"cat {shlex.quote(p)}")
        import base64
        r = self.probe("cat", path=app_relative_path)
        if not r.get("ok"):
            raise FileNotFoundError(app_relative_path)
        return base64.b64decode(r["b64"])

    def write_file(self, app_relative_path: str, data: bytes) -> None:
        if not self.rooted:
            import base64
            self.probe("write", path=app_relative_path, b64=base64.b64encode(data).decode("ascii"))
            return
        p = f"/data/data/{self.package}/{app_relative_path}"
        d = p.rsplit("/", 1)[0]
        self.sh(f"mkdir -p {shlex.quote(d)} && cat > {shlex.quote(p)}", input_bytes=data)
        self.sh(f"own=$(stat -c %u:%g /data/data/{self.package}); chown -R $own {shlex.quote(d)}; restorecon -R {shlex.quote(d)}",
                check=False)

    def settings(self, namespace: str, key: str) -> str:
        if namespace in ("global", "system", "secure"):
            return self.sh(f"settings get {namespace} {shlex.quote(key)}").strip()
        try:
            xml = self.read_file(f"shared_prefs/{namespace}.xml").decode("utf-8", "replace")
        except FileNotFoundError:
            return ""
        m = re.search(r'name="%s"(?: value="([^"]*)")?>?([^<]*)' % re.escape(key), xml)
        return (m.group(1) if m and m.group(1) is not None else (m.group(2) if m else "")) or ""

    # ------------------------------------------------------------- shared storage
    def _ext(self, rel: str) -> str:
        return f"{EXT}/{rel.lstrip('/')}"

    def write_external(self, relative_path: str, data: bytes) -> None:
        p = self._ext(relative_path)
        self.sh(f"mkdir -p {shlex.quote(p.rsplit('/', 1)[0])} && cat > {shlex.quote(p)}", input_bytes=data)

    def delete_external(self, relative_path: str) -> None:
        """Delete files under shared storage AND their MediaStore rows. Recreating a file at the
        same path otherwise reuses the stale row (same _id), which gallery apps such as Iris do
        not show: the second seed on one device gave an empty gallery."""
        real = "/storage/emulated/0/" + relative_path.strip("/")
        like = real.replace("'", "''")
        where = f"_data='{like}' OR _data LIKE '{like}/%'"
        self.sh(f"content delete --uri content://media/external/file --where {shlex.quote(where)}", check=False)
        self.sh(f"rm -rf {shlex.quote(self._ext(relative_path))}", check=False)

    def list_external(self, relative_path: str) -> list[str]:
        p = self._ext(relative_path)
        if self.sh(f"test -d {shlex.quote(p)} && echo y", check=False).strip() != "y":
            raise FileNotFoundError(relative_path)
        return [x for x in self.sh(f"ls -1A {shlex.quote(p)}").splitlines() if x]

    def read_external(self, relative_path: str) -> bytes:
        p = self._ext(relative_path)
        if self.sh(f"test -f {shlex.quote(p)} && echo y", check=False).strip() != "y":
            raise FileNotFoundError(relative_path)
        return self._adb("exec-out", f"cat {shlex.quote(p)}")

    MEDIA_EXT = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".heic", ".mp4", ".mkv", ".webm", ".mp3", ".m4a", ".ogg")

    def media_scan(self, relative_path: str, timeout_s: float = 15) -> None:
        """Ask MediaStore to index a file and, for media files, wait until it is listed.
        The scan broadcast is asynchronous on API 30+; without the wait an app launched
        right after seeding can see an empty gallery."""
        p = self._ext(relative_path)
        self.sh(f"am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d {shlex.quote('file://' + p)}", check=False)
        if not p.lower().endswith(self.MEDIA_EXT):
            return
        real = "/storage/emulated/0/" + relative_path.lstrip("/")
        uri = "content://media/external/" + ("video" if p.lower().endswith((".mp4", ".mkv", ".webm")) else
                                            "audio" if p.lower().endswith((".mp3", ".m4a", ".ogg")) else "images") + "/media"
        where = "_data='" + real.replace("'", "''") + "'"
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            out = self.sh(f"content query --uri {uri} --projection _id --where {shlex.quote(where)}", check=False)
            if "Row:" in out:
                return
            time.sleep(0.3)
        raise TimeoutError(f"MediaStore did not index {relative_path} within {timeout_s}s")
