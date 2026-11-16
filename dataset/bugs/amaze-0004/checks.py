"""Deterministic checks for amaze-0004. passed=True means intended behaviour (bug absent).
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

def _copy_alpha_here(dev, p):
    _home(dev, p)
    h.long_press(dev, "Alpha")
    if not h.go_opt(dev, p, "copy"):
        h.go(dev, p, "overflow"); h.go(dev, p, "copy")
    h.go(dev, p, "paste")
    h.go_opt(dev, p, "conflict_rename")
    h.go_opt(dev, p, "ok")

def _dup(names):
    """The incremented copy of Alpha ('Alpha (1)' at the head, 'Alpha(1)' in older builds)."""
    return next((n for n in names if n != "Alpha" and n.startswith("Alpha") and "(1)" in n), None)

def _target(dev, p):
    _copy_alpha_here(dev, p)
    names = h.list_ext(dev, ROOT)
    dup = _dup(names)
    inner = h.list_ext(dev, ROOT + "/" + dup) if dup else []
    return dup is not None and "readme.txt" in inner, {"names": names, "dup": dup, "inner": inner}

def _held(dev, p):
    _copy_alpha_here(dev, p)
    h.relaunch(dev, PACKAGE)
    h.open_path(dev, ["AndroidQA", "Amaze"])
    dup = _dup(h.list_ext(dev, ROOT))
    if dup is None or not h.has(dev, dup):
        return False, {"texts": h.texts(dev)[:40]}
    h.tap_text(dev, dup)
    return h.has(dev, "readme.txt"), {"texts": h.texts(dev)[:40]}

def _keep(dev, p):
    """A plain file pasted into its own folder with Rename gets a numbered copy."""
    _home(dev, p)
    h.long_press(dev, "notes.txt")
    if not h.go_opt(dev, p, "copy"):
        h.go(dev, p, "overflow"); h.go(dev, p, "copy")
    h.go(dev, p, "paste")
    h.go_opt(dev, p, "conflict_rename")
    h.go_opt(dev, p, "ok")
    names = h.list_ext(dev, ROOT)
    dup = next((n for n in names if n != "notes.txt" and n.startswith("notes") and "(1)" in n), None)
    return dup is not None and "notes.txt" in names, {"names": names, "dup": dup}


def target(dev, params):
    return h.run(_target, dev, _p(params), TIER)


def held_out(dev, params):
    return h.run(_held, dev, _p(params), TIER)


def preserve(dev, params):
    return h.run(_keep, dev, _p(params), "A" if DB else "B")


CHECKS = {"target": target, "held_out": [held_out], "preservation": [preserve]}
