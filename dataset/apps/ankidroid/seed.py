"""Apply seeded starting data for ankidroid. Device API + device_ext optional file writes."""
from __future__ import annotations
from pathlib import Path
PACKAGE = 'com.ichi2.anki'
HERE = Path(__file__).resolve().parent


def _call(dev, name, *a):
    fn = getattr(dev, name, None)
    if fn is not None:
        fn(*a)


def apply(dev, seed: dict) -> None:
    # Skip the intro slides. The harness grants all-files access (appops), so on first launch the app
    # picks the public AnkiDroid folder (/sdcard/AnkiDroid) itself and shows no permission screen.
    dev.write_file("shared_prefs/com.ichi2.anki_preferences.xml", (
        "<?xml version='1.0' encoding='utf-8' standalone='yes' ?>\n<map>\n"
        '    <boolean name="IntroductionSlidesShown" value="true" />\n'
        "</map>\n").encode("utf-8"))
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
    dev.launch(PACKAGE)
    dev.wait_idle()
