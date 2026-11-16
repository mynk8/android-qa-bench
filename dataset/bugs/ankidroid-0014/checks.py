"""Deterministic checks for ankidroid-0014. passed=True means intended behaviour (bug absent).
Each check re-seeds, drives the trigger through the Device API, then observes.
No wall-clock reads or sleeps; labels live in params["nav"] (bug.json)."""
from __future__ import annotations
from dataset_tools import check_helpers as h

APP = 'ankidroid'
PACKAGE = 'com.ichi2.anki'
SEED = 'decks_basic'
DB = 'collection.anki2'
TIER = 'B'
PARAMS_DEFAULT = {'nav': {'intro_skip': [{'text': 'Get started'}, {'text': 'Skip'}, {'text': 'OK'}], 'drawer': [{'desc': 'Open drawer'}, {'desc': 'Navigate up'}, {'desc': 'Open navigation drawer'}], 'browser': [{'text': 'Card browser'}, {'text': 'Browse'}, {'desc': 'Browse'}], 'deck_spinner': [{'id': 'com.ichi2.anki:id/toolbar_spinner'}, {'text': 'All decks'}], 'overflow': [{'desc': 'More options'}], 'edit_tags': [{'text': 'Edit tags'}, {'desc': 'Edit tags'}, {'text': 'Tags'}], 'ok': [{'text': 'OK'}, {'text': 'Save'}], 'settings': [{'text': 'Settings'}], 'search': [{'desc': 'Search'}, {'id': 'com.ichi2.anki:id/search'}], 'search_field': [{'id': 'com.ichi2.anki:id/search'}, {'text': 'Search…'}, {'text': 'Search'}], 'browse_cards': [{'text': 'Browse cards'}, {'text': 'Browse'}], 'deck_spanish': [{'text': 'Spanish'}], 'fab': [{'desc': 'Add'}, {'id': 'com.ichi2.anki:id/fab_main'}], 'filtered_deck': [{'text': 'Create filtered deck'}], 'filter_search': [{'text': 'Search'}, {'id': 'com.ichi2.anki:id/search'}], 'notes_mode': [{'text': 'Notes'}, {'text': 'Toggle cards/notes'}], 'expander': [{'desc': 'Expand'}, {'desc': 'Collapse'}], 'expand': [{'desc': 'Expand'}], 'collapse': [{'desc': 'Collapse'}], 'manage_note_types': [{'text': 'Manage note types'}], 'note_type': [{'text': 'Select note type'}, {'text': 'Note type'}, {'desc': 'Note type'}, {'id': 'com.ichi2.anki:id/note_type_spinner'}], 'add_note': [{'desc': 'Add note'}, {'text': 'Add note'}, {'desc': 'Add'}, {'id': 'com.ichi2.anki:id/fab_expand_menu_button'}, {'id': 'com.ichi2.anki:id/fab_main'}], 'add_template': [{'desc': 'Add'}, {'text': 'Add'}, {'id': 'com.ichi2.anki:id/action_add'}], 'export': [{'text': 'Export deck'}, {'text': 'Export'}, {'desc': 'Export'}], 'study': [{'text': 'Study'}, {'desc': 'Study'}], 'subdeck_menu': [{'text': 'Create subdeck'}], 'subdeck_name': [{'id': 'com.ichi2.anki:id/dialog_text_input'}], 'create_confirm': [{'text': 'Create'}]}}


def _p(params):
    p = dict(PARAMS_DEFAULT)
    p.update(params or {})
    return p


def _start(dev, p):
    h.fresh(dev, APP, SEED)
    h.go_opt(dev, p, "intro_skip")


def _make_subdeck(dev, p, parent, name):
    h.long_press(dev, parent)
    h.go(dev, p, "subdeck_menu")
    h.type_into(dev, p, "subdeck_name", name)
    h.go(dev, p, "create_confirm")


def _state(dev, p):
    """Which expander is on screen: 'Expand' (collapsed deck), 'Collapse' (expanded deck) or None."""
    if h.find(dev, p["nav"]["expand"]) is not None:
        return "Expand"
    if h.find(dev, p["nav"]["collapse"]) is not None:
        return "Collapse"
    return None


def _toggle(dev, p, taps):
    before = _state(dev, p)
    after = before
    for _ in range(taps):
        if after is None:
            break
        h.go(dev, p, "expand" if after == "Expand" else "collapse")
        after = _state(dev, p)
    return before, after


def _target(dev, p):
    # Spanish gets a subdeck, then its expander is tapped once: the arrow must flip.
    # Buggy: the parent row is not rebound when only the collapsed flag changes, so the arrow stays stale.
    _start(dev, p)
    _make_subdeck(dev, p, "Spanish", "Verbs")
    before, after = _toggle(dev, p, 1)
    return before is not None and after is not None and after != before, {"before": before, "after": after, "texts": h.texts(dev)[:30]}


def _held(dev, p):
    # Variant: French gets the subdeck and the expander is tapped three times: the arrow must end flipped.
    _start(dev, p)
    _make_subdeck(dev, p, "French", "Slang")
    before, after = _toggle(dev, p, 3)
    return before is not None and after is not None and after != before, {"before": before, "after": after, "texts": h.texts(dev)[:30]}


def _keep(dev, p):
    # Creating a subdeck works and the parent shows an expander (both builds).
    _start(dev, p)
    _make_subdeck(dev, p, "Spanish", "Verbs")
    state = _state(dev, p)
    return state is not None and h.has(dev, "Spanish") and h.has(dev, "French"), {"state": state, "texts": h.texts(dev)[:30]}


def target(dev, params):
    return h.run(_target, dev, _p(params), TIER)


def held_out(dev, params):
    return h.run(_held, dev, _p(params), TIER)


def preserve(dev, params):
    return h.run(_keep, dev, _p(params), TIER)


CHECKS = {"target": target, "held_out": [held_out], "preservation": [preserve]}
