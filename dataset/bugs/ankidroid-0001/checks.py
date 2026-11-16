"""Deterministic checks for ankidroid-0001. passed=True means intended behaviour (bug absent).
Each check re-seeds, drives the trigger through the Device API, then observes.
No wall-clock reads or sleeps; labels live in params["nav"] (bug.json)."""
from __future__ import annotations
from dataset_tools import check_helpers as h

APP = 'ankidroid'
PACKAGE = 'com.ichi2.anki'
SEED = 'decks_basic'
DB = 'collection.anki2'
TIER = 'A'
PARAMS_DEFAULT = {'nav': {'intro_skip': [{'text': 'Get started'}, {'text': 'Skip'}, {'text': 'OK'}], 'drawer': [{'desc': 'Open drawer'}, {'desc': 'Navigate up'}, {'desc': 'Open navigation drawer'}], 'browser': [{'text': 'Card browser'}, {'text': 'Browse'}, {'desc': 'Browse'}], 'deck_spinner': [{'id': 'com.ichi2.anki:id/toolbar_spinner'}, {'text': 'All decks'}], 'overflow': [{'desc': 'More options'}], 'edit_tags': [{'text': 'Edit tags'}, {'desc': 'Edit tags'}, {'text': 'Tags'}], 'ok': [{'text': 'OK'}, {'text': 'Save'}], 'settings': [{'text': 'Settings'}], 'search': [{'desc': 'Search'}, {'id': 'com.ichi2.anki:id/search'}], 'search_field': [{'id': 'com.ichi2.anki:id/search'}, {'text': 'Search…'}, {'text': 'Search'}], 'browse_cards': [{'text': 'Browse cards'}, {'text': 'Browse'}], 'deck_spanish': [{'text': 'Spanish'}], 'fab': [{'desc': 'Add'}, {'id': 'com.ichi2.anki:id/fab_main'}], 'filtered_deck': [{'text': 'Create filtered deck'}], 'filter_search': [{'text': 'Search'}, {'id': 'com.ichi2.anki:id/search'}], 'notes_mode': [{'text': 'Notes'}, {'text': 'Toggle cards/notes'}], 'expander': [{'desc': 'Expand'}, {'desc': 'Collapse'}], 'expand': [{'desc': 'Expand'}], 'collapse': [{'desc': 'Collapse'}], 'manage_note_types': [{'text': 'Manage note types'}], 'note_type': [{'text': 'Select note type'}, {'text': 'Note type'}, {'desc': 'Note type'}, {'id': 'com.ichi2.anki:id/note_type_spinner'}], 'add_note': [{'desc': 'Add note'}, {'text': 'Add note'}, {'desc': 'Add'}, {'id': 'com.ichi2.anki:id/fab_expand_menu_button'}, {'id': 'com.ichi2.anki:id/fab_main'}], 'add_template': [{'desc': 'Add'}, {'text': 'Add'}, {'id': 'com.ichi2.anki:id/action_add'}], 'export': [{'text': 'Export deck'}, {'text': 'Export'}, {'desc': 'Export'}], 'study': [{'text': 'Study'}, {'desc': 'Study'}]}}


def _p(params):
    p = dict(PARAMS_DEFAULT)
    p.update(params or {})
    return p

def _start(dev, p):
    h.fresh(dev, APP, SEED)
    h.go_opt(dev, p, "intro_skip")

def _verb_notes(dev):
    rows = h.sql(dev, DB, "SELECT flds, tags FROM notes")
    return sorted(str(r["flds"]).split("\x1f")[0] for r in rows if "verb" in str(r.get("tags") or "").split())

def _tag_dialog(dev, p, fronts):
    _start(dev, p)
    h.go(dev, p, "drawer")
    h.go(dev, p, "browser")
    if not h.has(dev, fronts[0]):
        h.go_opt(dev, p, "deck_spinner")
        h.go_opt(dev, p, "deck_spanish")
    h.long_press(dev, fronts[0])
    for f in fronts[1:]:
        h.tap_text(dev, f)
    if not h.go_opt(dev, p, "edit_tags"):
        h.go(dev, p, "overflow"); h.go(dev, p, "edit_tags")
    h.go(dev, p, "ok")

def _target(dev, p):
    _tag_dialog(dev, p, ["comer", "mesa"])
    v = _verb_notes(dev)
    return v == ["comer"], {"verb_notes": v}

def _held(dev, p):
    _tag_dialog(dev, p, ["comer", "mesa", "hola"])
    h.relaunch(dev, PACKAGE)
    v = _verb_notes(dev)
    return v == ["comer"], {"verb_notes": v}

def _keep(dev, p):
    _tag_dialog(dev, p, ["comer"])
    v = _verb_notes(dev)
    return v == ["comer"], {"verb_notes": v}


def target(dev, params):
    return h.run(_target, dev, _p(params), TIER)


def held_out(dev, params):
    return h.run(_held, dev, _p(params), TIER)


def preserve(dev, params):
    return h.run(_keep, dev, _p(params), "A" if DB else "B")


CHECKS = {"target": target, "held_out": [held_out], "preservation": [preserve]}
