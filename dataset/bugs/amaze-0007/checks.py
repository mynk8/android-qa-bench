"""Deterministic checks for amaze-0007. passed=True means intended behaviour (bug absent).
Each check re-seeds, drives the trigger through the Device API, then observes.
No wall-clock reads or sleeps; labels live in params["nav"] (bug.json)."""
from __future__ import annotations
from dataset_tools import check_helpers as h

APP = 'amaze'
PACKAGE = 'com.amaze.filemanager'
SEED = 'files_basic'
DB = ''
TIER = 'A'
PARAMS_DEFAULT = {'nav': {'overflow': [{'desc': 'More options'}], 'rename': [{'text': 'Rename'}], 'rename_field': [{'id': 'com.amaze.filemanager:id/singleedittext_input'}, {'text': 'report+final.txt'}, {'text': 'notes.txt'}], 'ok': [{'text': 'OK'}, {'text': 'SAVE'}, {'text': 'Save'}, {'text': 'CREATE'}], 'copy': [{'desc': 'Copy'}, {'text': 'Copy'}], 'paste': [{'desc': 'Paste'}, {'text': 'Paste'}, {'id': 'com.amaze.filemanager:id/paste'}], 'conflict_rename': [{'text': 'Rename'}, {'text': 'RENAME'}, {'text': 'KEEP BOTH'}], 'sort_by': [{'text': 'Sort By'}, {'text': 'Sort by'}, {'text': 'Sort'}], 'none_on_top': [{'text': 'None On Top'}, {'text': 'None on top'}], 'folders_on_top': [{'text': 'Folders On Top'}, {'text': 'Folders on top'}], 'delete': [{'desc': 'Delete'}, {'text': 'Delete'}], 'delete_confirm': [{'text': 'DELETE'}, {'text': 'Delete'}], 'drawer': [{'desc': 'Navigate up'}, {'desc': 'Open navigation drawer'}, {'desc': 'Open drawer'}], 'images': [{'text': 'Images'}], 'settings': [{'text': 'Settings'}], 'bookmarks_pref': [{'text': 'Bookmarks'}], 'add': [{'desc': 'Add'}, {'text': 'Add'}, {'text': 'ADD'}], 'name_field': [{'text': 'Name'}, {'id': 'com.amaze.filemanager:id/text1'}], 'path_field': [{'text': 'Path'}, {'id': 'com.amaze.filemanager:id/text2'}], 'search': [{'desc': 'Search'}], 'search_field': [{'id': 'com.amaze.filemanager:id/search_edit_text'}, {'text': 'Search'}], 'deep_search': [{'text': 'Try Indexed Search!'}, {'text': 'Try indexed search'}], 'add_connection': [{'text': 'SMB Connection'}, {'text': 'Cloud Connection'}, {'text': 'New Cloud Connection'}, {'desc': 'Add'}], 'smb': [{'text': 'SMB Connection'}, {'text': 'SMB'}], 'extract': [{'text': 'Extract'}]}}


def _p(params):
    p = dict(PARAMS_DEFAULT)
    p.update(params or {})
    return p

ROOT = "AndroidQA/Amaze"
def _home(dev, p):
    h.fresh(dev, APP, SEED)
    h.open_path(dev, ["AndroidQA", "Amaze"])

def _rename(dev, p, old, new):
    _home(dev, p)
    h.long_press(dev, old)
    if not h.go_opt(dev, p, "rename"):
        h.go(dev, p, "overflow")
        h.go(dev, p, "rename")
    h.type_into(dev, p, "rename_field", new)
    h.go(dev, p, "ok")

def _paste_into_beta(dev, p, times):
    _home(dev, p)
    for _ in range(times):
        h.tap_text(dev, "Alpha")
        h.long_press(dev, "readme.txt")
        if not h.go_opt(dev, p, "copy"):
            h.go(dev, p, "overflow"); h.go(dev, p, "copy")
        dev.back(); dev.wait_idle()
        h.tap_text(dev, "Beta")
        h.go(dev, p, "paste")
        h.go(dev, p, "conflict_rename")
        h.go_opt(dev, p, "ok")
        dev.back(); dev.wait_idle()

def _target(dev, p):
    _paste_into_beta(dev, p, 2)
    names = h.list_ext(dev, ROOT + "/Beta")
    return {"readme.txt", "readme (1).txt", "readme (2).txt"} <= set(names), {"beta": names}

def _held(dev, p):
    _paste_into_beta(dev, p, 2)
    h.relaunch(dev, PACKAGE)
    h.open_path(dev, ["AndroidQA", "Amaze", "Beta"])
    return h.has(dev, "readme (2).txt"), {"texts": h.texts(dev)[:40]}

def _keep(dev, p):
    _paste_into_beta(dev, p, 1)
    names = h.list_ext(dev, ROOT + "/Beta")
    return {"readme.txt", "readme (1).txt"} <= set(names), {"beta": names}


def target(dev, params):
    return h.run(_target, dev, _p(params), TIER)


def held_out(dev, params):
    return h.run(_held, dev, _p(params), TIER)


def preserve(dev, params):
    return h.run(_keep, dev, _p(params), "A" if DB else "B")


CHECKS = {"target": target, "held_out": [held_out], "preservation": [preserve]}
