"""Deterministic checks for ankidroid-0017. passed=True means intended behaviour (bug absent).
Each check re-seeds, drives the trigger through the Device API, then observes.
No wall-clock reads or sleeps; labels live in params["nav"] (bug.json)."""
from __future__ import annotations
from dataset_tools import check_helpers as h

APP = 'ankidroid'
PACKAGE = 'com.ichi2.anki'
SEED = 'decks_basic'
DB = 'collection.anki2'
TIER = 'B'
PARAMS_DEFAULT = {'nav': {'intro_skip': [{'text': 'Get started'}, {'text': 'Skip'}, {'text': 'OK'}], 'drawer': [{'desc': 'Open drawer'}, {'desc': 'Navigate up'}, {'desc': 'Open navigation drawer'}], 'browser': [{'text': 'Card browser'}, {'text': 'Browse'}, {'desc': 'Browse'}], 'deck_spinner': [{'id': 'com.ichi2.anki:id/toolbar_spinner'}, {'text': 'All decks'}], 'overflow': [{'desc': 'More options'}], 'edit_tags': [{'text': 'Edit tags'}, {'desc': 'Edit tags'}, {'text': 'Tags'}], 'ok': [{'text': 'OK'}, {'text': 'Save'}], 'settings': [{'text': 'Settings'}], 'search': [{'desc': 'Search'}, {'id': 'com.ichi2.anki:id/search'}], 'search_field': [{'id': 'com.ichi2.anki:id/search'}, {'text': 'Search…'}, {'text': 'Search'}], 'browse_cards': [{'text': 'Browse cards'}, {'text': 'Browse'}], 'deck_spanish': [{'text': 'Spanish'}], 'fab': [{'desc': 'Add'}, {'id': 'com.ichi2.anki:id/fab_main'}], 'filtered_deck': [{'text': 'Create filtered deck'}], 'filter_search': [{'text': 'Search'}, {'id': 'com.ichi2.anki:id/search'}], 'notes_mode': [{'text': 'Notes'}, {'text': 'Toggle cards/notes'}], 'expander': [{'desc': 'Expand'}, {'desc': 'Collapse'}], 'expand': [{'desc': 'Expand'}], 'collapse': [{'desc': 'Collapse'}], 'add_note': [{'desc': 'Add note'}, {'text': 'Add note'}, {'desc': 'Add'}, {'id': 'com.ichi2.anki:id/fab_expand_menu_button'}, {'id': 'com.ichi2.anki:id/fab_main'}], 'note_type': [{'id': 'com.ichi2.anki:id/note_type_spinner'}, {'text': 'Select note type'}, {'text': 'Note type'}, {'desc': 'Note type'}, {'text': 'Type'}], 'type_cloze': [{'text': 'Cloze'}], 'type_basic': [{'text': 'Basic'}], 'deck_french': [{'text': 'French'}], 'front_field': [{'text': 'Front'}, {'id': 'com.ichi2.anki:id/id_note_editText'}], 'text_field': [{'text': 'Text'}, {'id': 'com.ichi2.anki:id/id_note_editText'}], 'save_note': [{'desc': 'Save'}, {'text': 'Save'}, {'desc': 'Close'}, {'id': 'com.ichi2.anki:id/action_save'}], 'manage_note_types': [{'text': 'Manage note types'}, {'text': 'Note types'}], 'card_template': [{'text': 'Cards'}, {'text': 'Card'}, {'desc': 'Cards'}], 'add_template': [{'desc': 'Add'}, {'text': 'Add'}, {'id': 'com.ichi2.anki:id/action_add'}, {'text': 'Add template'}, {'text': 'Add card type'}], 'columns': [{'text': 'Manage columns'}, {'text': 'Columns'}, {'desc': 'Columns'}], 'due_column': [{'text': 'Due'}], 'export': [{'text': 'Export deck'}, {'text': 'Export'}, {'desc': 'Export'}], 'study': [{'text': 'Study'}, {'desc': 'Study'}, {'text': 'Review'}], 'edit_note': [{'text': 'Edit note'}, {'desc': 'Edit'}, {'id': 'com.ichi2.anki:id/action_edit_note'}], 'preview': [{'text': 'Preview'}, {'desc': 'Preview'}], 'fab_main': [{'id': 'com.ichi2.anki:id/fab_main'}], 'picker_fab': [{'id': 'com.ichi2.anki:id/fab_main'}], 'deck_row': [{'id': 'com.ichi2.anki:id/note_deck_name'}], 'cards_button': [{'id': 'com.ichi2.anki:id/CardEditorCardsButton'}, {'text': 'Cards: Cloze'}, {'text': 'Cards:'}], 'add_card_type': [{'text': 'Add card type'}], 'confirm_add': [{'text': 'Add'}], 'sync_ok': [{'text': 'OK'}]}}


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


