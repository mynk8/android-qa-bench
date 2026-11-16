"""Deterministic checks for featherline-0020. passed=True means intended behaviour (bug absent).
Each check re-seeds, drives the trigger through the Device API, then observes.
No wall-clock reads or sleeps; labels live in params["nav"] (bug.json)."""
from __future__ import annotations
import re as _re
from dataset_tools import check_helpers as h

APP = 'featherline'
PACKAGE = 'com.mkx.hrttracker'
SEED = 'plan_empty'
DB = ''
TIER = 'B'
PARAMS_DEFAULT = {'nav': {'onboarding_skip': [{'text': 'Skip'}, {'text': 'Get started'}, {'text': 'Continue'}], 'add_medication': [{'text': 'Add medicine'}, {'text': 'Add medication'}, {'desc': 'Add medication'}, {'text': '+ New medicine'}], 'new_medicine': [{'text': 'Add medicine'}, {'text': '+ New medicine'}], 'route_gel': [{'text': 'Gel'}], 'route_oral': [{'text': 'Oral'}], 'prep_tablet': [{'text': 'Tablet'}], 'name_field': [{'text': 'Name'}, {'text': 'Medicine name'}], 'strength_field': [{'text': 'Tablet strength (mg)'}, {'text': 'Tablet strength'}], 'per_dose_field': [{'text': 'Tablets per dose'}], 'save': [{'text': 'Save'}, {'desc': 'Save'}], 'calibration': [{'text': 'Calibration'}, {'desc': 'Calibration'}], 'e2_field': [{'text': 'E2'}], 'ime_next': [{'desc': 'Next'}], 'focused_field': [{'text': ''}], 'stock_field': [{'text': 'Stock'}, {'desc': 'Stock'}], 'add_stock': [{'text': 'Add'}, {'text': 'Add stock'}], 'log_dose': [{'text': 'Log now'}, {'text': 'Quick log'}, {'text': 'Logged'}], 'backfill': [{'text': 'Past schedule'}, {'text': 'Past due'}], 'labs': [{'text': 'Labs'}, {'text': 'Test results'}, {'text': 'Add result'}], 'add_result': [{'text': 'Add result'}, {'text': 'Add'}], 'result_name': [{'text': 'Name'}], 'result_value': [{'text': 'Value'}, {'text': 'Result'}], 'medicine_list': [{'text': 'Medications'}, {'text': 'Plan'}], 'prep_patch': [{'text': 'Patch'}, {'text': 'Patch release rate'}], 'onb_start': [{'text': 'Get started'}], 'onb_agree': [{'text': 'I have read and agree'}], 'onb_skip': [{'text': 'Skip'}], 'onb_continue': [{'text': 'Continue'}], 'onb_open': [{'text': 'Open Featherline'}], 'tab_plan': [{'text': 'Plan'}, {'desc': 'Plan'}], 'tab_home': [{'text': 'Home'}, {'desc': 'Home'}], 'add_group': [{'text': 'Add'}], 'group_add_medication': [{'text': 'Add'}], 'add_medicine_btn': [{'text': 'Add medicine'}], 'display_name_field': [{'text': 'Display name'}], 'tab_settings': [{'text': 'Settings'}, {'desc': 'Settings'}], 'tab_history': [{'text': 'History'}, {'desc': 'History'}], 'weight_row': [{'text': 'Body weight'}], 'weight_field': [{'text': 'Weight'}], 'weight_save': [{'text': 'Save'}], 'weight_clear': [{'text': 'Clear'}], 'daily_choice': [{'text': 'Daily'}], 'weekly_choice': [{'text': 'Weekly'}], 'start_date_row': [{'text': 'Start date'}], 'dialog_ok': [{'text': 'OK'}], 'dialog_cancel': [{'text': 'Cancel'}], 'custom_category': [{'text': 'Custom'}], 'custom_name_field': [{'text': 'Medication name'}], 'language_row': [{'text': 'App language'}]}}


def _p(params):
    p = dict(PARAMS_DEFAULT)
    p.update(params or {})
    return p


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


def _new_group(dev, p):
    """Plan > Add (group): leaves the new group editor open."""
    h.go(dev, p, "tab_plan")
    _reveal(dev, {"text": "Add"})
    h.go(dev, p, "add_group")


def _group_with_medicine_sheet(dev, p):
    _onboard(dev, p)
    _new_group(dev, p)
    _reveal(dev, {"text": "Add"})
    h.go(dev, p, "group_add_medication")
    h.go(dev, p, "add_medicine_btn")


def _add_custom(dev, p, name, strength):
    """With the 'Add medicine' sheet open: category Custom, a name, a tablet strength, Save."""
    h.go(dev, p, "custom_category")
    h.type_into(dev, p, "custom_name_field", name)
    dev.back()   # close the keyboard that hides the lower fields
    dev.wait_idle()
    _reveal(dev, {"text": "Tablet strength"})
    h.type_into(dev, p, "strength_field", strength)
    if h.find(dev, p["nav"]["save"]) is None:
        dev.back()   # close the keyboard that covers Save
        dev.wait_idle()
    if h.find(dev, p["nav"]["save"]) is None:
        _reveal(dev, {"text": "Save"})
    h.go(dev, p, "save")


def _route_labels(dev):
    ts = h.texts(dev)
    custom = [t for t in ts if _re.match(r"^Custom\s*\u00b7", t)]
    oral = [t for t in ts if _re.match(r"^Oral\s*\u00b7", t)]
    return custom, oral, ts


# A custom medicine's card reads Custom as its route, not Oral.
def _target(dev, p):
    _group_with_medicine_sheet(dev, p)
    _add_custom(dev, p, "Custom A", "2")
    custom, oral, ts = _route_labels(dev)
    return bool(custom) and not oral, {"custom": custom, "oral": oral, "texts": ts[:50]}


def _held(dev, p):
    # two custom medicines in one group
    _group_with_medicine_sheet(dev, p)
    _add_custom(dev, p, "Custom B", "3")
    _reveal(dev, {"text": "Add"})
    h.go(dev, p, "group_add_medication")
    h.go(dev, p, "add_medicine_btn")
    _add_custom(dev, p, "Custom D", "5")
    custom, oral, ts = _route_labels(dev)
    return len(custom) >= 2 and not oral, {"custom": custom, "oral": oral, "texts": ts[:50]}


def _keep(dev, p):
    # a catalogue estradiol tablet keeps its Oral route label
    _group_with_medicine_sheet(dev, p)
    h.type_into(dev, p, "display_name_field", "Estradiol C")
    dev.back()
    dev.wait_idle()
    _reveal(dev, {"text": "Tablet strength"})
    h.type_into(dev, p, "strength_field", "2")
    if h.find(dev, p["nav"]["save"]) is None:
        dev.back()
        dev.wait_idle()
    if h.find(dev, p["nav"]["save"]) is None:
        _reveal(dev, {"text": "Save"})
    h.go(dev, p, "save")
    custom, oral, ts = _route_labels(dev)
    return bool(oral) and not custom, {"custom": custom, "oral": oral, "texts": ts[:50]}


def target(dev, params):
    return h.run(_target, dev, _p(params), TIER)


def held_out(dev, params):
    return h.run(_held, dev, _p(params), TIER)


def preserve(dev, params):
    return h.run(_keep, dev, _p(params), "A" if DB else "B")


CHECKS = {"target": target, "held_out": [held_out], "preservation": [preserve]}
