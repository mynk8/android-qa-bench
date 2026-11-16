"""Deterministic checks for amaze-0016. passed=True means intended behaviour (bug absent).
Each check re-seeds, drives the trigger through the Device API, then observes.
No wall-clock reads or sleeps; labels live in params["nav"] (bug.json)."""
from __future__ import annotations
from dataset_tools import check_helpers as h

APP = 'amaze'
PACKAGE = 'com.amaze.filemanager'
SEED = 'files_basic'
DB = ''
TIER = 'B'
PARAMS_DEFAULT = {'nav': {'count': [{'id': 'com.amaze.filemanager:id/item_count'}], 'select_all': [{'text': 'Select All'}], 'select_inverse': [{'text': 'Select Inverse'}]}}


def _p(params):
    p = dict(PARAMS_DEFAULT)
    p.update(params or {})
    return p

ROOT = "AndroidQA/Amaze"
def _home(dev, p):
    h.fresh(dev, APP, SEED)
    h.open_path(dev, ["AndroidQA", "Amaze"])

def _count(dev):
    """Text of the action-bar selection counter, or None when no action bar is shown."""
    for n in h.nodes(dev):
        if (n.get("id") or "").endswith("/item_count"):
            return (n.get("text") or "").strip()
    return None

def _choose(dev, p, step):
    """Open the selection dropdown (the counter in the action bar) and pick an entry."""
    h.go(dev, p, "count")
    h.go(dev, p, step)

def _all_then_inverse(dev, p, first):
    _home(dev, p)
    h.long_press(dev, first)
    _choose(dev, p, "select_all")
    _choose(dev, p, "select_inverse")
    return _count(dev)

def _target(dev, p):
    c = _all_then_inverse(dev, p, "notes.txt")
    return c is None, {"counter_after": c, "texts": h.texts(dev)[:30]}

def _held(dev, p):
    c = _all_then_inverse(dev, p, "Beta")
    return c is None and h.has(dev, "notes.txt"), {"counter_after": c, "texts": h.texts(dev)[:30]}

def _keep(dev, p):
    _home(dev, p)
    h.long_press(dev, "notes.txt")
    _choose(dev, p, "select_all")
    n = _count(dev)
    return bool(n) and n.isdigit() and int(n) >= 6, {"count": n}


def target(dev, params):
    return h.run(_target, dev, _p(params), TIER)


def held_out(dev, params):
    return h.run(_held, dev, _p(params), TIER)


def preserve(dev, params):
    return h.run(_keep, dev, _p(params), "A" if DB else "B")


CHECKS = {"target": target, "held_out": [held_out], "preservation": [preserve]}
