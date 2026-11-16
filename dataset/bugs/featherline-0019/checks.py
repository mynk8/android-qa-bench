"""Deterministic checks for featherline-0019. passed=True means intended behaviour (bug absent).
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


def _start_is_now(dev):
    ts = h.texts(dev)
    if any(t.strip().casefold() == "now" for t in ts):
        return True
    return any(t.startswith("Start time") and t.rstrip().endswith("Now") for t in ts)


def _open_date(dev):
    # the "Start date" label can sit under the top bar; tap the date value (e.g. "Nov 11 Wed") instead
    _reveal(dev, {"text": "Start date"})
    for _ in range(8):
        if any(t.strip().casefold() == "start date" for t in h.texts(dev)):
            break
        try:
            dev.swipe({"text": "Weekly"}, "down")
            dev.wait_idle()
        except Exception:
            break
    ts = h.texts(dev)
    if not any(t.strip().casefold() == "start date" for t in ts):
        raise h.StepMissing("start_date_row")
    start = [t.strip().casefold() for t in ts].index("start date")
    for t in ts[start:]:
        if _re.match(r"^[A-Z][a-z]{2} \d{1,2} [A-Z][a-z]{2}$", t.strip()):
            dev.tap({"text": t})
            dev.wait_idle()
            return
    raise h.StepMissing("start_date_row")


def _repick_start_date(dev, p):
    _reveal(dev, {"text": "Start date"})
    if not _start_is_now(dev):
        raise h.StepMissing("start_now_initial")
    _open_date(dev)
    h.go(dev, p, "dialog_ok")
    _reveal(dev, {"text": "Start time"})
    return not _start_is_now(dev), {"texts": h.texts(dev)[:40]}


# Choosing the start date that is already set starts the plan with that whole day (Start time no longer Now).
def _target(dev, p):
    _onboard(dev, p)
    _new_group(dev, p)
    return _repick_start_date(dev, p)


def _held(dev, p):
    _onboard(dev, p)
    _new_group(dev, p)
    h.go(dev, p, "weekly_choice")
    return _repick_start_date(dev, p)


def _keep(dev, p):
    # opening the date picker and cancelling leaves the start as Now
    _onboard(dev, p)
    _new_group(dev, p)
    _open_date(dev)
    h.go(dev, p, "dialog_cancel")
    _reveal(dev, {"text": "Start time"})
    return _start_is_now(dev), {"texts": h.texts(dev)[:40]}


def target(dev, params):
    return h.run(_target, dev, _p(params), TIER)


def held_out(dev, params):
    return h.run(_held, dev, _p(params), TIER)


def preserve(dev, params):
    return h.run(_keep, dev, _p(params), "A" if DB else "B")


CHECKS = {"target": target, "held_out": [held_out], "preservation": [preserve]}
