"""Deterministic checks for markor-0014. passed=True means intended behaviour (bug absent).
Each check re-seeds, drives the trigger through the Device API, then observes.
No wall-clock reads or sleeps; labels live in params["nav"] (bug.json)."""
from __future__ import annotations
import re
from dataset_tools import check_helpers as h

APP = 'markor'
PACKAGE = 'net.gsantner.markor'
SEED = 'notebook_basic'
DB = ''
TIER = 'A'
PARAMS_DEFAULT = {'nav': {'files_tab': [{'text': 'Files'}, {'desc': 'Files'}], 'edit_mode': [{'desc': 'Edit'}, {'id': 'net.gsantner.markor:id/fab_edit'}], 'editor': [{'id': 'net.gsantner.markor:id/document__fragment__edit__highlighting_editor'}], 'bold': [{'desc': 'Bold'}, {'text': 'Bold'}], 'quote': [{'desc': 'Quote'}, {'text': 'Quote'}]}}

def _p(params):
    p = dict(PARAMS_DEFAULT)
    p.update(params or {})
    return p

ROOT = "Documents/markor"
PREFS = "shared_prefs/app.xml"


def _files(dev, p):
    (h.find(dev, [{"text": "Shopping.md"}]) is None and h.go_opt(dev, p, "files_tab"))
    (h.find(dev, [{"text": "Shopping.md"}]) is None and h.open_path(dev, ["markor"]))


def _home(dev, p):
    h.fresh(dev, APP, SEED)
    _files(dev, p)


def _pref(dev, line):
    """Store one app preference, then start the app again (it reads its settings at launch)."""
    dev.force_stop(PACKAGE)
    try:
        raw = dev.read_file(PREFS).decode("utf-8", "replace")
    except Exception:
        raw = ""
    raw = raw.replace("<map />", "<map>\n</map>")
    if "</map>" in raw:
        raw = raw.replace("</map>", "    " + line + "\n</map>")
    else:
        raw = "<?xml version='1.0' encoding='utf-8' standalone='yes' ?>\n<map>\n    " + line + "\n</map>\n"
    dev.write_file(PREFS, raw.encode("utf-8"))
    dev.launch(PACKAGE)
    dev.wait_idle()
    h.dismiss_first_run(dev, APP)


def _reopen(dev, p, name):
    h.tap_text(dev, name)
    h.go_opt(dev, p, "edit_mode")
    h.go_opt(dev, p, "editor")


def _open_doc(dev, p, name):
    _home(dev, p)
    _reopen(dev, p, name)


def _leave(dev):
    dev.back(); dev.wait_idle()   # Markor saves the document when leaving the editor
    dev.back(); dev.wait_idle()


def _reveal(dev, p, step):
    """The editor action bar scrolls horizontally: swipe it until the action shows."""
    for _ in range(8):
        if h.find(dev, p["nav"][step]) is not None:
            return
        ns = h.nodes(dev)
        bar = [n for n in ns if str(n.get("id") or "").endswith("document__fragment__edit__text_actions_bar")]
        if not bar:
            return
        x1, y1, x2, y2 = bar[0]["bounds"]
        kids = [n for n in ns if n.get("desc") and n.get("bounds") and n["bounds"][1] >= y1 - 5
                and n["bounds"][3] <= y2 + 5 and n["bounds"][0] >= x1]
        if not kids:
            return
        # avoid the screen edge (a swipe from there is the system back gesture)
        kids = [n for n in kids if n["bounds"][2] <= 690] or kids
        kids.sort(key=lambda n: n["bounds"][2])
        dev.swipe({"desc": kids[-1]["desc"]}, "left")
        dev.wait_idle()


def _tap(dev, p, step):
    _reveal(dev, p, step)
    h.go(dev, p, step)


def _read(dev, name):
    return h.read_ext(dev, ROOT + "/" + name)


def _long_bold(dev, p, doc, up=False):
    _open_doc(dev, p, doc)
    up and h.key(dev, "DPAD_UP")
    _reveal(dev, p, "bold")
    h.long_press(dev, "Bold")
    _leave(dev)
    return _read(dev, doc)


def _target(dev, p):
    c = _long_bold(dev, p, "Single.md")
    return c is not None and c.rstrip("\n") == "**gamma**", {"content": c}


def _held(dev, p):
    c = _long_bold(dev, p, "Regex.md", up=True)
    return c is not None and c.rstrip("\n") == "**cat@home**", {"content": c}


def _keep(dev, p):
    _open_doc(dev, p, "Single.md")
    _tap(dev, p, "quote")
    _leave(dev)
    c = _read(dev, "Single.md")
    return c is not None and c.rstrip("\n") == "> gamma", {"content": c}


def target(dev, params):
    return h.run(_target, dev, _p(params), TIER)


def held_out(dev, params):
    return h.run(_held, dev, _p(params), TIER)


def preserve(dev, params):
    return h.run(_keep, dev, _p(params), "A" if DB else "B")


CHECKS = {"target": target, "held_out": [held_out], "preservation": [preserve]}
