"""Deterministic checks for ankidroid-0007. passed=True means intended behaviour (bug absent).
Each check re-seeds, drives the trigger through the Device API, then observes.
No wall-clock reads or sleeps; labels live in params["nav"] (bug.json)."""
from __future__ import annotations
from dataset_tools import check_helpers as h

APP = 'ankidroid'
PACKAGE = 'com.ichi2.anki'
SEED = 'decks_basic'
DB = 'collection.anki2'
TIER = 'B'
PARAMS_DEFAULT = {'nav': {'intro_skip': [{'text': 'Get started'}, {'text': 'Skip'}, {'text': 'OK'}], 'drawer': [{'desc': 'Open drawer'}, {'desc': 'Navigate up'}, {'desc': 'Open navigation drawer'}], 'browser': [{'text': 'Card browser'}, {'text': 'Browse'}, {'desc': 'Browse'}], 'deck_spinner': [{'id': 'com.ichi2.anki:id/toolbar_spinner'}, {'text': 'All decks'}], 'overflow': [{'desc': 'More options'}], 'edit_tags': [{'text': 'Edit tags'}, {'desc': 'Edit tags'}, {'text': 'Tags'}], 'ok': [{'text': 'OK'}, {'text': 'Save'}], 'settings': [{'text': 'Settings'}], 'search': [{'desc': 'Search'}, {'id': 'com.ichi2.anki:id/search'}], 'search_field': [{'id': 'com.ichi2.anki:id/search'}, {'text': 'Search…'}, {'text': 'Search'}], 'browse_cards': [{'text': 'Browse cards'}, {'text': 'Browse'}], 'deck_spanish': [{'text': 'Spanish'}], 'fab': [{'desc': 'Add'}, {'id': 'com.ichi2.anki:id/fab_main'}], 'filtered_deck': [{'text': 'Create filtered deck'}], 'filter_search': [{'text': 'Search'}, {'id': 'com.ichi2.anki:id/search'}], 'notes_mode': [{'text': 'Notes'}, {'text': 'Toggle cards/notes'}], 'expander': [{'desc': 'Expand'}, {'desc': 'Collapse'}], 'expand': [{'desc': 'Expand'}], 'collapse': [{'desc': 'Collapse'}], 'add_note': [{'desc': 'Add note'}, {'text': 'Add note'}, {'desc': 'Add'}, {'id': 'com.ichi2.anki:id/fab_expand_menu_button'}, {'id': 'com.ichi2.anki:id/fab_main'}], 'note_type': [{'id': 'com.ichi2.anki:id/note_type_spinner'}, {'text': 'Select note type'}, {'text': 'Note type'}, {'desc': 'Note type'}, {'text': 'Type'}], 'type_cloze': [{'text': 'Cloze'}], 'type_basic': [{'text': 'Basic'}], 'deck_french': [{'text': 'French'}], 'front_field': [{'desc': 'Front'}, {'text': 'Front'}, {'id': 'com.ichi2.anki:id/id_note_editText'}], 'text_field': [{'desc': 'Text'}, {'text': 'Text'}, {'id': 'com.ichi2.anki:id/id_note_editText'}], 'save_note': [{'desc': 'Save'}, {'text': 'Save'}, {'desc': 'Close'}, {'id': 'com.ichi2.anki:id/action_save'}], 'manage_note_types': [{'text': 'Manage note types'}, {'text': 'Note types'}], 'card_template': [{'text': 'Cards'}, {'text': 'Card'}, {'desc': 'Cards'}], 'add_template': [{'desc': 'Add'}, {'text': 'Add'}, {'id': 'com.ichi2.anki:id/action_add'}, {'text': 'Add template'}, {'text': 'Add card type'}], 'columns': [{'text': 'Manage columns'}, {'text': 'Columns'}, {'desc': 'Columns'}], 'due_column': [{'text': 'Due'}], 'export': [{'text': 'Export deck'}, {'text': 'Export'}, {'desc': 'Export'}], 'study': [{'text': 'Study'}, {'desc': 'Study'}, {'text': 'Review'}], 'edit_note': [{'text': 'Edit note'}, {'desc': 'Edit'}, {'id': 'com.ichi2.anki:id/action_edit_note'}], 'preview': [{'desc': 'Preview'}, {'text': 'Preview'}], 'fab_main': [{'id': 'com.ichi2.anki:id/fab_main'}], 'picker_fab': [{'id': 'com.ichi2.anki:id/fab_main'}], 'deck_row': [{'id': 'com.ichi2.anki:id/note_deck_name'}]}}


