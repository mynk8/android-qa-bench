"""Deterministic checks for amaze-0014. passed=True means intended behaviour (bug absent).
Each check re-seeds, drives the trigger through the Device API, then observes.
No wall-clock reads or sleeps; labels live in params["nav"] (bug.json)."""
from __future__ import annotations
from dataset_tools import check_helpers as h

APP = 'amaze'
PACKAGE = 'com.amaze.filemanager'
SEED = 'files_basic'
DB = ''
TIER = 'A'
PARAMS_DEFAULT = {'nav': {'drawer': [{'desc': 'Navigate up'}, {'desc': 'Open navigation drawer'}, {'desc': 'Open drawer'}], 'overflow': [{'desc': 'More options'}], 'images': [{'text': 'Images'}], 'rename': [{'text': 'Rename'}], 'rename_field': [{'id': 'com.amaze.filemanager:id/singleedittext_input'}], 'ok': [{'text': 'Save'}, {'text': 'SAVE'}, {'text': 'OK'}]}}


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

def _images(dev, p):
    h.fresh(dev, APP, SEED)
    h.go(dev, p, "drawer")
    if h.find(dev, p["nav"]["images"]) is None:
        dev.scroll_to({"text": p["nav"]["images"][0]["text"]})   # the drawer list is longer than the screen
    h.go(dev, p, "images")

def _rename_in_images(dev, p, old, new):
    _images(dev, p)
    _rename_dialog(dev, p, old)
    h.type_into(dev, p, "rename_field", new)
    h.go(dev, p, "ok")

def _target(dev, p):
    _rename_in_images(dev, p, "photo.jpg", "photo-renamed.jpg")
    texts = h.texts(dev)[:60]          # the Images list the tester looks at
    shown = "photo-renamed.jpg" in texts and "photo.jpg" not in texts
    names = h.list_ext(dev, ROOT)
    return shown and "photo-renamed.jpg" in names and "photo.jpg" not in names, {"names": names, "images_list": texts}

def _held(dev, p):
    _rename_in_images(dev, p, "keep.jpg", "keep-2.jpg")
    h.relaunch(dev, PACKAGE)
    h.open_path(dev, ["AndroidQA", "Amaze"])
    return h.has(dev, "keep-2.jpg") and not h.has(dev, "keep.jpg"), {"texts": h.texts(dev)[:60]}

def _keep(dev, p):
    _home(dev, p)
    _rename_dialog(dev, p, "notes.txt")
    h.type_into(dev, p, "rename_field", "notes2.txt")
    h.go(dev, p, "ok")
    names = h.list_ext(dev, ROOT)
    return "notes2.txt" in names and "notes.txt" not in names, {"names": names}


def target(dev, params):
    return h.run(_target, dev, _p(params), TIER)


def held_out(dev, params):
    return h.run(_held, dev, _p(params), TIER)


def preserve(dev, params):
    return h.run(_keep, dev, _p(params), "A" if DB else "B")


CHECKS = {"target": target, "held_out": [held_out], "preservation": [preserve]}
