"""Deterministic checks for markor-0010. passed=True means intended behaviour (bug absent).
Each check re-seeds, drives the trigger through the Device API, then observes.
No wall-clock reads or sleeps; labels live in params["nav"] (bug.json)."""
from __future__ import annotations
from dataset_tools import check_helpers as h

APP = 'markor'
PACKAGE = 'net.gsantner.markor'
SEED = 'notebook_basic'
DB = ''
TIER = 'A'
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

def _replace(dev, p, doc, mode):
    _open_doc(dev, p, doc)
    # the toolbar Search icon opens the inline find bar; "Toggle Find/Replace" shows the replace row
    dev.tap({"id": "net.gsantner.markor:id/action_search"}); dev.wait_idle()
    if h.find(dev, p["nav"]["replace_field"]) is None:
        dev.tap({"desc": "Toggle Find/Replace"}); dev.wait_idle()
    h.type_into(dev, p, "find_field", r"(\w+)@home")
    h.go(dev, p, "regex_toggle")
    h.type_into(dev, p, "replace_field", "$1")
    h.go(dev, p, mode)
    dev.back(); dev.wait_idle()
    _leave(dev)
    return h.read_ext(dev, ROOT + "/" + doc)

def _target(dev, p):
    c = _replace(dev, p, "Regex.md", "replace_one")
    return c is not None and c.strip() == "cat", {"content": c}

def _held(dev, p):
    c = _replace(dev, p, "Regex2.md", "replace_one")
    # replace-once acts on one match (which one depends on the cursor); the group must be substituted
    return c is not None and c.strip() in ("cat dog@home", "cat@home dog"), {"content": c}

def _keep(dev, p):
    c = _replace(dev, p, "Regex.md", "replace_all")
    return c is not None and c.strip() == "cat", {"content": c}


def target(dev, params):
    return h.run(_target, dev, _p(params), TIER)


def held_out(dev, params):
    return h.run(_held, dev, _p(params), TIER)


def preserve(dev, params):
    return h.run(_keep, dev, _p(params), "A" if DB else "B")


CHECKS = {"target": target, "held_out": [held_out], "preservation": [preserve]}
