"""Deterministic checks for markor-0002. passed=True means intended behaviour (bug absent).
Each check re-seeds, drives the trigger through the Device API, then observes.
No wall-clock reads or sleeps; labels live in params["nav"] (bug.json)."""
from __future__ import annotations
from dataset_tools import check_helpers as h

APP = 'markor'
PACKAGE = 'net.gsantner.markor'
SEED = 'notebook_basic'
DB = ''
TIER = 'B'
PARAMS_DEFAULT = {'nav': {'files_tab': [{'text': 'Files'}, {'desc': 'Files'}], 'sort': [{'desc': 'Sort by'}, {'text': 'Sort by'}, {'desc': 'Sort'}], 'overflow': [{'desc': 'More options'}], 'folder_first': [{'text': 'Folder first'}, {'text': 'Folders first'}], 'editor': [{'id': 'net.gsantner.markor:id/document__fragment__edit__highlighting_editor'}], 'edit_mode': [{'desc': 'Edit'}, {'id': 'net.gsantner.markor:id/fab_edit'}], 'duplicate_line': [{'text': 'Duplicate lines'}, {'desc': 'Duplicate lines'}, {'desc': 'Duplicate line(s)'}, {'desc': 'Duplicate line'}], 'search_replace': [{'text': 'Search / Replace'}, {'text': 'Search and replace'}, {'text': 'Search & replace'}, {'desc': 'Search and replace'}], 'find_field': [{'text': 'Search'}, {'text': 'Find'}, {'id': 'net.gsantner.markor:id/search_input'}], 'replace_field': [{'text': 'Replace'}, {'text': 'Replace with'}, {'id': 'net.gsantner.markor:id/replace_input'}], 'regex_toggle': [{'text': 'Regex'}, {'text': 'Use regex'}, {'desc': 'Regex'}], 'replace_one': [{'text': 'Replace'}, {'text': 'REPLACE'}], 'replace_all': [{'text': 'Replace all'}, {'text': 'REPLACE ALL'}], 'view_mode': [{'desc': 'View'}, {'id': 'net.gsantner.markor:id/action_preview'}], 'file_info': [{'text': 'Info'}, {'text': 'More info'}, {'text': 'File info'}], 'favourite_box': [{'text': 'Favourite'}, {'text': 'Favorite'}], 'favourites_view': [{'text': 'Favourites'}, {'text': 'Favorites'}], 'ok': [{'text': 'OK'}], 'cursor_line_start': [{'desc': 'Line Start (Home)'}, {'desc': 'Home'}, {'desc': 'Move to line start'}], 'enter_key': [{'desc': 'New line'}, {'desc': 'Enter'}], 'new_file': [{'text': 'Create a new file or folder'}, {'desc': 'New file'}, {'text': 'New file'}, {'desc': 'Create'}, {'id': 'fab'}], 'filename_field': [{'text': 'Name'}, {'text': 'File name'}, {'id': 'document__dialog_new_filename'}], 'type_markdown': [{'text': 'Markdown'}, {'text': 'Plain text'}], 'create': [{'text': 'OK'}, {'text': 'Create'}, {'text': 'Ok'}], 'undo': [{'desc': 'Undo'}, {'text': 'Undo'}], 'redo': [{'desc': 'Redo'}, {'text': 'Redo'}], 'folders_first': [{'text': 'Folder first'}, {'text': 'Folders first'}], 'use_regex': [{'text': 'Regex'}, {'text': 'Regex search'}]}}


def _p(params):
    p = dict(PARAMS_DEFAULT)
    p.update(params or {})
    return p


def _home(dev, p):
    h.fresh(dev, APP, SEED)
    (h.find(dev, [{"text": "Shopping.md"}]) is None and h.go_opt(dev, p, "files_tab"))
    (h.find(dev, [{"text": "Shopping.md"}]) is None and h.open_path(dev, ["markor"]))

def _create(dev, p, name):
    _home(dev, p)
    if not h.go_opt(dev, p, "new_file"):
        h.go(dev, p, "overflow")
        h.go(dev, p, "new_file")
    h.type_into(dev, p, "filename_field", name)
    if not h.has_exact_ci(dev, "OK"):
        dev.back(); dev.wait_idle()   # close the keyboard that hides the dialog buttons
    h.go(dev, p, "create")
    h.go_opt(dev, p, "edit_mode")

def _type(dev, p, text):
    if h.find(dev, p["nav"].get("editor") or []) is not None:
        h.type_into(dev, p, "editor", text)
        return
    sel = h.find(dev, [{"id": "document__fragment_content"}]) or {"desc": "Edit"}
    dev.input_text(sel, text)
    dev.wait_idle()

def _ed(dev):
    """Text of the editor only (the keyboard suggestion strip also shows typed words)."""
    return " ".join(str(n.get("text") or "") for n in h.nodes(dev)
                    if str(n.get("id") or "").endswith("highlighting_editor"))

def _target(dev, p):
    _create(dev, p, "UndoMe.md")
    _type(dev, p, "hello")
    h.go(dev, p, "undo")
    after_undo = "hello" in _ed(dev)
    h.go(dev, p, "redo")
    after_redo = "hello" in _ed(dev)
    return (not after_undo) and after_redo, {"after_undo_has_hello": after_undo, "after_redo_has_hello": after_redo, "texts": h.texts(dev)[:40]}

def _held(dev, p):
    _create(dev, p, "UndoTwo.md")
    _type(dev, p, "world")
    h.go(dev, p, "undo")
    gone = "world" not in _ed(dev)
    h.go(dev, p, "redo")
    back = "world" in _ed(dev)
    return gone and back, {"after_undo_gone": gone, "after_redo_back": back}

def _keep(dev, p):
    _home(dev, p)
    h.tap_text(dev, "Shopping.md")
    h.go_opt(dev, p, "edit_mode")
    return h.has(dev, "milk"), {"texts": h.texts(dev)[:40]}


def target(dev, params):
    return h.run(_target, dev, _p(params), TIER)


def held_out(dev, params):
    return h.run(_held, dev, _p(params), TIER)


def preserve(dev, params):
    return h.run(_keep, dev, _p(params), "A" if DB else "B")


CHECKS = {"target": target, "held_out": [held_out], "preservation": [preserve]}
