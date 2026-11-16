"""Deterministic checks for minus-0001. passed=True means intended behaviour (bug absent).
Each check re-seeds, drives the trigger through the Device API, then observes.
No wall-clock reads or sleeps; labels live in params["nav"] (bug.json)."""
from __future__ import annotations
import re
from dataset_tools import check_helpers as h

APP = 'minus'
PACKAGE = 'com.serranoie.app.minus'
SEED = 'budget_basic'
DB = 'minus_budget.db'
TIER = 'B'
PARAMS_DEFAULT = {'nav': {'key_1': [{'text': '1'}], 'key_2': [{'text': '2'}], 'comment_tag': [{'text': 'Add comment'}, {'text': 'Comment'}, {'text': 'Category'}, {'desc': 'Edit category'}], 'comment_field': [{'text': 'Add comment'}, {'text': 'Comment'}, {'text': ''}], 'comment_check': [{'desc': 'Done'}, {'desc': 'Apply'}, {'desc': 'Confirm'}], 'save_expense': [{'desc': 'Save'}, {'desc': 'Add'}, {'text': 'Save'}, {'desc': 'Apply'}], 'dismiss_tutorial': [{'text': 'Skip'}, {'text': 'Got it'}, {'text': 'OK'}], 'analytics': [{'desc': 'Analytics'}, {'text': 'Analytics'}], 'income_toggle': [{'desc': 'Income'}, {'text': '+'}], 'key_3': [{'text': '3'}], 'key_0': [{'text': '0'}], 'history': [{'text': 'History'}, {'desc': 'History'}], 'groceries': [{'text': 'Groceries'}], 'rent': [{'text': 'Rent'}], 'category_row': [{'text': 'Category'}, {'text': 'Food'}], 'category_transport': [{'text': 'Transport'}], 'category_food': [{'text': 'Food'}], 'save': [{'text': 'Save'}, {'desc': 'Save'}, {'text': 'Done'}], 'settings': [{'text': 'Settings'}, {'desc': 'Settings'}], 'currency': [{'text': 'Currency'}, {'text': 'USD'}], 'currency_eur': [{'text': 'EUR'}, {'text': 'Euro'}], 'currency_usd': [{'text': 'USD'}, {'text': 'US Dollar'}], 'split': [{'text': 'Budget split'}, {'text': 'Daily amount'}, {'text': 'Split'}, {'text': 'Split mode'}], 'split_equal': [{'text': 'Split equally'}, {'text': 'Equal'}, {'text': 'Even'}, {'text': 'FIXED'}, {'text': 'Fixed'}], 'split_dynamic': [{'text': 'Rebalanced daily'}, {'text': 'Dynamic'}, {'text': 'DYNAMIC'}], 'period': [{'text': 'Period'}], 'period_weekly': [{'text': 'Weekly'}, {'text': 'This week'}], 'period_monthly': [{'text': 'Monthly'}, {'text': 'This month'}], 'budget_pill': [{'text': 'Today'}, {'text': 'This week'}, {'text': 'This biweekly'}, {'text': 'This month'}, {'text': 'Budget amount exceeded'}], 'edit_budget': [{'desc': 'Edit Budget'}, {'text': 'Edit Budget'}], 'next': [{'text': 'Next'}, {'desc': 'Next'}], 'apply': [{'text': 'Apply'}, {'desc': 'Apply'}], 'split_saved_later': [{'text': 'Saved for later'}], 'split_same': [{'text': 'Same every day'}], 'chip_weekly': [{'text': 'Weekly'}], 'chip_biweekly': [{'text': 'Biweekly'}], 'show_out_of_period': [{'text': 'Show subscriptions outside of the period'}], 'numpad_apply': [{'desc': 'Editor action'}], 'dialog_exit': [{'text': 'Tap to exit'}]}}


def _p(params):
    p = dict(PARAMS_DEFAULT)
    p.update(params or {})
    return p


def _start(dev, p):
    h.fresh(dev, APP, SEED)
    h.go_opt(dev, p, "dismiss_tutorial")


def _sql_relaunch(dev, p, stmts):
    """Edit the seeded data while the app is stopped, then start it again."""
    dev.force_stop(PACKAGE)
    dev.write_seed_sql(DB, stmts)
    dev.launch(PACKAGE)
    dev.wait_idle()
    h.go_opt(dev, p, "dismiss_tutorial")


PILL_LABELS = ["Today", "This week", "This biweekly", "This month"]


def _open_history(dev, p):
    """The history is a top sheet: drag the main screen down (swipe down on the budget pill)."""
    for _ in range(2):
        if h.has(dev, "Groceries"):
            return
        for lab in PILL_LABELS:
            if h.find(dev, [{"text": lab}]) is not None:
                h.swipe(dev, lab, "down")
                break
        else:
            raise h.StepMissing("history_drag_anchor")
    if not h.has(dev, "Groceries"):
        raise h.StepMissing("history_open")


# Rent is moved so its next charge is ~22 days away (after the period end) and it has no charge inside
# the period: it then appears only in the out-of-period section. Renamed so the row text is unique.
MOVE = ("UPDATE transactions SET comment='Gym', "
        "date=((CAST(strftime('%s','now','start of day','+22 days','-1 month','+12 hours') AS INTEGER))*1000), "
        "createdAt=((CAST(strftime('%s','now','start of day','+22 days','-1 month','+12 hours') AS INTEGER))*1000) "
        "WHERE comment='Rent';")


def _history_with_section(dev, p):
    _start(dev, p)
    _sql_relaunch(dev, p, [MOVE])
    _open_history(dev, p)
    dev.scroll_to({"text": "Show subscriptions outside of the period"})
    h.go(dev, p, "show_out_of_period")
    if not h.has(dev, "Gym"):
        raise h.StepMissing("out_of_period_row")


def _target(dev, p):
    # head: swiping the out-of-period recurring row right opens the delete dialog
    _history_with_section(dev, p)
    h.swipe(dev, "Gym", "right")  # head: swipe right = delete, left = edit
    ts = h.texts(dev)
    return h.has(dev, "Delete recurrent expense"), {"texts": ts[:40]}


def _held(dev, p):
    # head: swiping the same row left opens the edit screen
    _history_with_section(dev, p)
    h.swipe(dev, "Gym", "left")
    ts = h.texts(dev)
    return h.has(dev, "Tap to exit"), {"texts": ts[:40]}


def _keep(dev, p):
    # a one-off expense row keeps its swipe-to-delete (with undo) in the same list
    _start(dev, p)
    _open_history(dev, p)
    h.swipe(dev, "Groceries", "right")
    ts = h.texts(dev)
    blob = " ".join(ts).casefold()
    return ("deleted" in blob) or ("undo" in blob), {"texts": ts[:40]}


def target(dev, params):
    return h.run(_target, dev, _p(params), TIER)


def held_out(dev, params):
    return h.run(_held, dev, _p(params), TIER)


def preserve(dev, params):
    return h.run(_keep, dev, _p(params), "A" if DB else "B")


CHECKS = {"target": target, "held_out": [held_out], "preservation": [preserve]}
