"""Deterministic checks for amaze-0003. passed=True means intended behaviour (bug absent).
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

def _rename(dev, p, old, new):
    _home(dev, p)
    _row_menu(dev, old)
    h.go(dev, p, "rename")
    h.type_into(dev, p, "rename_field", new)
    h.go(dev, p, "ok")

def _target(dev, p):
    _rename(dev, p, "report+final.txt", "report-final.txt")
    names = h.list_ext(dev, ROOT)
    return "report-final.txt" in names and "report+final.txt" not in names, {"names": names}

def _held(dev, p):
    _rename(dev, p, "report+final.txt", "report-final.txt")
    h.relaunch(dev, PACKAGE)
    h.open_path(dev, ["AndroidQA", "Amaze"])
    return h.has(dev, "report-final.txt") and not h.has(dev, "report+final.txt"), {"texts": h.texts(dev)[:60]}

def _keep(dev, p):
    _rename(dev, p, "notes.txt", "notes2.txt")
    names = h.list_ext(dev, ROOT)
    return "notes2.txt" in names and "notes.txt" not in names, {"names": names}


def target(dev, params):
    return h.run(_target, dev, _p(params), TIER)


def held_out(dev, params):
    return h.run(_held, dev, _p(params), TIER)


def preserve(dev, params):
    return h.run(_keep, dev, _p(params), "A" if DB else "B")


CHECKS = {"target": target, "held_out": [held_out], "preservation": [preserve]}
