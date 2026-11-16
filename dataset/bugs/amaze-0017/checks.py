"""Deterministic checks for amaze-0017. passed=True means intended behaviour (bug absent).
Each check re-seeds, drives the trigger through the Device API, then observes.
No wall-clock reads or sleeps; labels live in params["nav"] (bug.json)."""
from __future__ import annotations
from dataset_tools import check_helpers as h

APP = 'amaze'
PACKAGE = 'com.amaze.filemanager'
SEED = 'files_basic'
DB = ''
TIER = 'A'
PARAMS_DEFAULT = {'nav': {'overflow': [{'desc': 'More options'}], 'copy': [{'desc': 'Copy'}, {'text': 'Copy'}], 'paste': [{'desc': 'Paste'}, {'text': 'Paste'}, {'id': 'com.amaze.filemanager:id/paste'}]}}


def _p(params):
    p = dict(PARAMS_DEFAULT)
    p.update(params or {})
    return p

ROOT = "AndroidQA/Amaze"
def _home(dev, p):
    h.fresh(dev, APP, SEED)
    h.open_path(dev, ["AndroidQA", "Amaze"])

def _copy(dev, p, label):
    h.long_press(dev, label)
    if not h.go_opt(dev, p, "copy"):
        h.go(dev, p, "overflow")
        h.go(dev, p, "copy")

def _paste_into_self(dev, p, name):
    _home(dev, p)
    _copy(dev, p, name)
    h.tap_text(dev, name)
    h.go(dev, p, "paste")
    names = h.list_ext(dev, ROOT + "/" + name)
    for _ in range(6):   # the copy runs in a background service
        if name in names:
            break
        dev.wait_idle()
        names = h.list_ext(dev, ROOT + "/" + name)
    return names

def _target(dev, p):
    names = _paste_into_self(dev, p, "Alpha")
    return "Alpha" not in names and "readme.txt" in names, {"inner": names}

def _held(dev, p):
    names = _paste_into_self(dev, p, "Beta")
    return "Beta" not in names and "readme.txt" in names, {"inner": names}

def _keep(dev, p):
    _home(dev, p)
    _copy(dev, p, "Alpha")
    h.tap_text(dev, "Beta")
    h.go(dev, p, "paste")
    inner = h.list_ext(dev, ROOT + "/Beta/Alpha")
    for _ in range(6):
        if "readme.txt" in inner:
            break
        dev.wait_idle()
        inner = h.list_ext(dev, ROOT + "/Beta/Alpha")
    return "readme.txt" in inner, {"inner": inner}


def target(dev, params):
    return h.run(_target, dev, _p(params), TIER)


def held_out(dev, params):
    return h.run(_held, dev, _p(params), TIER)


def preserve(dev, params):
    return h.run(_keep, dev, _p(params), "A" if DB else "B")


CHECKS = {"target": target, "held_out": [held_out], "preservation": [preserve]}
