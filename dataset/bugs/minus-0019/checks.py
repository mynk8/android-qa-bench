"""Deterministic checks for minus-0019. passed=True means intended behaviour (bug absent).
Each check re-seeds, drives the trigger through the Device API, then observes.
No wall-clock reads or sleeps; labels live in params["nav"] (bug.json)."""
from __future__ import annotations
import re
from dataset_tools import check_helpers as h

APP = 'minus'
PACKAGE = 'com.serranoie.app.minus'
SEED = 'budget_basic'
DB = 'minus_budget.db'
TIER = 'B'
PARAMS_DEFAULT = {'nav': {'dismiss_tutorial': [{'text': 'Skip'}, {'text': 'Got it'}, {'text': 'OK'}], 'budget_pill': [{'text': 'Today'}, {'text': 'This week'}, {'text': 'This biweekly'}, {'text': 'This month'}, {'text': 'Daily Amount exceeded'}], 'chip_weekly': [{'text': 'Weekly'}]}}


def _p(params):
    p = dict(PARAMS_DEFAULT)
    p.update(params or {})
    return p

def _clear_shade(dev):
    """The Android 'Certificate authority installed' notice can pull the shade down: close it."""
    for _ in range(2):
        if h.has(dev, "Certificate authority installed") or h.has(dev, "Clear all"):
            dev.back()
            dev.wait_idle()


def _start(dev, p):
    h.fresh(dev, APP, SEED)
    _clear_shade(dev)
    h.go_opt(dev, p, "dismiss_tutorial")


def _sql_relaunch(dev, p, stmts):
    """Edit the seeded data while the app is stopped, then start it again."""
    dev.force_stop(PACKAGE)
    dev.write_seed_sql(DB, stmts)
    dev.launch(PACKAGE)
    dev.wait_idle()
    _clear_shade(dev)
    h.go_opt(dev, p, "dismiss_tutorial")


MONEY = re.compile(r"\d[\d,]*(?:\.\d+)?")


def _money_after(dev, label, span=3):
    """First money token in the texts at/after the one containing `label` (case-insensitive)."""
    ts = h.texts(dev)
    key = label.casefold()
    for i, t in enumerate(ts):
        if key in t.casefold():
            blob = " ".join(ts[i:i + span]).replace(label, "")
            m = MONEY.search(blob)
            return (float(m.group(0).replace(",", "")) if m else None), ts[i:i + span]
    return None, ts[:20]


def _remaining_brief(dev):
    """The money token in the helper line '<amount> (remaining) / N day'."""
    ts = h.texts(dev)
    for t in ts:
        if "(remaining)" in t:
            m = MONEY.search(t)
            return (float(m.group(0).replace(",", "")) if m else None), t
    return None, ts[:20]


def _open_sheet(dev, p):
    h.go(dev, p, "budget_pill")
    if not h.has(dev, "Calculated amount"):
        raise h.StepMissing("budget_sheet")


def _target(dev, p):
    # 100.00 budget - (40.00 Groceries + 20.00 Rent charge) = 40.00 over 21 days = 1.90 a day
    _start(dev, p)
    _open_sheet(dev, p)
    daily, seen = _money_after(dev, "Calculated amount", 3)
    return daily is not None and abs(daily - 1.90) < 0.006, {"calculated_amount": daily, "seen": seen}


def _held(dev, p):
    # Rent of 30.00: 100.00 - 40.00 - 30.00 = 30.00 left, shown as "Available: 30%"
    _start(dev, p)
    _sql_relaunch(dev, p, ["UPDATE transactions SET amount='30.00' WHERE comment='Rent';"])
    _open_sheet(dev, p)
    ts = h.texts(dev)
    pct = None
    for t in ts:
        m = re.search(r"Available:\s*(\d+)%", t)
        if m:
            pct = int(m.group(1))
    return pct == 30, {"available_pct": pct, "seen": ts[:20]}


def _keep(dev, p):
    # the sheet itself still opens with its budget figures
    _start(dev, p)
    _open_sheet(dev, p)
    daily, seen = _money_after(dev, "Calculated amount", 3)
    return daily is not None and h.has(dev, "Total budget"), {"calculated_amount": daily, "seen": seen}


def target(dev, params):
    return h.run(_target, dev, _p(params), TIER)


def held_out(dev, params):
    return h.run(_held, dev, _p(params), TIER)


def preserve(dev, params):
    return h.run(_keep, dev, _p(params), "A" if DB else "B")


CHECKS = {"target": target, "held_out": [held_out], "preservation": [preserve]}