def _open_template_editor(dev, p, cloze):
    """Add note screen -> (Cloze) -> 'Cards: ...' button -> card type editor."""
    _start(dev, p)
    _open_add(dev, p)
    if cloze:
        h.go(dev, p, "note_type")
        h.go(dev, p, "type_cloze")
    dev.scroll_to(p["nav"]["cards_button"][0])
    h.go(dev, p, "cards_button")
    if not h.has(dev, "Card types"):
        raise h.StepMissing("card_type_editor")


def _try_add(dev, p):
    """Try to add a card type from the editor menu; True when the menu offered it."""
    h.go(dev, p, "overflow")
    if not h.go_opt(dev, p, "add_card_type"):
        dev.back()
        dev.wait_idle()
        return False
    h.go_opt(dev, p, "confirm_add")
    h.go_opt(dev, p, "sync_ok")
    return True


def _extra_template(dev):
    j = " ".join(h.texts(dev))
    for ch in "\u2066\u2067\u2068\u2069":  # bidi isolates around the number in "Card 2"
        j = j.replace(ch, "")
    return "Card 2" in j or "Card 3" in j, j[:300]


def _target(dev, p):
    # Cloze has one card type. Head hides 'Add card type' for Cloze (and addCardTemplate returns early).
    # Buggy: the menu offers it and a second card type ("Card 2") appears. Passing = no second template.
    _open_template_editor(dev, p, cloze=True)
    offered = _try_add(dev, p)
    extra, j = _extra_template(dev)
    return not extra, {"menu_offered_add": offered, "extra_template": extra, "screen": j}


def _held(dev, p):
    # Variant: try twice and also confirm the stored Cloze template count is still one.
    _open_template_editor(dev, p, cloze=True)
    first = _try_add(dev, p)
    second = _try_add(dev, p)
    extra, j = _extra_template(dev)
    try:
        stored = len(h.sql(dev, DB, "SELECT ord FROM templates WHERE ntid = (SELECT id FROM notetypes WHERE name=?)", ("Cloze",)))
    except Exception as e:
        stored = "sql-error: %s" % type(e).__name__
    stored_ok = stored == 1 or isinstance(stored, str)
    return (not extra) and stored_ok, {"offered": [first, second], "extra_template": extra, "stored_templates": stored, "screen": j}


def _keep(dev, p):
    # A normal note type (Basic) still offers 'Add card type' in the card type editor.
    _open_template_editor(dev, p, cloze=False)
    h.go(dev, p, "overflow")
    offered = h.find(dev, p["nav"]["add_card_type"]) is not None
    return offered, {"menu_offered_add": offered}


def target(dev, params):
    return h.run(_target, dev, _p(params), TIER)


def held_out(dev, params):
    return h.run(_held, dev, _p(params), TIER)


def preserve(dev, params):
    return h.run(_keep, dev, _p(params), TIER)


CHECKS = {"target": target, "held_out": [held_out], "preservation": [preserve]}
