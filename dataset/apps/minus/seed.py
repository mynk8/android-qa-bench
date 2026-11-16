"""Apply seeded starting data for minus. Device API + device_ext optional file writes."""
from __future__ import annotations
from pathlib import Path
PACKAGE = 'com.serranoie.app.minus'
HERE = Path(__file__).resolve().parent


def _call(dev, name, *a):
    fn = getattr(dev, name, None)
    if fn is not None:
        fn(*a)


_FLAGS = ["onboarding_completed", "tutorial_box_completed", "analytics_tutorial_completed",
          "analytics_spends_tutorial_completed", "history_tutorial_completed", "receipt_scan_hint_shown"]


def _varint(n: int) -> bytes:
    out = b""
    while True:
        b = n & 0x7F
        n >>= 7
        out += bytes([b | (0x80 if n else 0)])
        if not n:
            return out


def _prefs_pb(keys) -> bytes:
    """Preferences DataStore proto: repeated entry{key=1, Value{bool=1 | long=4}}."""
    out = b""
    items = [(k, b"\x08\x01") for k in keys]
    items.append(("changelog_last_seen_version_code", b"\x20" + _varint(2000000000)))  # no changelog sheet
    for k, val in items:
        kb = k.encode()
        entry = b"\x0a" + bytes([len(kb)]) + kb + b"\x12" + bytes([len(val)]) + val
        out += b"\x0a" + bytes([len(entry)]) + entry
    return out


def apply(dev, seed: dict) -> None:
    dev.launch(PACKAGE)          # first launch creates the app's database/schema
    dev.wait_idle()
    dev.force_stop(PACKAGE)
    for rel in seed.get("delete_external") or []:
        _call(dev, "delete_external", rel)
    for item in seed.get("files") or []:
        _call(dev, "write_external", item["path"], item["text"].encode("utf-8"))
        _call(dev, "media_scan", item["path"])
    for item in seed.get("fixtures") or []:
        _call(dev, "write_external", item["path"], (HERE / "seed" / item["fixture"]).read_bytes())
        _call(dev, "media_scan", item["path"])
    if seed.get("db_name") and seed.get("sql"):
        dev.write_seed_sql(seed["db_name"], seed["sql"])
    dev.write_file("files/datastore/settings.preferences_pb", _prefs_pb(_FLAGS))
    dev.launch(PACKAGE)
    dev.wait_idle()
