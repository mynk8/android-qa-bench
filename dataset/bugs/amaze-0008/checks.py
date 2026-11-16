"""Deterministic checks for amaze-0008. passed=True means intended behaviour (bug absent).
Each check re-seeds, drives the trigger through the Device API, then observes.
No wall-clock reads or sleeps; labels live in params["nav"] (bug.json)."""
from __future__ import annotations
from dataset_tools import check_helpers as h

APP = 'amaze'
PACKAGE = 'com.amaze.filemanager'
SEED = 'files_basic'
DB = ''
TIER = 'B'
PARAMS_DEFAULT = {'nav': {'overflow': [{'desc': 'More options'}], 'rename': [{'text': 'Rename'}], 'rename_field': [{'id': 'com.amaze.filemanager:id/singleedittext_input'}, {'text': 'report+final.txt'}, {'text': 'notes.txt'}], 'ok': [{'text': 'OK'}, {'text': 'SAVE'}, {'text': 'Save'}, {'text': 'CREATE'}], 'copy': [{'desc': 'Copy'}, {'text': 'Copy'}], 'paste': [{'desc': 'Paste'}, {'text': 'Paste'}, {'id': 'com.amaze.filemanager:id/paste'}], 'conflict_rename': [{'text': 'Rename'}, {'text': 'RENAME'}, {'text': 'KEEP BOTH'}], 'sort_by': [{'text': 'Sort By'}, {'text': 'Sort by'}, {'text': 'Sort'}], 'none_on_top': [{'text': 'None On Top'}, {'text': 'None on top'}], 'folders_on_top': [{'text': 'Folders On Top'}, {'text': 'Folders on top'}], 'delete': [{'desc': 'Delete'}, {'text': 'Delete'}], 'delete_confirm': [{'text': 'DELETE'}, {'text': 'Delete'}], 'drawer': [{'desc': 'Navigate up'}, {'desc': 'Open navigation drawer'}, {'desc': 'Open drawer'}], 'images': [{'text': 'Images'}], 'settings': [{'text': 'Settings'}], 'bookmarks_pref': [{'text': 'Bookmarks'}], 'add': [{'desc': 'Add'}, {'text': 'Add'}, {'text': 'ADD'}], 'name_field': [{'text': 'Name'}, {'id': 'com.amaze.filemanager:id/text1'}], 'path_field': [{'text': 'Path'}, {'id': 'com.amaze.filemanager:id/text2'}], 'search': [{'desc': 'Search'}], 'search_field': [{'id': 'com.amaze.filemanager:id/search_edit_text'}, {'text': 'Search'}], 'deep_search': [{'text': 'Try Indexed Search!'}, {'text': 'Try indexed search'}], 'add_connection': [{'text': 'SMB Connection'}, {'text': 'Cloud Connection'}, {'text': 'New Cloud Connection'}, {'desc': 'Add'}], 'smb': [{'text': 'SMB Connection'}, {'text': 'SMB'}], 'extract': [{'text': 'Extract'}], 'sort_menu': [{'desc': 'Sort'}, {'text': 'Sort'}], 'dir_sort': [{'text': 'Directory Sort Mode'}]}}


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

HEADERS = ("folders", "files")
def _sort(dev, p, choice):
    """Sort icon (or overflow > Sort) > Directory Sort Mode > pick the mode. The mode list is
    a single-choice dialog that applies and closes on tap, so there is no OK step."""
    _home(dev, p)
    if not h.go_opt(dev, p, "sort_menu"):
        h.go(dev, p, "overflow")
        h.go(dev, p, "sort_menu")
    h.go(dev, p, "dir_sort")
    h.go(dev, p, choice)

def _no_headers(dev):
    hdr = [x for x in HEADERS if h.has_exact_ci(dev, x)]
    return not hdr and h.has(dev, "Alpha") and h.has(dev, "notes.txt"), {"headers": hdr, "texts": h.texts(dev)[:40]}

def _target(dev, p):
    _sort(dev, p, "none_on_top")
    return _no_headers(dev)

def _held(dev, p):
    _sort(dev, p, "none_on_top")
    h.relaunch(dev, PACKAGE)
    h.open_path(dev, ["AndroidQA", "Amaze"])
    return _no_headers(dev)

def _keep(dev, p):
    _sort(dev, p, "folders_on_top")
    return h.has_exact_ci(dev, "folders"), {"texts": h.texts(dev)[:40]}


def target(dev, params):
    return h.run(_target, dev, _p(params), TIER)


def held_out(dev, params):
    return h.run(_held, dev, _p(params), TIER)


def preserve(dev, params):
    return h.run(_keep, dev, _p(params), "A" if DB else "B")


CHECKS = {"target": target, "held_out": [held_out], "preservation": [preserve]}
