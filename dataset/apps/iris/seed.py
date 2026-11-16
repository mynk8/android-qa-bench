"""Apply seeded starting data for iris. Device API + device_ext optional file writes."""
from __future__ import annotations
from pathlib import Path
PACKAGE = 'com.iris.gallery'
HERE = Path(__file__).resolve().parent


def _call(dev, name, *a):
    fn = getattr(dev, name, None)
    if fn is not None:
        fn(*a)


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
    dev.launch(PACKAGE)
    dev.wait_idle()
    # Iris queries MediaStore once at launch; if that ran before the index settled it shows
    # "No photos found" although the seed photos are indexed. Relaunch until they show (max 3).
    if seed.get("fixtures") or seed.get("files"):
        for _ in range(3):
            texts = [n.get("text") or "" for n in (dev.ui() or [])]
            if "No photos found" not in texts:
                break
            dev.force_stop(PACKAGE)
            dev.launch(PACKAGE)
            dev.wait_idle()
