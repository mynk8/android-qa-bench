"""Deterministic checks for featherline-0003. passed=True means intended behaviour (bug absent).
Each check re-seeds, drives the trigger through the Device API, then observes.
No wall-clock reads or sleeps; labels live in params["nav"] (bug.json)."""
from __future__ import annotations
from dataset_tools import check_helpers as h

APP = 'featherline'
PACKAGE = 'com.mkx.hrttracker'
SEED = 'plan_empty'
DB = ''
TIER = 'B'
PARAMS_DEFAULT = {'nav': {'onboarding_skip': [{'text': 'Skip'}, {'text': 'Get started'}, {'text': 'Continue'}], 'add_medication': [{'text': 'Add medicine'}, {'text': 'Add medication'}, {'desc': 'Add medication'}, {'text': '+ New medicine'}], 'new_medicine': [{'text': 'Add medicine'}, {'text': '+ New medicine'}], 'route_gel': [{'text': 'Gel'}], 'route_oral': [{'text': 'Oral'}], 'prep_tablet': [{'text': 'Tablet'}], 'name_field': [{'text': 'Name'}, {'text': 'Medicine name'}], 'strength_field': [{'text': 'Tablet strength (mg)'}, {'text': 'Tablet strength'}], 'per_dose_field': [{'text': 'Tablets per dose'}], 'save': [{'text': 'Save'}, {'desc': 'Save'}], 'calibration': [{'text': 'Calibration'}, {'desc': 'Calibration'}], 'e2_field': [{'text': 'E2'}], 'ime_next': [{'desc': 'Next'}], 'focused_field': [{'text': ''}], 'stock_field': [{'text': 'Stock'}, {'desc': 'Stock'}, {'text': 'On hand'}], 'add_stock': [{'text': 'Add'}, {'text': 'Add stock'}, {'desc': 'Add stock'}], 'log_dose': [{'text': 'Log now'}, {'text': 'Quick log'}, {'text': 'Logged'}, {'text': 'Log dose'}, {'text': 'Take'}, {'text': 'Mark taken'}, {'desc': 'Log'}], 'backfill': [{'text': 'Past schedule'}, {'text': 'Past due'}, {'text': 'Backfill'}, {'text': 'Log past dose'}, {'text': 'Retrospective'}, {'text': 'Past'}], 'date_row': [{'text': 'Date'}, {'desc': 'Date'}], 'medicine_list': [{'text': 'Medications'}, {'text': 'Plan'}, {'text': 'Catalogue'}], 'labs': [{'text': 'Labs'}, {'text': 'Test results'}, {'text': 'Add result'}, {'text': 'Blood tests'}, {'text': 'Results'}], 'add_result': [{'text': 'Add result'}, {'text': 'Add'}, {'desc': 'Add'}], 'result_name': [{'text': 'Name'}, {'text': 'Marker'}], 'result_value': [{'text': 'Value'}, {'text': 'Result'}], 'e2_marker': [{'text': 'E2'}, {'text': 'Estradiol'}], 'prep_patch': [{'text': 'Patch'}, {'text': 'Patch release rate'}], 'onb_start': [{'text': 'Get started'}], 'onb_agree': [{'text': 'I have read and agree'}], 'onb_skip': [{'text': 'Skip'}], 'onb_continue': [{'text': 'Continue'}], 'onb_open': [{'text': 'Open Featherline'}], 'tab_plan': [{'text': 'Plan'}, {'desc': 'Plan'}], 'tab_home': [{'text': 'Home'}, {'desc': 'Home'}], 'add_group': [{'text': 'Add'}], 'group_add_medication': [{'text': 'Add'}], 'add_medicine_btn': [{'text': 'Add medicine'}], 'cat_antiandrogen': [{'text': 'Antiandrogen'}], 'quick_log': [{'text': 'Quick log'}, {'desc': 'Quick log'}]}}


def _p(params):
    p = dict(PARAMS_DEFAULT)
    p.update(params or {})
    return p

import re as _re


