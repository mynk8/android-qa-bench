"""Deterministic checks for amaze-0018. passed=True means intended behaviour (bug absent).
Each check re-seeds, drives the trigger through the Device API, then observes.
No wall-clock reads or sleeps; labels live in params["nav"] (bug.json)."""
from __future__ import annotations
from dataset_tools import check_helpers as h

APP = 'amaze'
PACKAGE = 'com.amaze.filemanager'
SEED = 'files_basic'
DB = ''
TIER = 'B'
PARAMS_DEFAULT = {'nav': {'encrypt': [{'text': 'Encrypt'}], 'pw_field': [{'id': 'com.amaze.filemanager:id/edit_text_dialog_encrypt_password'}], 'pw_confirm': [{'id': 'com.amaze.filemanager:id/edit_text_dialog_encrypt_password_confirm'}]}}


def _p(params):
    p = dict(PARAMS_DEFAULT)
    p.update(params or {})
    return p

ROOT = "AndroidQA/Amaze"
def _home(dev, p):
    h.fresh(dev, APP, SEED)
    h.open_path(dev, ["AndroidQA", "Amaze"])

def _row_menu(dev, label):
    """Tap the three-dots button (desc 'Properties') on the row whose name is `label`.
    All rows share the same selector, so aim by the row's vertical position."""
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

def _dialog(dev, p, label):
    _home(dev, p)
    _row_menu(dev, label)
    h.go(dev, p, "encrypt")

def _dialog_open(dev, p):
    """Positive evidence that the Encrypt dialog is up (its password field exists)."""
    return h.find(dev, p["nav"]["pw_field"]) is not None

def _mismatch_shown(dev):
    return any("match" in t.lower() for t in h.texts(dev))

def _target(dev, p):
    _dialog(dev, p, "notes.txt")
    h.type_into(dev, p, "pw_field", "secret1")
    return _dialog_open(dev, p) and not _mismatch_shown(dev), {"texts": h.texts(dev)[:30]}

def _held(dev, p):
    _dialog(dev, p, "report+final.txt")
    h.type_into(dev, p, "pw_confirm", "secret1")
    return _dialog_open(dev, p) and not _mismatch_shown(dev), {"texts": h.texts(dev)[:30]}

def _keep(dev, p):
    _dialog(dev, p, "notes.txt")
    h.type_into(dev, p, "pw_field", "secret1")
    h.type_into(dev, p, "pw_confirm", "other2")
    return _mismatch_shown(dev), {"texts": h.texts(dev)[:30]}


def target(dev, params):
    return h.run(_target, dev, _p(params), TIER)


def held_out(dev, params):
    return h.run(_held, dev, _p(params), TIER)


def preserve(dev, params):
    return h.run(_keep, dev, _p(params), "A" if DB else "B")


CHECKS = {"target": target, "held_out": [held_out], "preservation": [preserve]}