def _p(params):
    p = dict(PARAMS_DEFAULT)
    p.update(params or {})
    return p


def _start(dev, p):
    h.fresh(dev, APP, SEED)
    h.go_opt(dev, p, "intro_skip")

def _open_add(dev, p):
    """Deck list -> Add note screen (first FAB tap opens the menu, the next one adds a note)."""
    for _ in range(4):
        if h.find(dev, p["nav"]["deck_row"]) is not None:
            return
        h.go(dev, p, "fab_main")
    raise h.StepMissing("add_note_screen")


def _to_picker(dev, p):
    """Leave the editor (keyboard first, then the screen) until the deck list FAB is visible."""
    for _ in range(4):
        if h.find(dev, p["nav"]["picker_fab"]) is not None:
            return
        dev.back()
        dev.wait_idle()
    raise h.StepMissing("deck_list")


def _deck_name(dev):
    for n in h.nodes(dev):
        if (n.get("id") or "").endswith("note_deck_name"):
            return n.get("text") or ""
    return None


def _start_by_note_type(dev, p):
    """Seed, then set Settings > General > 'Deck for new cards' to 'Decide by note type' through the screen
    (the same step the case gives). The seed already records French as the last deck used for Basic."""
    h.fresh(dev, APP, SEED)
    h.go_opt(dev, p, "intro_skip")
    h.go(dev, p, "drawer")
    h.go(dev, p, "settings")
    h.tap_text(dev, "General")
    h.tap_text(dev, "Deck for new cards")
    h.tap_text(dev, "Decide by note type")
    _to_picker(dev, p)


def _choose_deck(dev, p, deck_step):
    h.go(dev, p, "deck_row")
    h.go(dev, p, deck_step)


def _target(dev, p):
    # Add a Basic note to Spanish, leave, open Add note again: the deck must be remembered (Spanish).
    # Buggy: Add note preselects the globally selected deck (Default) instead of the remembered one.
    _start_by_note_type(dev, p)
    _open_add(dev, p)
    _choose_deck(dev, p, "deck_spanish")
    chosen = _deck_name(dev)
    h.type_into(dev, p, "front_field", "merci")
    h.go(dev, p, "save_note")
    _to_picker(dev, p)
    _open_add(dev, p)
    name = _deck_name(dev)
    return bool(name) and "Spanish" in name, {"chosen": chosen, "reopened": name}


def _held(dev, p):
    # Variant: no note is added; the French deck recorded for Basic in the seed must be preselected.
    _start_by_note_type(dev, p)
    _open_add(dev, p)
    name = _deck_name(dev)
    return bool(name) and "French" in name, {"deck": name}


def _keep(dev, p):
    # Choosing a deck in the editor still works (same on both builds).
    _start_by_note_type(dev, p)
    _open_add(dev, p)
    _choose_deck(dev, p, "deck_spanish")
    name = _deck_name(dev)
    return bool(name) and "Spanish" in name, {"deck": name}


def target(dev, params):
    return h.run(_target, dev, _p(params), TIER)


def held_out(dev, params):
    return h.run(_held, dev, _p(params), TIER)


def preserve(dev, params):
    return h.run(_keep, dev, _p(params), TIER)


CHECKS = {"target": target, "held_out": [held_out], "preservation": [preserve]}
