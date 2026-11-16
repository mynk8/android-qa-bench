"""Deterministic checks for amaze-0015. passed=True means intended behaviour (bug absent).
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

def _all_twice(dev, p, first):
    _home(dev, p)
    h.long_press(dev, first)
    _choose(dev, p, "select_all")
    n1 = _count(dev)
    _choose(dev, p, "select_all")
    n2 = _count(dev)
    return n1, n2

def _ok(n1, n2):
    return bool(n1) and n1.isdigit() and int(n1) >= 6 and n2 == n1

def _target(dev, p):
    n1, n2 = _all_twice(dev, p, "notes.txt")
    return _ok(n1, n2), {"after_first": n1, "after_second": n2}

def _held(dev, p):
    n1, n2 = _all_twice(dev, p, "Alpha")
    return _ok(n1, n2) and h.has(dev, "notes.txt"), {"after_first": n1, "after_second": n2}

def _keep(dev, p):
    _home(dev, p)
    h.long_press(dev, "notes.txt")
    one = _count(dev)
    _choose(dev, p, "select_inverse")
    n = _count(dev)
    return one == "1" and n == "5", {"start": one, "after_inverse": n}


def target(dev, params):
    return h.run(_target, dev, _p(params), TIER)


def held_out(dev, params):
    return h.run(_held, dev, _p(params), TIER)


def preserve(dev, params):
    return h.run(_keep, dev, _p(params), "A" if DB else "B")


CHECKS = {"target": target, "held_out": [held_out], "preservation": [preserve]}
