"""Deterministic checks for minus-0018. passed=True means intended behaviour (bug absent).
Each check re-seeds, drives the trigger through the Device API, then observes.
No wall-clock reads or sleeps; labels live in params["nav"] (bug.json)."""
from __future__ import annotations
from dataset_tools import check_helpers as h

APP = 'minus'
PACKAGE = 'com.serranoie.app.minus'
SEED = 'budget_basic'
DB = 'minus_budget.db'
TIER = 'B'
PARAMS_DEFAULT = {'nav': {'dismiss_tutorial': [{'text': 'Skip'}, {'text': 'Got it'}, {'text': 'OK'}], 'collapse': [{'desc': 'Collapse'}], 'expand': [{'desc': 'Expand'}]}}


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


PILL_LABELS = ["Today", "This week", "This biweekly", "This month"]


def _open_history(dev, p, marker="Groceries"):
    """The history is a top sheet: drag the main screen down (swipe down on the budget pill)."""
    for _ in range(3):
        _clear_shade(dev)
        if h.has(dev, marker):
            return
        for lab in PILL_LABELS:
            if h.find(dev, [{"text": lab}]) is not None:
                h.swipe(dev, lab, "down")
                break
        else:
            raise h.StepMissing("history_drag_anchor:" + "|".join(h.texts(dev)[:14]))
    if not h.has(dev, marker):
        raise h.StepMissing("history_open")


def _collapse_day(dev, p, stmts=None, marker="Groceries"):
    _start(dev, p)
    if stmts:
        _sql_relaunch(dev, p, stmts)
    _open_history(dev, p, marker)
    shown_before = h.has(dev, marker)
    h.go(dev, p, "collapse")
    return shown_before


# the Groceries expense moved to two days ago: another day group
GROCERIES_EARLIER = ("UPDATE transactions SET "
                     "date=((CAST(strftime('%s','now','start of day','-2 days','+12 hours') AS INTEGER))*1000) "
                     "WHERE comment='Groceries';")


def _target(dev, p):
    # the only expanded day group closes when its arrow is tapped
    before = _collapse_day(dev, p)
    hidden = not h.has(dev, "Groceries")
    return before and hidden and h.find(dev, p["nav"]["expand"]) is not None, {"groceries_before": before, "groceries_after": not hidden, "texts": h.texts(dev)[:30]}


def _held(dev, p):
    # Groceries is on an older day (collapsed); the newest day (Rent) is the only expanded group
    before = _collapse_day(dev, p, [GROCERIES_EARLIER], "Rent")
    hidden = not h.has(dev, "Rent")
    return before and hidden and h.find(dev, p["nav"]["expand"]) is not None, {"rent_before": before, "rent_after": not hidden, "texts": h.texts(dev)[:30]}


def _keep(dev, p):
    # untouched: the newest day group starts expanded, showing its expense and a collapse arrow
    _start(dev, p)
    _open_history(dev, p)
    return h.has(dev, "Groceries") and h.find(dev, p["nav"]["collapse"]) is not None, {"texts": h.texts(dev)[:30]}


def target(dev, params):
    return h.run(_target, dev, _p(params), TIER)


def held_out(dev, params):
    return h.run(_held, dev, _p(params), TIER)


def preserve(dev, params):
    return h.run(_keep, dev, _p(params), "A" if DB else "B")


CHECKS = {"target": target, "held_out": [held_out], "preservation": [preserve]}
