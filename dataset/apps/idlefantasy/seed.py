"""Apply seeded starting data for idlefantasy. Device API + device_ext optional file writes."""
from __future__ import annotations
PACKAGE = 'com.tristinbaker.idlefantasy'


def apply(dev, seed: dict) -> None:
    dev.launch(PACKAGE)          # first launch creates the app's database/schema
    dev.wait_idle()
    dev.force_stop(PACKAGE)
    if seed.get("db_name") and seed.get("sql"):
        dev.write_seed_sql(seed["db_name"], seed["sql"])
    dev.launch(PACKAGE)
    dev.wait_idle()
