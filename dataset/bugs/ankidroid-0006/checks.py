"""Deterministic checks for ankidroid-0006. passed=True means intended behaviour (bug absent).
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


def _joined(dev):
    return " ".join(h.texts(dev))


def _preview_cloze(dev, p, text):
    _start(dev, p)
    _open_add(dev, p)
    h.go(dev, p, "note_type")
    h.go(dev, p, "type_cloze")
    h.type_into(dev, p, "text_field", text)
    h.go(dev, p, "preview")


def _tab_shows(dev, tab, want, unwanted):
    """Open previewer tab `tab`; the card shown must contain the cloze hint, `want` and not `unwanted`."""
    # tab labels carry bidi isolates around the number ("Card \u20683\u2069")
    def _plain(t):
        return "".join(c for c in (t or "") if c not in "\u2066\u2067\u2068\u2069")
    sel = None
    for _ in range(6):
        for n in h.nodes(dev):
            if _plain(n.get("text")) == tab:
                sel = {"text": n["text"]}
                break
        if sel:
            break
        dev.wait_idle()
    if sel is None:
        raise h.StepMissing("text:" + tab)
    dev.tap(sel)
    dev.wait_idle()
    j = ""
    for _ in range(6):
        dev.wait_idle()
        j = _joined(dev)
        if "[...]" in j and want in j and unwanted not in j:
            return True, j
    return False, j


def _target(dev, p):
    # Clozes 1 and 3 (no 2): the previewer tab "Card 3" must show card c3 (alpha shown, gamma hidden).
    # Buggy: tab position 1 is mapped straight to ord 1 (a cloze that does not exist), so c3 is never shown.
    _preview_cloze(dev, p, "{{c1::alpha}} and {{c3::gamma}}")
    ok, j = _tab_shows(dev, "Card 3", "alpha", "gamma")
    return ok, {"screen": j[:300]}


def _held(dev, p):
    # Clozes 2 and 4: tab "Card 4" must show card c4 (beta shown, delta hidden).
    _preview_cloze(dev, p, "{{c2::beta}} and {{c4::delta}}")
    ok, j = _tab_shows(dev, "Card 4", "beta", "delta")
    return ok, {"screen": j[:300]}


def _keep(dev, p):
    # Non-cloze preview is unaffected: a Basic note previews its front text.
    _start(dev, p)
    _open_add(dev, p)
    h.type_into(dev, p, "front_field", "hello")
    h.go(dev, p, "preview")
    j = ""
    for _ in range(6):
        dev.wait_idle()
        j = _joined(dev)
        if "hello" in j:
            return True, {"screen": j[:300]}
    return False, {"screen": j[:300]}


def target(dev, params):
    return h.run(_target, dev, _p(params), TIER)


def held_out(dev, params):
    return h.run(_held, dev, _p(params), TIER)


def preserve(dev, params):
    return h.run(_keep, dev, _p(params), TIER)


CHECKS = {"target": target, "held_out": [held_out], "preservation": [preserve]}
