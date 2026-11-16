"""Deterministic checks for ankidroid-0008. passed=True means intended behaviour (bug absent).
Each check re-seeds, drives the trigger through the Device API, then observes.
No wall-clock reads or sleeps; labels live in params["nav"] (bug.json)."""
from __future__ import annotations
from dataset_tools import check_helpers as h

APP = 'ankidroid'
PACKAGE = 'com.ichi2.anki'
SEED = 'decks_basic'
DB = 'collection.anki2'
TIER = 'B'
PARAMS_DEFAULT = {'nav': {'intro_skip': [{'text': 'Get started'}, {'text': 'Skip'}, {'text': 'OK'}], 'drawer': [{'desc': 'Open drawer'}, {'desc': 'Navigate up'}, {'desc': 'Open navigation drawer'}], 'browser': [{'text': 'Card browser'}, {'text': 'Browse'}, {'desc': 'Browse'}], 'deck_spinner': [{'id': 'com.ichi2.anki:id/toolbar_spinner'}, {'text': 'All decks'}], 'overflow': [{'desc': 'More options'}], 'edit_tags': [{'text': 'Edit tags'}, {'desc': 'Edit tags'}, {'text': 'Tags'}], 'ok': [{'text': 'OK'}, {'text': 'Save'}], 'settings': [{'text': 'Settings'}], 'search': [{'desc': 'Search'}, {'id': 'com.ichi2.anki:id/search'}], 'search_field': [{'id': 'com.ichi2.anki:id/search'}, {'text': 'Search…'}, {'text': 'Search'}], 'browse_cards': [{'text': 'Browse cards'}, {'text': 'Browse'}], 'deck_spanish': [{'text': 'Spanish'}], 'fab': [{'desc': 'Add'}, {'id': 'com.ichi2.anki:id/fab_main'}], 'filtered_deck': [{'text': 'Create filtered deck'}], 'filter_search': [{'text': 'Search'}, {'id': 'com.ichi2.anki:id/search'}], 'notes_mode': [{'text': 'Notes'}, {'text': 'Toggle cards/notes'}], 'expander': [{'desc': 'Expand'}, {'desc': 'Collapse'}], 'expand': [{'desc': 'Expand'}], 'collapse': [{'desc': 'Collapse'}], 'manage_note_types': [{'text': 'Manage note types'}], 'note_type': [{'text': 'Select note type'}, {'text': 'Note type'}, {'desc': 'Note type'}, {'id': 'com.ichi2.anki:id/note_type_spinner'}], 'add_note': [{'desc': 'Add note'}, {'text': 'Add note'}, {'desc': 'Add'}, {'id': 'com.ichi2.anki:id/fab_expand_menu_button'}, {'id': 'com.ichi2.anki:id/fab_main'}], 'add_template': [{'desc': 'Add'}, {'text': 'Add'}, {'id': 'com.ichi2.anki:id/action_add'}], 'export': [{'text': 'Export deck'}, {'text': 'Export'}, {'desc': 'Export'}], 'study': [{'text': 'Study'}, {'desc': 'Study'}], 'open_options': [{'text': 'Options'}], 'save_dialog': [{'text': 'Save'}], 'change_order': [{'text': 'Change display order'}]}}


def _p(params):
    p = dict(PARAMS_DEFAULT)
    p.update(params or {})
    return p


def _start(dev, p):
    h.fresh(dev, APP, SEED)
    h.go_opt(dev, p, "intro_skip")

import re


def _cfg(notes_backwards, cards_backwards):
    ins = "INSERT OR REPLACE INTO config (KEY, usn, mtime_secs, val) VALUES ('%s', 0, 0, CAST('%s' AS BLOB))"
    return [
        ins % ("noteSortType", '"noteFld"'),
        ins % ("browserNoteSortBackwards", "true" if notes_backwards else "false"),
        ins % ("sortBackwards", "true" if cards_backwards else "false"),
    ]


def _start_sorted(dev, p, notes_backwards, cards_backwards):
    h.fresh(dev, APP, SEED)
    dev.force_stop(PACKAGE)
    dev.write_seed_sql(DB, _cfg(notes_backwards, cards_backwards))
    h.relaunch(dev, PACKAGE)
    h.go_opt(dev, p, "intro_skip")


def _open_sheet(dev, p, notes_mode):
    h.go(dev, p, "drawer")
    h.go(dev, p, "browser")
    if notes_mode:
        h.go(dev, p, "overflow")
        h.go(dev, p, "open_options")
        h.go(dev, p, "notes_mode")
        h.go(dev, p, "save_dialog")
    h.go(dev, p, "overflow")
    h.go(dev, p, "change_order")


def _directions(dev):
    """Sort-direction subtitles shown in the 'Choose display order' sheet (only the selected column has one)."""
    ts = [re.sub("[\u2010-\u2015\u2212]", "-", t).strip().casefold() for t in h.texts(dev)]
    return "a-z" in ts, "z-a" in ts, ts[:40]


def _target(dev, p):
    # Notes mode has its own saved order (noteFld, backwards); cards mode is ascending.
    # Buggy: SortType.build reads the cards keys in notes mode, so the sheet shows ascending (A-Z).
    _start_sorted(dev, p, notes_backwards=True, cards_backwards=False)
    _open_sheet(dev, p, notes_mode=True)
    az, za, ts = _directions(dev)
    return za and not az, {"a-z": az, "z-a": za, "texts": ts}


def _held(dev, p):
    # Mirror image: notes ascending, cards descending. Buggy build shows the cards order (Z-A) in notes mode.
    _start_sorted(dev, p, notes_backwards=False, cards_backwards=True)
    _open_sheet(dev, p, notes_mode=True)
    az, za, ts = _directions(dev)
    return az and not za, {"a-z": az, "z-a": za, "texts": ts}


def _keep(dev, p):
    # Cards mode still shows the cards order in both builds.
    _start_sorted(dev, p, notes_backwards=False, cards_backwards=True)
    _open_sheet(dev, p, notes_mode=False)
    az, za, ts = _directions(dev)
    return za and not az, {"a-z": az, "z-a": za, "texts": ts}


def target(dev, params):
    return h.run(_target, dev, _p(params), TIER)


def held_out(dev, params):
    return h.run(_held, dev, _p(params), TIER)


def preserve(dev, params):
    return h.run(_keep, dev, _p(params), TIER)


CHECKS = {"target": target, "held_out": [held_out], "preservation": [preserve]}
