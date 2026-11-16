"""Deterministic checks for amaze-0019. passed=True means intended behaviour (bug absent).
Each check re-seeds, drives the trigger through the Device API, then observes.
No wall-clock reads or sleeps; labels live in params["nav"] (bug.json)."""
from __future__ import annotations
from dataset_tools import check_helpers as h

APP = 'amaze'
PACKAGE = 'com.amaze.filemanager'
SEED = 'files_basic'
DB = ''
TIER = 'B'
PARAMS_DEFAULT = {'nav': {'overflow': [{'desc': 'More options'}], 'rename': [{'text': 'Rename'}], 'rename_field': [{'id': 'com.amaze.filemanager:id/singleedittext_input'}]}}


def _p(params):
    p = dict(PARAMS_DEFAULT)
    p.update(params or {})
    return p

ROOT = "AndroidQA/Amaze"
def _home(dev, p):
    h.fresh(dev, APP, SEED)
    h.open_path(dev, ["AndroidQA", "Amaze"])

def _row_menu(dev, label):
    """Tap the three-dots button (desc 'Properties') on the row whose name is `label`."""
    ns = h.nodes(dev)
    row = next((n for n in ns if n.get("text") == label and n.get("bounds")), None)
    if row is None:
        raise h.StepMissing("row:" + label)
    cy = (row["bounds"][1] + row["bounds"][3]) // 2
    btns = [n for n in ns if n.get("desc") == "Properties" and n.get("bounds")
            and n["bounds"][1] - 40 <= cy <= n["bounds"][3] + 40]
    if not btns or not hasattr(dev, "tap_xy"):
        raise h.StepMissing("row_menu:" + label)
    x1, y1, x2, y2 = btns[0]["bounds"]
    dev.tap_xy((x1 + x2) // 2, (y1 + y2) // 2)
    dev.wait_idle()

def _rename_dialog(dev, p, label):
    """Row three-dots button (desc 'Properties') > Rename. Long-press action mode has no Rename on device."""
    _row_menu(dev, label)
    h.go(dev, p, "rename")

def _notice(dev):
    return any("no changes" in t.lower() for t in h.texts(dev))

def _target(dev, p):
    _home(dev, p)
    _rename_dialog(dev, p, "notes.txt")
    h.type_into(dev, p, "rename_field", "notes.txt")
    return _notice(dev), {"texts": h.texts(dev)[:30]}

def _held(dev, p):
    _home(dev, p)
    _rename_dialog(dev, p, "Alpha")
    h.type_into(dev, p, "rename_field", "Alpha")
    return _notice(dev), {"texts": h.texts(dev)[:30]}

def _keep(dev, p):
    _home(dev, p)
    _rename_dialog(dev, p, "notes.txt")
    h.type_into(dev, p, "rename_field", " bad")
    return any("invalid" in t.lower() for t in h.texts(dev)) and not _notice(dev), {"texts": h.texts(dev)[:30]}


def target(dev, params):
    return h.run(_target, dev, _p(params), TIER)


def held_out(dev, params):
    return h.run(_held, dev, _p(params), TIER)


def preserve(dev, params):
    return h.run(_keep, dev, _p(params), "A" if DB else "B")


CHECKS = {"target": target, "held_out": [held_out], "preservation": [preserve]}
