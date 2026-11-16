"""Deterministic checks for minus-0010. passed=True means intended behaviour (bug absent).
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
PARAMS_DEFAULT = {'nav': {'key_1': [{'text': '1'}], 'key_2': [{'text': '2'}], 'comment_tag': [{'text': 'Add comment'}, {'text': 'Comment'}, {'text': 'Category'}, {'desc': 'Edit category'}], 'comment_field': [{'text': 'Add comment'}, {'text': 'Comment'}, {'text': ''}], 'comment_check': [{'desc': 'Done'}, {'desc': 'Apply'}, {'desc': 'Confirm'}], 'save_expense': [{'desc': 'Save'}, {'desc': 'Add'}, {'text': 'Save'}, {'desc': 'Apply'}], 'dismiss_tutorial': [{'text': 'Skip'}, {'text': 'Got it'}, {'text': 'OK'}], 'analytics': [{'desc': 'Analytics'}, {'text': 'Analytics'}], 'income_toggle': [{'desc': 'Income'}, {'text': '+'}], 'key_3': [{'text': '3'}], 'key_0': [{'text': '0'}], 'split': [{'text': 'Budget split'}, {'text': 'Daily amount'}, {'text': 'Split'}], 'split_equal': [{'text': 'Split equally'}, {'text': 'Equal'}], 'split_dynamic': [{'text': 'Rebalanced daily'}, {'text': 'Dynamic'}], 'currency': [{'text': 'Currency'}], 'currency_eur': [{'text': 'EUR'}], 'currency_usd': [{'text': 'USD'}], 'period': [{'text': 'Period'}], 'period_weekly': [{'text': 'Weekly'}, {'text': 'This week'}], 'period_monthly': [{'text': 'Monthly'}, {'text': 'This month'}], 'history': [{'text': 'History'}, {'desc': 'History'}], 'settings': [{'text': 'Settings'}, {'desc': 'Settings'}], 'budget_pill': [{'text': 'Today'}, {'text': 'This week'}, {'text': 'This biweekly'}, {'text': 'This month'}, {'text': 'Budget amount exceeded'}], 'edit_budget': [{'desc': 'Edit Budget'}, {'text': 'Edit Budget'}], 'next': [{'text': 'Next'}, {'desc': 'Next'}], 'apply': [{'text': 'Apply'}, {'desc': 'Apply'}], 'split_saved_later': [{'text': 'Saved for later'}], 'split_same': [{'text': 'Same every day'}], 'chip_weekly': [{'text': 'Weekly'}], 'chip_biweekly': [{'text': 'Biweekly'}], 'show_out_of_period': [{'text': 'Show subscriptions outside of the period'}], 'numpad_apply': [{'desc': 'Editor action'}], 'dialog_exit': [{'text': 'Tap to exit'}]}}


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


COUNT_RE = re.compile(r"\d+")


def _total_expenses(dev):
    ts = h.texts(dev)
    for i, t in enumerate(ts):
        if "total expenses" in t.casefold():
            head = t.casefold().split("total expenses")[0]
            m = COUNT_RE.search(head)
            if m is None and i > 0:
                m = COUNT_RE.search(ts[i - 1])
            return (int(m.group(0)) if m else None), ts[max(0, i - 2):i + 2]
    return None, ts[:20]


MONEY = re.compile(r"\d[\d,]*(?:\.\d+)?")


def _spent(dev):
    """The amount on the Spent card (exact label, not 'Maximum spent')."""
    ts = h.texts(dev)
    for i, t in enumerate(ts):
        if t.strip().casefold() == "spent":
            m = MONEY.search(" ".join(ts[max(0, i - 1):i]))  # the amount sits just above its label
            return ("%.2f" % float(m.group(0).replace(",", ""))) if m else None
    return None


def _analytics_count(dev, p, stmts=None):
    _start(dev, p)
    if stmts:
        _sql_relaunch(dev, p, stmts)
    h.go(dev, p, "analytics")
    dev.scroll_to({"text": "Total Expenses"})
    n, seen = _total_expenses(dev)
    spent = _spent(dev)          # the Spent card sits just below Total Expenses
    return n, seen, spent


# Rent's saved date is a month before the period: only the recurring charge that falls in the
# period (yesterday) counts at head; the raw row is outside the period.
RENT_LAST_MONTH = ("UPDATE transactions SET "
                   "date=((CAST(strftime('%s','now','start of day','-1 days','-1 month','+12 hours') AS INTEGER))*1000) "
                   "WHERE comment='Rent';")
# weekly Rent that started two weeks before yesterday (also outside the period)
RENT_WEEKLY_OLD = ("UPDATE transactions SET recurrentFrequency='WEEKLY', "
                   "date=((CAST(strftime('%s','now','start of day','-15 days','+12 hours') AS INTEGER))*1000) "
                   "WHERE comment='Rent';")


def _target(dev, p):
    # Groceries + the Rent charge of yesterday = 2 expenses (the raw Rent row is outside the period)
    n, seen, spent = _analytics_count(dev, p, [RENT_LAST_MONTH])
    return n == 2 and spent == "60.00", {"total_expenses": n, "spent": spent, "seen": seen}


def _held(dev, p):
    n, seen, spent = _analytics_count(dev, p, [RENT_WEEKLY_OLD])
    return n == 2 and spent == "60.00", {"total_expenses": n, "spent": spent, "seen": seen}


def _keep(dev, p):
    # seeded data: Rent row is inside the period, so both builds count 2
    n, seen, spent = _analytics_count(dev, p)
    return n == 2 and spent == "60.00", {"total_expenses": n, "spent": spent, "seen": seen}


def target(dev, params):
    return h.run(_target, dev, _p(params), TIER)


def held_out(dev, params):
    return h.run(_held, dev, _p(params), TIER)


def preserve(dev, params):
    return h.run(_keep, dev, _p(params), "A" if DB else "B")


CHECKS = {"target": target, "held_out": [held_out], "preservation": [preserve]}
