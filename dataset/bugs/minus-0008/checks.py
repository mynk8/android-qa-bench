"""Deterministic checks for minus-0008. passed=True means intended behaviour (bug absent).
Each check re-seeds, drives the trigger through the Device API, then observes.
No wall-clock reads or sleeps; labels live in params["nav"] (bug.json)."""
from __future__ import annotations
import re
from dataset_tools import check_helpers as h

APP = 'minus'
PACKAGE = 'com.serranoie.app.minus'
SEED = 'budget_basic'
DB = 'minus_budget.db'
TIER = 'A'
PARAMS_DEFAULT = {'nav': {'key_1': [{'text': '1'}], 'key_2': [{'text': '2'}], 'comment_tag': [{'text': 'Add comment'}, {'text': 'Comment'}, {'text': 'Category'}, {'desc': 'Edit category'}], 'comment_field': [{'text': 'Add comment'}, {'text': 'Comment'}, {'text': ''}], 'comment_check': [{'desc': 'Done'}, {'desc': 'Apply'}, {'desc': 'Confirm'}], 'save_expense': [{'desc': 'Save'}, {'desc': 'Add'}, {'text': 'Save'}, {'desc': 'Apply'}], 'dismiss_tutorial': [{'text': 'Skip'}, {'text': 'Got it'}, {'text': 'OK'}], 'analytics': [{'desc': 'Analytics'}, {'text': 'Analytics'}], 'income_toggle': [{'desc': 'Income'}, {'text': '+'}], 'key_3': [{'text': '3'}], 'key_0': [{'text': '0'}], 'history': [{'text': 'History'}, {'desc': 'History'}], 'groceries': [{'text': 'Groceries'}], 'rent': [{'text': 'Rent'}], 'category_row': [{'text': 'Category'}, {'text': 'Food'}], 'category_transport': [{'text': 'Transport'}], 'category_food': [{'text': 'Food'}], 'save': [{'text': 'Save'}, {'desc': 'Save'}, {'text': 'Done'}], 'settings': [{'text': 'Settings'}, {'desc': 'Settings'}], 'currency': [{'text': 'Currency'}, {'text': 'USD'}], 'currency_eur': [{'text': 'EUR'}, {'text': 'Euro'}], 'currency_usd': [{'text': 'USD'}, {'text': 'US Dollar'}], 'split': [{'text': 'Budget split'}, {'text': 'Daily amount'}, {'text': 'Split'}, {'text': 'Split mode'}], 'split_equal': [{'text': 'Split equally'}, {'text': 'Equal'}, {'text': 'Even'}, {'text': 'FIXED'}, {'text': 'Fixed'}], 'split_dynamic': [{'text': 'Rebalanced daily'}, {'text': 'Dynamic'}, {'text': 'DYNAMIC'}], 'period': [{'text': 'Period'}], 'period_weekly': [{'text': 'Weekly'}, {'text': 'This week'}], 'period_monthly': [{'text': 'Monthly'}, {'text': 'This month'}], 'budget_pill': [{'text': 'Today'}, {'text': 'This week'}, {'text': 'This biweekly'}, {'text': 'This month'}, {'text': 'Budget amount exceeded'}], 'edit_budget': [{'desc': 'Edit Budget'}, {'text': 'Edit Budget'}], 'next': [{'text': 'Next'}, {'desc': 'Next'}], 'apply': [{'text': 'Apply'}, {'desc': 'Apply'}], 'split_saved_later': [{'text': 'Saved for later'}], 'split_same': [{'text': 'Same every day'}], 'chip_weekly': [{'text': 'Weekly'}], 'chip_biweekly': [{'text': 'Biweekly'}], 'show_out_of_period': [{'text': 'Show subscriptions outside of the period'}], 'numpad_apply': [{'desc': 'Editor action'}], 'dialog_exit': [{'text': 'Tap to exit'}]}}


def _p(params):
    p = dict(PARAMS_DEFAULT)
    p.update(params or {})
    return p


