"""Deterministic checks for ankidroid-0027. passed=True means intended behaviour (bug absent).
Each check re-seeds, drives the trigger through the Device API, then observes.
No wall-clock reads or sleeps; labels live in params["nav"] (bug.json)."""
from __future__ import annotations
from dataset_tools import check_helpers as h

APP = 'ankidroid'
PACKAGE = 'com.ichi2.anki'
SEED = 'decks_basic'
DB = 'collection.anki2'
TIER = 'B'
PARAMS_DEFAULT = {'nav': {'intro_skip': [{'text': 'Get started'}, {'text': 'Skip'}, {'text': 'OK'}], 'drawer': [{'desc': 'Open drawer'}, {'desc': 'Navigate up'}, {'desc': 'Open navigation drawer'}], 'browser': [{'text': 'Card browser'}, {'text': 'Browse'}, {'desc': 'Browse'}], 'deck_spinner': [{'id': 'com.ichi2.anki:id/toolbar_spinner'}, {'text': 'All decks'}], 'overflow': [{'desc': 'More options'}], 'edit_tags': [{'text': 'Edit tags'}, {'desc': 'Edit tags'}, {'text': 'Tags'}], 'ok': [{'text': 'OK'}, {'text': 'Save'}], 'settings': [{'text': 'Settings'}], 'search': [{'desc': 'Search'}, {'id': 'com.ichi2.anki:id/search'}], 'search_field': [{'id': 'com.ichi2.anki:id/search'}, {'text': 'Search…'}, {'text': 'Search'}], 'browse_cards': [{'text': 'Browse cards'}, {'text': 'Browse'}], 'deck_spanish': [{'text': 'Spanish'}], 'fab': [{'desc': 'Add'}, {'id': 'com.ichi2.anki:id/fab_main'}], 'filtered_deck': [{'text': 'Create filtered deck'}], 'filter_search': [{'text': 'Search'}, {'id': 'com.ichi2.anki:id/search'}], 'notes_mode': [{'text': 'Notes'}, {'text': 'Toggle cards/notes'}], 'expander': [{'desc': 'Expand'}, {'desc': 'Collapse'}], 'expand': [{'desc': 'Expand'}], 'collapse': [{'desc': 'Collapse'}], 'add_note': [{'desc': 'Add note'}, {'text': 'Add note'}, {'desc': 'Add'}, {'id': 'com.ichi2.anki:id/fab_expand_menu_button'}, {'id': 'com.ichi2.anki:id/fab_main'}], 'note_type': [{'id': 'com.ichi2.anki:id/note_type_spinner'}, {'text': 'Select note type'}, {'text': 'Note type'}, {'desc': 'Note type'}, {'text': 'Type'}], 'type_cloze': [{'text': 'Cloze'}], 'type_basic': [{'text': 'Basic'}], 'deck_french': [{'text': 'French'}], 'front_field': [{'desc': 'Front'}, {'text': 'Front'}, {'id': 'com.ichi2.anki:id/id_note_editText'}], 'text_field': [{'desc': 'Text'}, {'text': 'Text'}, {'id': 'com.ichi2.anki:id/id_note_editText'}], 'save_note': [{'desc': 'Save'}, {'text': 'Save'}, {'desc': 'Close'}, {'id': 'com.ichi2.anki:id/action_save'}], 'manage_note_types': [{'text': 'Manage note types'}, {'text': 'Note types'}], 'card_template': [{'text': 'Cards'}, {'text': 'Card'}, {'desc': 'Cards'}], 'add_template': [{'desc': 'Add'}, {'text': 'Add'}, {'id': 'com.ichi2.anki:id/action_add'}, {'text': 'Add template'}, {'text': 'Add card type'}], 'columns': [{'text': 'Manage columns'}, {'text': 'Columns'}, {'desc': 'Columns'}], 'due_column': [{'text': 'Due'}], 'export': [{'text': 'Export deck'}, {'text': 'Export'}, {'desc': 'Export'}], 'study': [{'text': 'Study'}, {'desc': 'Study'}, {'text': 'Review'}], 'edit_note': [{'text': 'Edit note'}, {'desc': 'Edit'}, {'id': 'com.ichi2.anki:id/action_edit_note'}], 'preview': [{'desc': 'Preview'}, {'text': 'Preview'}], 'fab_main': [{'id': 'com.ichi2.anki:id/fab_main'}], 'picker_fab': [{'id': 'com.ichi2.anki:id/fab_main'}], 'deck_row': [{'id': 'com.ichi2.anki:id/note_deck_name'}], 'subdeck_menu': [{'text': 'Create subdeck'}], 'subdeck_name': [{'id': 'com.ichi2.anki:id/dialog_text_input'}], 'create_confirm': [{'text': 'Create'}], 'rename_menu': [{'text': 'Rename deck'}, {'text': 'Rename'}], 'rename_confirm': [{'text': 'Rename'}]}}

def _p(params):
    p = dict(PARAMS_DEFAULT)
    p.update(params or {})
    return p


def _start(dev, p):
    h.fresh(dev, APP, SEED)
    h.go_opt(dev, p, "intro_skip")


def _reach(dev, p, step):
    """Tap a labelled item, scrolling the list first when it is not on screen."""
    alts = p["nav"][step]
    if h.find(dev, alts) is None:
        for a in alts:
            if dev.scroll_to(a):
                break
    h.go(dev, p, step)


def _node_text(dev, id_suffix):
    for n in h.nodes(dev):
        if (n.get("id") or "").endswith(id_suffix):
            return n.get("text") or ""
    return None


def _exact(dev, s):
    return any(t.strip() == s for t in h.texts(dev))


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


def _browser_row(dev, p):
    """Open the card browser and long-press the first listed seeded note; returns its text."""
    h.go(dev, p, "drawer")
    h.go(dev, p, "browser")
    for word in ("comer", "bonjour", "mesa", "pain", "hola", "chat", "agua"):
        if h.find(dev, [{"text": word}]) is not None:
            h.long_press(dev, word)
            return word
    raise h.StepMissing("browser_row")


def _rename(dev, p, deck, new_name):
    _start(dev, p)
    h.long_press(dev, deck)
    h.go(dev, p, "rename_menu")
    h.type_into(dev, p, "subdeck_name", new_name)
    h.go_opt(dev, p, "rename_confirm")
    open_ = h.find(dev, p["nav"]["subdeck_name"]) is not None
    return open_, _exact(dev, new_name)


def _target(dev, p):
    # French -> FRENCH: the dialog must close and the list must show FRENCH.
    still_open, shown = _rename(dev, p, "French", "FRENCH")
    return (not still_open) and shown, {"dialog_open": still_open, "texts": h.texts(dev)[:30]}


def _held(dev, p):
    # Variant: Spanish -> spanish (lower case).
    still_open, shown = _rename(dev, p, "Spanish", "spanish")
    return (not still_open) and shown, {"dialog_open": still_open, "texts": h.texts(dev)[:30]}


def _keep(dev, p):
    # A genuinely new name renames the deck (both builds).
    still_open, shown = _rename(dev, p, "French", "Francais")
    return (not still_open) and shown, {"dialog_open": still_open, "texts": h.texts(dev)[:30]}


def target(dev, params):
    return h.run(_target, dev, _p(params), TIER)


def held_out(dev, params):
    return h.run(_held, dev, _p(params), TIER)


def preserve(dev, params):
    return h.run(_keep, dev, _p(params), TIER)


CHECKS = {"target": target, "held_out": [held_out], "preservation": [preserve]}
