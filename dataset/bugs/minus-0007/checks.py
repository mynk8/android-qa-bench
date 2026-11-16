"""Deterministic checks for minus-0007. passed=True means intended behaviour (bug absent).
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
PARAMS_DEFAULT = {'nav': {'key_1': [{'text': '1'}], 'key_2': [{'text': '2'}], 'comment_tag': [{'text': 'Add comment'}, {'text': 'Comment'}, {'text': 'Category'}, {'desc': 'Edit category'}], 'comment_field': [{'text': 'Add comment'}, {'text': 'Comment'}, {'text': ''}], 'comment_check': [{'desc': 'Done'}, {'desc': 'Apply'}, {'desc': 'Confirm'}], 'save_expense': [{'desc': 'Save'}, {'desc': 'Add'}, {'text': 'Save'}, {'desc': 'Apply'}], 'dismiss_tutorial': [{'text': 'Skip'}, {'text': 'Got it'}, {'text': 'OK'}], 'analytics': [{'desc': 'Analytics'}, {'text': 'Analytics'}], 'income_toggle': [{'desc': 'Income'}, {'text': '+'}], 'key_3': [{'text': '3'}], 'key_0': [{'text': '0'}], 'history': [{'text': 'History'}, {'desc': 'History'}], 'groceries': [{'text': 'Groceries'}], 'rent': [{'text': 'Rent'}], 'category_row': [{'text': 'Category'}, {'text': 'Food'}], 'category_transport': [{'text': 'Transport'}], 'category_food': [{'text': 'Food'}], 'save': [{'text': 'Save'}, {'desc': 'Save'}, {'text': 'Done'}], 'settings': [{'text': 'Settings'}, {'desc': 'Settings'}], 'currency': [{'text': 'Currency'}, {'text': 'USD'}], 'currency_eur': [{'text': 'EUR'}, {'text': 'Euro'}], 'currency_usd': [{'text': 'USD'}, {'text': 'US Dollar'}], 'split': [{'text': 'Budget split'}, {'text': 'Daily amount'}, {'text': 'Split'}, {'text': 'Split mode'}, {'text': 'Split equally'}, {'desc': 'Split equally'}], 'split_equal': [{'text': 'Split equally'}, {'text': 'Equal'}, {'text': 'Even'}, {'text': 'FIXED'}, {'text': 'Fixed'}], 'split_dynamic': [{'text': 'Rebalanced daily'}, {'text': 'Dynamic'}, {'text': 'DYNAMIC'}], 'period': [{'text': 'Period'}], 'period_weekly': [{'text': 'Weekly'}, {'text': 'This week'}], 'period_monthly': [{'text': 'Monthly'}, {'text': 'This month'}], 'budget_pill': [{'text': 'Today'}, {'text': 'This week'}, {'text': 'This biweekly'}, {'text': 'This month'}, {'text': 'Budget amount exceeded'}], 'edit_budget': [{'desc': 'Edit Budget'}, {'text': 'Edit Budget'}], 'next': [{'text': 'Next'}, {'desc': 'Next'}], 'apply': [{'text': 'Apply'}, {'desc': 'Apply'}], 'split_saved_later': [{'text': 'Saved for later'}], 'split_same': [{'text': 'Same every day'}], 'chip_weekly': [{'text': 'Weekly'}], 'chip_biweekly': [{'text': 'Biweekly'}], 'show_out_of_period': [{'text': 'Show subscriptions outside of the period'}], 'numpad_apply': [{'desc': 'Editor action'}], 'dialog_exit': [{'text': 'Tap to exit'}]}}


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


MONEY = re.compile(r"\d[\d,]*(?:\.\d+)?")


def _money_after(dev, label, span=3):
    """First money token in the texts at/after the one containing `label` (case-insensitive)."""
    ts = h.texts(dev)
    key = label.casefold()
    for i, t in enumerate(ts):
        if key in t.casefold():
            blob = " ".join(ts[i:i + span]).replace(label, "")
            m = MONEY.search(blob)
            return (("%.2f" % float(m.group(0).replace(",", ""))) if m else None), ts[i:i + span]
    return None, ts[:20]


def _amount(dev):
    return _money_after(dev, "Calculated amount", 3)


def _open_sheet(dev, p):
    h.go(dev, p, "budget_pill")
    if not h.has(dev, "Calculated amount"):
        raise h.StepMissing("budget_sheet")


def _pick_restart_reopen(dev, p, chip):
    """Choose a split view in the budget sheet, close the app completely, reopen the sheet."""
    _start(dev, p)
    _open_sheet(dev, p)
    first, _ = _amount(dev)
    h.go(dev, p, chip)
    chosen, _ = _amount(dev)
    h.relaunch(dev, PACKAGE)
    h.go_opt(dev, p, "dismiss_tutorial")
    _open_sheet(dev, p)
    again, seen = _amount(dev)
    ok = first is not None and chosen is not None and chosen != first and again == chosen
    return ok, {"daily": first, "after_pick": chosen, "after_restart": again, "seen": seen}


def _target(dev, p):
    # head: the Weekly split view is still selected after the app is closed and opened again
    return _pick_restart_reopen(dev, p, "chip_weekly")


def _held(dev, p):
    return _pick_restart_reopen(dev, p, "chip_biweekly")


def _keep(dev, p):
    # inside the open sheet, picking Weekly recalculates the amount
    _start(dev, p)
    _open_sheet(dev, p)
    first, _ = _amount(dev)
    has_total = h.has(dev, "Total budget")
    h.go(dev, p, "chip_weekly")
    chosen, _ = _amount(dev)
    return has_total and first is not None and chosen is not None and chosen != first, {"daily": first, "weekly": chosen}


def target(dev, params):
    return h.run(_target, dev, _p(params), TIER)


def held_out(dev, params):
    return h.run(_held, dev, _p(params), TIER)


def preserve(dev, params):
    return h.run(_keep, dev, _p(params), "A" if DB else "B")


CHECKS = {"target": target, "held_out": [held_out], "preservation": [preserve]}
