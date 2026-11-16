"""Deterministic checks for minus-0009. passed=True means intended behaviour (bug absent).
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
PARAMS_DEFAULT = {'nav': {'key_1': [{'text': '1'}], 'key_2': [{'text': '2'}], 'comment_tag': [{'text': 'Add comment'}, {'text': 'Comment'}, {'text': 'Category'}, {'desc': 'Edit category'}], 'comment_field': [{'text': 'Add comment'}, {'text': 'Comment'}, {'text': ''}], 'comment_check': [{'desc': 'Done'}, {'desc': 'Apply'}, {'desc': 'Confirm'}], 'save_expense': [{'desc': 'Save'}, {'desc': 'Add'}, {'text': 'Save'}, {'desc': 'Apply'}], 'dismiss_tutorial': [{'text': 'Skip'}, {'text': 'Got it'}, {'text': 'OK'}], 'analytics': [{'desc': 'Analytics'}, {'text': 'Analytics'}], 'income_toggle': [{'desc': 'Income'}, {'text': '+'}], 'key_3': [{'text': '3'}], 'key_0': [{'text': '0'}], 'history': [{'text': 'History'}, {'desc': 'History'}], 'groceries': [{'text': 'Groceries'}], 'rent': [{'text': 'Rent'}], 'category_row': [{'text': 'Category'}, {'text': 'Food'}], 'category_transport': [{'text': 'Transport'}], 'category_food': [{'text': 'Food'}], 'save': [{'text': 'Save'}, {'desc': 'Save'}, {'text': 'Done'}], 'settings': [{'text': 'Settings'}, {'desc': 'Settings'}], 'currency': [{'text': 'Currency'}, {'text': 'USD'}], 'currency_eur': [{'text': 'EUR'}, {'text': 'Euro'}], 'currency_usd': [{'text': 'USD'}, {'text': 'US Dollar'}], 'split': [{'text': 'Budget split'}, {'text': 'Daily amount'}, {'text': 'Split'}, {'text': 'Split mode'}], 'split_equal': [{'text': 'Split equally'}, {'text': 'Equal'}, {'text': 'Even'}, {'text': 'FIXED'}, {'text': 'Fixed'}], 'split_dynamic': [{'text': 'Rebalanced daily'}, {'text': 'Dynamic'}, {'text': 'DYNAMIC'}], 'period': [{'text': 'Period'}], 'period_weekly': [{'text': 'Weekly'}, {'text': 'This week'}], 'period_monthly': [{'text': 'Monthly'}, {'text': 'This month'}], 'budget_pill': [{'text': 'Today'}, {'text': 'This week'}, {'text': 'This biweekly'}, {'text': 'This month'}, {'text': 'Budget amount exceeded'}], 'edit_budget': [{'desc': 'Edit Budget'}, {'text': 'Edit Budget'}], 'next': [{'text': 'Next'}, {'desc': 'Next'}], 'apply': [{'text': 'Apply'}, {'desc': 'Apply'}], 'split_saved_later': [{'text': 'Saved for later'}], 'split_same': [{'text': 'Same every day'}], 'chip_weekly': [{'text': 'Weekly'}], 'chip_biweekly': [{'text': 'Biweekly'}], 'show_out_of_period': [{'text': 'Show subscriptions outside of the period'}], 'numpad_apply': [{'desc': 'Editor action'}], 'dialog_exit': [{'text': 'Tap to exit'}], 'recurrent_toggle': [{'desc': 'Recurrent Expense'}]}}


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


MONEY = re.compile(r"\d[\d,]*(?:\.\d{2})?")


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



PILL_LABELS = ["Today", "This week", "This biweekly", "This month"]


def _open_history(dev, p):
    """The history is a top sheet: drag the main screen down (swipe down on the budget pill)."""
    for _ in range(3):
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


def _edit_rent_frequency(dev, p, chip):
    """The case's UI path: swipe Rent left to edit, recurrent toggle, pick a frequency, Save, apply."""
    _open_history(dev, p)
    h.swipe(dev, "Rent", "left")  # head: left = edit, right = delete
    h.go(dev, p, "recurrent_toggle")
    h.go(dev, p, chip)
    h.go(dev, p, "save")
    h.key(dev, "ENTER")  # the numpad check shares its label with backspace; Enter = apply
    dev.wait_idle()
    if h.has(dev, "Tap to exit"):
        raise h.StepMissing("numpad_apply")


def _recurring(dev, p, chip=None):
    _start(dev, p)
    if chip:
        _edit_rent_frequency(dev, p, chip)
    if chip:
        dev.back()  # close the history sheet
        dev.wait_idle()
    h.go(dev, p, "analytics")
    dev.scroll_to({"text": "Recurring expenses"})
    return _money_after(dev, "Recurring expenses", 3)


def _target(dev, p):
    # Rent edited to weekly in the UI: yesterday's charge (20) + the next weekly charge inside the period (20) = 40
    val, seen = _recurring(dev, p, "chip_weekly")
    return val == "40.00", {"recurring": val, "seen": seen}


def _held(dev, p):
    val, seen = _recurring(dev, p, "chip_biweekly")
    return val == "40.00", {"recurring": val, "seen": seen}


def _keep(dev, p):
    # seeded monthly Rent: next charge is outside the period, so only yesterday's 20 counts;
    # the one-time card shows the 40 Groceries
    rec, seen = _recurring(dev, p)
    one, seen2 = _money_after(dev, "One-time expenses", 3)
    return rec == "20.00" and one == "40.00", {"recurring": rec, "one_time": one, "seen": seen, "seen2": seen2}


def target(dev, params):
    return h.run(_target, dev, _p(params), TIER)


def held_out(dev, params):
    return h.run(_held, dev, _p(params), TIER)


def preserve(dev, params):
    return h.run(_keep, dev, _p(params), "A" if DB else "B")


CHECKS = {"target": target, "held_out": [held_out], "preservation": [preserve]}