def _reveal(dev, sel):
    """Best-effort scroll until a node is on screen; never raises."""
    try:
        return bool(dev.scroll_to(sel))
    except Exception:
        return False


def _onboard(dev, p):
    h.fresh(dev, APP, SEED)
    agreed = False
    for _ in range(8):
        if h.has_exact_ci(dev, "Plan") and h.has_exact_ci(dev, "Home"):
            return
        if h.go_opt(dev, p, "onb_start"):
            continue
        if not agreed:
            if h.has(dev, "Important information"):
                _reveal(dev, {"text": "I have read and agree"})
            if h.go_opt(dev, p, "onb_agree"):
                agreed = True
                continue
        if h.go_opt(dev, p, "onb_skip"):
            continue
        if h.go_opt(dev, p, "onb_continue"):
            continue
        if h.go_opt(dev, p, "onb_open"):
            continue
        break


def _labels(p, key):
    return [s.get("text") or s.get("desc") for s in (p.get("nav") or {}).get(key, []) if s.get("text") or s.get("desc")]


def _new_group_new_medicine(dev, p):
    """Plan > Add (group) > Medications Add > Add medicine: leaves the 'Add medicine' sheet open."""
    h.go(dev, p, "tab_plan")
    _reveal(dev, {"text": "Add"})
    h.go(dev, p, "add_group")
    _reveal(dev, {"text": "Add"})
    h.go(dev, p, "group_add_medication")
    h.go(dev, p, "add_medicine_btn")


def _setup(dev, p, strength):
    """Antiandrogen tablet in a new daily group (default time: next :00/:30 today), saved; Home tab."""
    _onboard(dev, p)
    _new_group_new_medicine(dev, p)
    h.go(dev, p, "cat_antiandrogen")
    h.go_opt(dev, p, "prep_tablet")
    h.type_into(dev, p, "strength_field", strength)
    if h.find(dev, p["nav"]["save"]) is None:
        dev.back()   # close the keyboard that covers Save
        dev.wait_idle()
    h.go(dev, p, "save")   # sheet
    dev.wait_idle()
    h.go(dev, p, "save")   # group editor
    h.go(dev, p, "tab_home")


def _scan(dev):
    """Texts of the Home screen around the Antiandrogen card (top of card, then one swipe lower)."""
    _reveal(dev, {"text": "Antiandrogen"})
    ts = list(h.texts(dev))
    try:
        h.swipe(dev, "Antiandrogen", "up")
    except Exception:
        pass
    return ts + list(h.texts(dev))


def _quick_log(dev, p):
    if h.find(dev, p["nav"]["quick_log"]) is None:
        _reveal(dev, {"text": "Quick log"})
    h.go(dev, p, "quick_log")
    h.go(dev, p, "save")   # 'Add record' sheet: confirm the dose
    dev.wait_idle()


def _due_tomorrow(ts):
    return any("due tomorrow" in t.casefold() for t in ts)


# Bug: the Home Antiandrogen card ignores a fulfilled slot, so after the dose is logged its Due
# line still names the logged slot (today's time) instead of the next one (tomorrow).
def _target(dev, p):
    _setup(dev, p, "25")
    _quick_log(dev, p)
    ts = _scan(dev)
    return _due_tomorrow(ts), {"texts": ts[:60]}


def _held(dev, p):
    _setup(dev, p, "50")
    _quick_log(dev, p)
    h.relaunch(dev, PACKAGE)
    ts = _scan(dev)
    return _due_tomorrow(ts), {"texts": ts[:60]}


def _keep(dev, p):
    # before any dose is logged the card names the upcoming slot in both builds
    _setup(dev, p, "25")
    ts = _scan(dev)
    return any(t.casefold().startswith("due ") for t in ts), {"texts": ts[:60]}


def target(dev, params):
    return h.run(_target, dev, _p(params), TIER)


def held_out(dev, params):
    return h.run(_held, dev, _p(params), TIER)


def preserve(dev, params):
    return h.run(_keep, dev, _p(params), "A" if DB else "B")


CHECKS = {"target": target, "held_out": [held_out], "preservation": [preserve]}
