"""Deterministic checks for featherline-0016. passed=True means intended behaviour (bug absent).
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


def _open_weight(dev, p):
    h.go(dev, p, "tab_settings")
    _reveal(dev, {"text": "Body weight"})
    h.go(dev, p, "weight_row")


def _submit_weight(dev, p):
    """Done on the keyboard; if the sheet is still up without an error, tap Save."""
    h.key(dev, "ENTER")
    if h.has_exact_ci(dev, "Weight") and not h.has(dev, "Enter a valid weight"):
        h.go_opt(dev, p, "weight_save")


def _set_weight(dev, p, value):
    _open_weight(dev, p)
    h.type_into(dev, p, "weight_field", value)
    _submit_weight(dev, p)


def _row_shows(dev, value):
    return any(_re.search(r"(?<![\d.])" + _re.escape(value) + r"(?![\d])", t) for t in h.texts(dev))


def _clear_by_empty_save(dev, p, value):
    _onboard(dev, p)
    _set_weight(dev, p, value)
    _reveal(dev, {"text": "Body weight"})
    h.go(dev, p, "weight_row")
    sel = h.find(dev, [{"text": value}, {"text": value + ".0"}])
    if sel is None:
        raise h.StepMissing("weight_field_filled")
    dev.input_text(sel, "")
    dev.wait_idle()
    _submit_weight(dev, p)
    _reveal(dev, {"text": "Not set"})
    ok = h.has(dev, "Not set") and not h.has(dev, "Enter a valid weight")
    return ok, {"texts": h.texts(dev)[:40]}


# Saving an emptied weight field must clear the stored weight and close the sheet.
def _target(dev, p):
    return _clear_by_empty_save(dev, p, "60")


def _held(dev, p):
    # no weight stored yet: saving the untouched empty field just closes the sheet
    _onboard(dev, p)
    _open_weight(dev, p)
    h.go(dev, p, "weight_save")
    ok = not h.has(dev, "Enter a valid weight") and h.has(dev, "Not set")
    return ok, {"texts": h.texts(dev)[:40]}


def _keep(dev, p):
    _onboard(dev, p)
    _set_weight(dev, p, "65")
    _reveal(dev, {"text": "Body weight"})
    return _row_shows(dev, "65"), {"texts": h.texts(dev)[:40]}


def target(dev, params):
    return h.run(_target, dev, _p(params), TIER)


def held_out(dev, params):
    return h.run(_held, dev, _p(params), TIER)


def preserve(dev, params):
    return h.run(_keep, dev, _p(params), "A" if DB else "B")


CHECKS = {"target": target, "held_out": [held_out], "preservation": [preserve]}
