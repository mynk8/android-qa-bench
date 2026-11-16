"""Deterministic checks for minus-0014. passed=True means intended behaviour (bug absent).
Each check re-seeds, drives the trigger through the Device API, then observes.
No wall-clock reads or sleeps; labels live in params["nav"] (bug.json)."""
from __future__ import annotations
from dataset_tools import check_helpers as h

APP = 'minus'
PACKAGE = 'com.serranoie.app.minus'
SEED = 'budget_basic'
DB = 'minus_budget.db'
TIER = 'A'
PARAMS_DEFAULT = {'nav': {'key_1': [{'text': '1'}], 'key_2': [{'text': '2'}], 'comment_tag': [{'text': 'Add comment'}, {'text': 'Comment'}, {'text': 'Category'}, {'desc': 'Edit category'}], 'comment_field': [{'text': 'Add comment'}, {'text': 'Comment'}, {'text': ''}], 'comment_check': [{'desc': 'Done'}, {'desc': 'Apply'}, {'desc': 'Confirm'}], 'save_expense': [{'desc': 'Save'}, {'desc': 'Add'}, {'text': 'Save'}, {'desc': 'Apply'}], 'dismiss_tutorial': [{'text': 'Skip'}, {'text': 'Got it'}, {'text': 'OK'}], 'analytics': [{'desc': 'Analytics'}, {'text': 'Analytics'}], 'income_toggle': [{'desc': 'Income'}, {'text': '+'}], 'key_3': [{'text': '3'}], 'key_0': [{'text': '0'}], 'split': [{'text': 'Budget split'}, {'text': 'Daily amount'}, {'text': 'Split'}], 'split_equal': [{'text': 'Split equally'}, {'text': 'Equal'}], 'split_dynamic': [{'text': 'Rebalanced daily'}, {'text': 'Dynamic'}], 'currency': [{'text': 'Currency'}], 'currency_eur': [{'text': 'EUR'}], 'currency_usd': [{'text': 'USD'}], 'period': [{'text': 'Period'}], 'period_weekly': [{'text': 'Weekly'}, {'text': 'This week'}], 'period_monthly': [{'text': 'Monthly'}, {'text': 'This month'}], 'history': [{'text': 'History'}, {'desc': 'History'}], 'settings': [{'text': 'Settings'}, {'desc': 'Settings'}]}}


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

def _count_new(dev):
    rows = h.sql(dev, DB, "SELECT amount, comment FROM transactions WHERE comment LIKE '%Snacks%' OR CAST(amount AS REAL) = 12")
    return len(rows), rows

def _enter(dev, p):
    _start(dev, p)
    h.go(dev, p, "key_1"); h.go(dev, p, "key_2")
    h.go(dev, p, "comment_tag")
    h.type_into(dev, p, "comment_field", "Snacks")
    h.go(dev, p, "comment_check")

def _target(dev, p):
    _enter(dev, p)
    n, rows = _count_new(dev)
    return n == 0, {"rows": rows}

def _held(dev, p):
    _enter(dev, p)
    h.relaunch(dev, PACKAGE)
    n, rows = _count_new(dev)
    return n == 0, {"rows": rows}

def _keep(dev, p):
    _start(dev, p)
    h.go(dev, p, "key_1"); h.go(dev, p, "key_2")
    # the numpad keeps working: the amount reads $12, and its backspace key (the first
    # "Editor action" node) turns it into $1
    before = h.texts(dev)
    h.go(dev, p, "save_expense")
    after = h.texts(dev)
    ok = "$12" in before and "$1" in after and "$12" not in after
    return ok, {"before": before[:14], "after": after[:14]}


def target(dev, params):
    return h.run(_target, dev, _p(params), TIER)


def held_out(dev, params):
    return h.run(_held, dev, _p(params), TIER)


def preserve(dev, params):
    return h.run(_keep, dev, _p(params), "A" if DB else "B")


CHECKS = {"target": target, "held_out": [held_out], "preservation": [preserve]}
