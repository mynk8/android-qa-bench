"""Deterministic checks for iris-0011. passed=True means intended behaviour (bug absent).
Each check re-seeds, drives the trigger through the Device API, then observes.
No wall-clock reads or sleeps; labels live in params["nav"] (bug.json)."""
from __future__ import annotations
from dataset_tools import check_helpers as h

APP = 'iris'
PACKAGE = 'com.iris.gallery'
SEED = 'album_basic'
DB = ''
TIER = 'B'
PARAMS_DEFAULT = {'nav': {'filter_btn': [{'desc': 'Filter'}], 'opt_media': [{'text': 'Media ('}], 'opt_photos': [{'text': 'Photos ('}], 'opt_videos': [{'text': 'Videos ('}]}}


def _p(params):
    p = dict(PARAMS_DEFAULT)
    p.update(params or {})
    return p

def _start(dev, p):
    h.fresh(dev, APP, SEED)


def _choose(dev, p, option):
    h.go(dev, p, "filter_btn")
    h.go(dev, p, option)


def _persisted(dev, p, option, label):
    _start(dev, p)
    _choose(dev, p, option)
    before = h.has_exact_ci(dev, label)
    h.relaunch(dev, PACKAGE)
    after = h.has_exact_ci(dev, label)
    return before and after, {"label_before": before, "label_after_restart": after, "texts": h.texts(dev)[:30]}


def _target(dev, p):
    # the Photos filter chosen on the Media tab is still active after the app is restarted
    return _persisted(dev, p, "opt_photos", "Photos")


def _held(dev, p):
    return _persisted(dev, p, "opt_videos", "Videos")


def _settle(dev, rounds=6):
    """Wait (bounded) until the seed photos are indexed and the grid shows them."""
    for _ in range(rounds):
        if h.has(dev, "big.jpg") or h.has(dev, "huge.jpg"):
            return True
        dev.wait_idle()
    return False


def _keep(dev, p):
    # the filter menu lists the three choices and picking one relabels the Media tab at once
    _start(dev, p)
    h.go(dev, p, "filter_btn")
    listed = all(h.find(dev, p["nav"][k]) is not None for k in ("opt_media", "opt_photos", "opt_videos"))
    h.go(dev, p, "opt_photos")
    grid = _settle(dev)
    return listed and h.has_exact_ci(dev, "Photos"), {"listed": listed, "grid_has_photos": grid, "texts": h.texts(dev)[:30]}


def target(dev, params):
    return h.run(_target, dev, _p(params), TIER)


def held_out(dev, params):
    return h.run(_held, dev, _p(params), TIER)


def preserve(dev, params):
    return h.run(_keep, dev, _p(params), "A" if DB else "B")


CHECKS = {"target": target, "held_out": [held_out], "preservation": [preserve]}
