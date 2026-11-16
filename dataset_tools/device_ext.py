"""Optional Device extensions for seeding file-based apps.

Appendix A (`Device`) has no write-file method. The sandbox should implement
the methods below on its Device subclass so `seed.py` can place fixture files.
Checks and repro scripts still prefer Appendix A (`sql`, `read_file`, `ui`,
`tap`, `launch`, `force_stop`, `rotate`, `back`, `wait_idle`).

This module is interface-only. It must not call adb itself.
"""
from __future__ import annotations

from dataset_tools.device_api import Device, Selector


class ExtendedDevice(Device):
    """Sandbox extensions. Not required for SQL-only apps."""

    def write_file(self, app_relative_path: str, data: bytes) -> None:
        """Write a file in the app data directory (debug / run-as)."""
        raise NotImplementedError

    def write_external(self, relative_path: str, data: bytes) -> None:
        """Write a file under the device's shared storage (Documents, Pictures)."""
        raise NotImplementedError

    def delete_external(self, relative_path: str) -> None:
        raise NotImplementedError

    def list_external(self, relative_path: str) -> list[str]:
        raise NotImplementedError

    def read_external(self, relative_path: str) -> bytes:
        raise NotImplementedError

    def media_scan(self, relative_path: str) -> None:
        """Ask MediaStore to index a file just written to shared storage."""
        raise NotImplementedError

    def long_press(self, selector: Selector) -> None:
        """Long-press the first node matching selector (adb: input swipe x y x y 800)."""
        raise NotImplementedError

    def tap_xy(self, x: int, y: int) -> None:
        """Tap a screen point, e.g. the centre of a node's bounds from ui() when several
        nodes share one label (per-row overflow buttons). adb: input tap x y."""
        raise NotImplementedError

    def key(self, name: str) -> None:
        """Press a hardware/IME key by Android name without the KEYCODE_ prefix
        (ENTER, SEARCH, TAB, DEL, ESCAPE). adb: input keyevent KEYCODE_<name>."""
        raise NotImplementedError

    def swipe(self, selector: Selector, direction: str = "left") -> None:
        """Swipe on the first node matching selector (adb: input swipe from its centre).
        direction is one of left, right, up, down."""
        raise NotImplementedError

    def ui_texts(self) -> list[str]:
        """Convenience: visible text and content-descriptions from dev.ui()."""
        out = []
        for n in self.ui():
            if not n.get("visible", True):
                continue
            for k in ("text", "desc"):
                v = n.get(k)
                if v:
                    out.append(str(v))
        return out

    def find(self, selector: Selector) -> dict | None:
        nodes = self.ui()
        for n in nodes:
            if "id" in selector and n.get("id") == selector["id"]:
                return n
            if "text" in selector and (n.get("text") or "") == selector["text"]:
                return n
            if "desc" in selector and (n.get("desc") or "") == selector["desc"]:
                return n
        return None