def _clear_shade(dev):
    """The Android 'Certificate authority installed' notice can pull the shade down: close it."""
    for _ in range(2):
        if h.has(dev, "Certificate authority installed") or h.has(dev, "Clear all"):
            dev.back()
            dev.wait_idle()


def _start(dev, p):
    h.fresh(dev, APP, SEED)
    _clear_shade(dev)
    h.go_opt(dev, p, "dismiss_tutorial")


def _sql_relaunch(dev, p, stmts):
    """Edit the seeded data while the app is stopped, then start it again."""
    dev.force_stop(PACKAGE)
    dev.write_seed_sql(DB, stmts)
    dev.launch(PACKAGE)
    dev.wait_idle()
    _clear_shade(dev)
    h.go_opt(dev, p, "dismiss_tutorial")


PILL_LABELS = ["Today", "This week", "This biweekly", "This month"]


def _open_history(dev, p):
    """The history is a top sheet: drag the main screen down (swipe down on the budget pill)."""
    for _ in range(3):
        _clear_shade(dev)
        if h.has(dev, "Groceries"):
            return
        for lab in PILL_LABELS:
            if h.find(dev, [{"text": lab}]) is not None:
                h.swipe(dev, lab, "down")
                break
        else:
            raise h.StepMissing("history_drag_anchor:" + "|".join(h.texts(dev)[:14]))
    if not h.has(dev, "Groceries"):
        raise h.StepMissing("history_open")



def _edit_groceries_to_transport(dev, p):
    _start(dev, p)
    _open_history(dev, p)
    h.swipe(dev, "Groceries", "left")  # head: left = edit, right = delete
    h.go(dev, p, "category_transport")
    h.key(dev, "ENTER")  # the check button shares its label with backspace; Enter = apply
    dev.wait_idle()
    if h.has(dev, "Tap to exit"):
        # the edit screen is still open: the tap did not hit the check button
        raise h.StepMissing("numpad_apply")
    return None


def _row(dev, tid):
    # DB reads restart the app on Limrun: only after the last UI action.
    # The edited expense is the one worth 40 (Groceries, or the comment the edit left on it).
    return h.sql_until(dev, DB, "SELECT t.comment AS comment, t.amount AS amount, c.name AS category FROM transactions t "
                                "LEFT JOIN category c ON c.id=t.categoryId WHERE CAST(t.amount AS REAL)=40", (),
                       lambda r: bool(r) and r[0]["category"] == "Transport")


def _target(dev, p):
    # head: the saved tag Transport re-resolves the category of the edited expense
    tid = _edit_groceries_to_transport(dev, p)
    rows = _row(dev, tid)
    return bool(rows) and rows[0]["category"] == "Transport", {"rows": rows}


def _held(dev, p):
    # same edit, then read the category on the Analytics "Maximum spent" card after a restart
    _edit_groceries_to_transport(dev, p)
    h.relaunch(dev, PACKAGE)
    h.go_opt(dev, p, "dismiss_tutorial")
    h.go(dev, p, "analytics")
    dev.scroll_to({"text": "Maximum spent"})
    ts = h.texts(dev)
    idx = [i for i, t in enumerate(ts) if "maximum spent" in t.casefold()]
    if not idx:
        raise h.StepMissing("maximum_spent_card")
    i = idx[0]
    near = ts[max(0, i - 5):i + 6]
    ok = any("transport" in t.casefold() for t in near)
    return ok, {"near_max_card": near}


def _keep(dev, p):
    # the untouched recurring expense stays in its category
    _start(dev, p)
    rows = h.sql(dev, DB, "SELECT t.comment AS comment, c.name AS category FROM transactions t "
                          "JOIN category c ON c.id=t.categoryId WHERE t.comment='Rent'")
    return bool(rows) and rows[0]["category"] == "Food", {"rows": rows}


def target(dev, params):
    return h.run(_target, dev, _p(params), TIER)


def held_out(dev, params):
    return h.run(_held, dev, _p(params), TIER)


def preserve(dev, params):
    return h.run(_keep, dev, _p(params), "A" if DB else "B")


CHECKS = {"target": target, "held_out": [held_out], "preservation": [preserve]}
