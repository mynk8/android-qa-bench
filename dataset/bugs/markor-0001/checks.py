"""Deterministic checks for markor-0001. passed=True means intended behaviour (bug absent).
Each check re-seeds, drives the trigger through the Device API, then observes.
No wall-clock reads or sleeps; labels live in params["nav"] (bug.json)."""
from __future__ import annotations
from dataset_tools import check_helpers as h

APP = 'markor'
PACKAGE = 'net.gsantner.markor'
SEED = 'notebook_basic'
DB = ''
TIER = 'B'
PARAMS_DEFAULT = {'nav': {'files_tab': [{'text': 'Files'}, {'desc': 'Files'}], 'sort': [{'desc': 'Sort by'}, {'text': 'Sort by'}, {'desc': 'Sort'}], 'overflow': [{'desc': 'More options'}], 'folder_first': [{'text': 'Folder first'}, {'text': 'Folders first'}], 'editor': [{'id': 'net.gsantner.markor:id/document__fragment__edit__highlighting_editor'}], 'edit_mode': [{'desc': 'Edit'}, {'id': 'net.gsantner.markor:id/fab_edit'}], 'duplicate_line': [{'text': 'Duplicate lines'}, {'desc': 'Duplicate lines'}, {'desc': 'Duplicate line(s)'}, {'desc': 'Duplicate line'}], 'search_replace': [{'text': 'Search / Replace'}, {'text': 'Search and replace'}, {'text': 'Search & replace'}, {'desc': 'Search and replace'}], 'find_field': [{'text': 'Search'}, {'text': 'Find'}, {'id': 'net.gsantner.markor:id/search_input'}], 'replace_field': [{'text': 'Replace'}, {'text': 'Replace with'}, {'id': 'net.gsantner.markor:id/replace_input'}], 'regex_toggle': [{'text': 'Regex'}, {'text': 'Use regex'}, {'desc': 'Regex'}], 'replace_one': [{'text': 'Replace'}, {'text': 'REPLACE'}], 'replace_all': [{'text': 'Replace all'}, {'text': 'REPLACE ALL'}], 'view_mode': [{'desc': 'View'}, {'id': 'net.gsantner.markor:id/action_preview'}], 'file_info': [{'text': 'Info'}, {'text': 'More info'}, {'text': 'File info'}], 'favourite_box': [{'text': 'Favourite'}, {'text': 'Favorite'}], 'favourites_view': [{'text': 'Favourites'}, {'text': 'Favorites'}], 'ok': [{'text': 'OK'}], 'cursor_line_start': [{'desc': 'Line Start (Home)'}, {'desc': 'Home'}, {'desc': 'Move to line start'}], 'enter_key': [{'desc': 'New line'}, {'desc': 'Enter'}], 'folders_first': [{'text': 'Folder first'}, {'text': 'Folders first'}], 'use_regex': [{'text': 'Regex'}, {'text': 'Regex search'}], 'new_file': [{'text': 'Create a new file or folder'}, {'desc': 'New file'}, {'text': 'New file'}, {'desc': 'Create'}, {'id': 'fab'}]}}


def _p(params):
    p = dict(PARAMS_DEFAULT)
    p.update(params or {})
    return p

ROOT = "Documents/markor"
def _home(dev, p):
    h.fresh(dev, APP, SEED)
    (h.find(dev, [{"text": "Shopping.md"}]) is None and h.go_opt(dev, p, "files_tab"))
    (h.find(dev, [{"text": "Shopping.md"}]) is None and h.open_path(dev, ["markor"]))

def _open_doc(dev, p, name):
    _home(dev, p)
    h.tap_text(dev, name)
    h.go_opt(dev, p, "edit_mode")
    h.go_opt(dev, p, "editor")

def _leave(dev):
    dev.back(); dev.wait_idle()   # Markor saves the document when leaving the editor
    dev.back(); dev.wait_idle()

def _toggle(dev, p):
    if not h.go_opt(dev, p, "sort"):
        h.go(dev, p, "overflow"); h.go(dev, p, "sort")
    h.go(dev, p, "folder_first")
    # the sort dialog applies its choices only on OK
    if not h.go_opt(dev, p, "ok") and h.find(dev, p["nav"]["folder_first"]) is not None:
        dev.back(); dev.wait_idle()

def _order(dev):
    ts = h.texts(dev)
    z, t = h.index_of(ts, "Zeta"), h.index_of(ts, "todo.txt")
    return z, t, ts

def _target(dev, p):
    _home(dev, p); _toggle(dev, p)
    z, t, ts = _order(dev)
    return z >= 0 and t >= 0 and z > t, {"zeta": z, "todo": t, "texts": ts[:40]}

def _held(dev, p):
    _home(dev, p); _toggle(dev, p)
    h.relaunch(dev, PACKAGE)
    (h.find(dev, [{"text": "Shopping.md"}]) is None and h.open_path(dev, ["markor"]))
    z, t, ts = _order(dev)
    return z >= 0 and t >= 0 and z > t, {"zeta": z, "todo": t, "texts": ts[:40]}

def _keep(dev, p):
    _home(dev, p)
    ts = h.texts(dev)
    z, s = h.index_of(ts, "Zeta"), h.index_of(ts, "Shopping.md")
    return z >= 0 and s >= 0 and z < s, {"zeta": z, "shopping": s, "texts": ts[:40]}


def target(dev, params):
    return h.run(_target, dev, _p(params), TIER)


def held_out(dev, params):
    return h.run(_held, dev, _p(params), TIER)


def preserve(dev, params):
    return h.run(_keep, dev, _p(params), "A" if DB else "B")


CHECKS = {"target": target, "held_out": [held_out], "preservation": [preserve]}
