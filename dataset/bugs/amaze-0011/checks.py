"""Deterministic checks for amaze-0011. passed=True means intended behaviour (bug absent).
Each check re-seeds, drives the trigger through the Device API, then observes.
No wall-clock reads or sleeps; labels live in params["nav"] (bug.json)."""
from __future__ import annotations
from dataset_tools import check_helpers as h

APP = 'amaze'
PACKAGE = 'com.amaze.filemanager'
SEED = 'files_basic'
DB = ''
TIER = 'B'
PARAMS_DEFAULT = {'nav': {'overflow': [{'desc': 'More options'}], 'rename': [{'text': 'Rename'}], 'rename_field': [{'id': 'com.amaze.filemanager:id/singleedittext_input'}, {'text': 'report+final.txt'}, {'text': 'notes.txt'}], 'ok': [{'text': 'OK'}, {'text': 'SAVE'}, {'text': 'Save'}, {'text': 'CREATE'}], 'copy': [{'desc': 'Copy'}, {'text': 'Copy'}], 'paste': [{'desc': 'Paste'}, {'text': 'Paste'}, {'id': 'com.amaze.filemanager:id/paste'}], 'conflict_rename': [{'text': 'Rename'}, {'text': 'RENAME'}, {'text': 'KEEP BOTH'}], 'sort_by': [{'text': 'Sort By'}, {'text': 'Sort by'}, {'text': 'Sort'}], 'none_on_top': [{'text': 'None On Top'}, {'text': 'None on top'}], 'folders_on_top': [{'text': 'Folders On Top'}, {'text': 'Folders on top'}], 'delete': [{'desc': 'Delete'}, {'text': 'Delete'}], 'delete_confirm': [{'text': 'DELETE'}, {'text': 'Delete'}], 'drawer': [{'desc': 'Navigate up'}, {'desc': 'Open navigation drawer'}, {'desc': 'Open drawer'}], 'images': [{'text': 'Images'}], 'settings': [{'text': 'Settings'}], 'bookmarks_pref': [{'text': 'Bookmarks'}], 'add': [{'desc': 'Add'}, {'text': 'Add'}, {'text': 'ADD'}], 'name_field': [{'text': 'Name'}, {'id': 'com.amaze.filemanager:id/text1'}], 'path_field': [{'text': 'Path'}, {'id': 'com.amaze.filemanager:id/text2'}], 'search': [{'desc': 'Search'}], 'search_field': [{'id': 'com.amaze.filemanager:id/search_edit_text'}, {'text': 'Search'}], 'deep_search': [{'text': 'Try Indexed Search!'}, {'text': 'Try indexed search'}], 'add_connection': [{'text': 'SMB Connection'}, {'text': 'Cloud Connection'}, {'text': 'New Cloud Connection'}, {'desc': 'Add'}], 'smb': [{'text': 'SMB Connection'}, {'text': 'SMB'}], 'extract': [{'text': 'Extract'}]}}


def _p(params):
    p = dict(PARAMS_DEFAULT)
    p.update(params or {})
    return p

ALPHA = "/storage/emulated/0/AndroidQA/Amaze/Alpha"
BETA = "/storage/emulated/0/AndroidQA/Amaze/Beta"
def _open(dev, p):
    h.fresh(dev, APP, SEED)
    h.go(dev, p, "drawer")
    if h.find(dev, p["nav"]["settings"]) is None:
        dev.scroll_to({"text": "Settings"})   # the drawer list is longer than the screen
    h.go(dev, p, "settings")
    h.go(dev, p, "interface")
    _reveal_bm = h.find(dev, p["nav"]["bookmarks_pref"]) is None
    if _reveal_bm:
        dev.scroll_to({"text": "Bookmarks"})
    h.go(dev, p, "bookmarks_pref")
    for _ in range(4):   # the sub-screen opens after a short transition
        if h.find(dev, p["nav"]["add"]) is not None:
            break
        dev.wait_idle()

def _add(dev, p, name, path):
    h.go(dev, p, "add")
    h.type_into(dev, p, "name_field", name)
    if path:
        h.type_into(dev, p, "path_field", path)
    h.go(dev, p, "ok")
    if any(t.strip().upper() == "CANCEL" for t in h.texts(dev)):   # dialog stayed open after rejection
        h.tap_text(dev, "CANCEL")
        if any(t.strip().upper() == "CANCEL" for t in h.texts(dev)):   # first tap only closed the keyboard
            h.tap_text(dev, "CANCEL")

def _target(dev, p):
    _open(dev, p)
    _add(dev, p, "Docs", ALPHA)
    _add(dev, p, "Docs2", ALPHA)
    return h.has(dev, "Docs") and not h.has(dev, "Docs2"), {"texts": h.texts(dev)[:40]}

def _held(dev, p):
    # same name, different path: the head rejects it as an existing bookmark (name match)
    _open(dev, p)
    _add(dev, p, "Docs", ALPHA)
    _add(dev, p, "Docs", BETA)
    ts = h.texts(dev)
    return ts.count("Docs") == 1 and BETA not in ts, {"texts": ts[:40]}

def _keep(dev, p):
    _open(dev, p)
    _add(dev, p, "Docs", ALPHA)
    _add(dev, p, "BetaMark", BETA)
    return h.has(dev, "Docs") and h.has(dev, "BetaMark"), {"texts": h.texts(dev)[:40]}


def target(dev, params):
    return h.run(_target, dev, _p(params), TIER)


def held_out(dev, params):
    return h.run(_held, dev, _p(params), TIER)


def preserve(dev, params):
    return h.run(_keep, dev, _p(params), "A" if DB else "B")


CHECKS = {"target": target, "held_out": [held_out], "preservation": [preserve]}
