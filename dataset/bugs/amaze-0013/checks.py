"""Deterministic checks for amaze-0013. passed=True means intended behaviour (bug absent).
Each check re-seeds, drives the trigger through the Device API, then observes.
No wall-clock reads or sleeps; labels live in params["nav"] (bug.json)."""
from __future__ import annotations
from dataset_tools import check_helpers as h

APP = 'amaze'
PACKAGE = 'com.amaze.filemanager'
SEED = 'files_basic'
DB = ''
TIER = 'B'
PARAMS_DEFAULT = {'nav': {'drawer': [{'desc': 'Navigate up'}, {'desc': 'Open navigation drawer'}, {'desc': 'Open drawer'}], 'overflow': [{'desc': 'More options'}], 'images': [{'text': 'Images'}], 'documents': [{'text': 'Documents'}], 'home_btn': [{'desc': 'Home'}, {'text': 'Home'}], 'fab': [{'id': 'com.amaze.filemanager:id/fabs_menu'}, {'id': 'com.amaze.filemanager:id/sd_main_fab'}]}}


def _p(params):
    p = dict(PARAMS_DEFAULT)
    p.update(params or {})
    return p

ROOT = "AndroidQA/Amaze"
def _category(dev, p, key):
    h.fresh(dev, APP, SEED)
    h.go(dev, p, "drawer")
    if h.find(dev, p["nav"][key]) is None:
        dev.scroll_to({"text": p["nav"][key][0]["text"]})   # the drawer list is longer than the screen
    h.go(dev, p, key)

def _home_button(dev, p):
    if not h.go_opt(dev, p, "home_btn"):
        h.go(dev, p, "overflow")
        h.go(dev, p, "home_btn")

def _fab_after_home(dev, p, key):
    _category(dev, p, key)
    _home_button(dev, p)
    fab = h.find(dev, p["nav"]["fab"]) is not None
    return fab and h.has(dev, "AndroidQA"), {"fab": fab, "texts": h.texts(dev)[:40]}

def _target(dev, p):
    return _fab_after_home(dev, p, "images")

def _held(dev, p):
    return _fab_after_home(dev, p, "documents")

def _keep(dev, p):
    h.fresh(dev, APP, SEED)
    h.open_path(dev, ["AndroidQA", "Amaze"])
    _home_button(dev, p)
    fab = h.find(dev, p["nav"]["fab"]) is not None
    return fab and h.has(dev, "AndroidQA") and not h.has(dev, "notes.txt"), {"fab": fab, "texts": h.texts(dev)[:40]}


def target(dev, params):
    return h.run(_target, dev, _p(params), TIER)


def held_out(dev, params):
    return h.run(_held, dev, _p(params), TIER)


def preserve(dev, params):
    return h.run(_keep, dev, _p(params), "A" if DB else "B")


CHECKS = {"target": target, "held_out": [held_out], "preservation": [preserve]}
