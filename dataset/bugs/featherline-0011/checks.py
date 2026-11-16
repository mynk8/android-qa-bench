"""Deterministic checks for featherline-0011. passed=True means intended behaviour (bug absent).
Each check re-seeds, drives the trigger through the Device API, then observes.
No wall-clock reads or sleeps; labels live in params["nav"] (bug.json)."""
from __future__ import annotations
from dataset_tools import check_helpers as h

APP = 'featherline'
PACKAGE = 'com.mkx.hrttracker'
SEED = 'plan_empty'
DB = ''
TIER = 'B'
PARAMS_DEFAULT = {'nav': {'onboarding_skip': [{'text': 'Skip'}, {'text': 'Get started'}, {'text': 'Continue'}], 'add_medication': [{'text': 'Add medicine'}, {'text': 'Add medication'}, {'desc': 'Add medication'}, {'text': '+ New medicine'}], 'new_medicine': [{'text': 'Add medicine'}, {'text': '+ New medicine'}], 'route_gel': [{'text': 'Gel'}], 'route_oral': [{'text': 'Oral'}], 'prep_tablet': [{'text': 'Tablet'}], 'name_field': [{'text': 'Name'}, {'text': 'Medicine name'}], 'strength_field': [{'text': 'Tablet strength (mg)'}, {'text': 'Tablet strength'}], 'per_dose_field': [{'text': 'Tablets per dose'}], 'save': [{'text': 'Save'}, {'desc': 'Save'}], 'calibration': [{'text': 'Calibration'}, {'desc': 'Calibration'}], 'e2_field': [{'text': 'E2'}], 'ime_next': [{'desc': 'Next'}], 'focused_field': [{'text': ''}], 'stock_field': [{'text': 'Stock'}, {'desc': 'Stock'}, {'text': 'On hand'}], 'add_stock': [{'text': 'Add'}, {'text': 'Add stock'}, {'desc': 'Add stock'}], 'log_dose': [{'text': 'Log now'}, {'text': 'Quick log'}, {'text': 'Logged'}, {'text': 'Log dose'}, {'text': 'Take'}, {'text': 'Mark taken'}, {'desc': 'Log'}, {'desc': 'Log now'}, {'desc': 'Quick log'}], 'backfill': [{'text': 'Past schedule'}, {'text': 'Past due'}, {'text': 'Backfill'}, {'text': 'Log past dose'}, {'text': 'Retrospective'}, {'text': 'Past'}, {'desc': 'Past schedule'}, {'desc': 'Past due'}], 'date_row': [{'text': 'Date'}, {'desc': 'Date'}], 'medicine_list': [{'text': 'Medications'}, {'text': 'Plan'}, {'text': 'Catalogue'}], 'labs': [{'text': 'Labs'}, {'text': 'Test results'}, {'text': 'Add result'}, {'text': 'Blood tests'}, {'text': 'Results'}], 'add_result': [{'text': 'Add result'}, {'text': 'Add'}, {'desc': 'Add'}], 'result_name': [{'text': 'Name'}, {'text': 'Marker'}], 'result_value': [{'text': 'Value'}, {'text': 'Result'}], 'e2_marker': [{'text': 'E2'}, {'text': 'Estradiol'}], 'prep_patch': [{'text': 'Patch'}, {'text': 'Patch release rate'}], 'onb_start': [{'text': 'Get started'}], 'onb_agree': [{'text': 'I have read and agree'}], 'onb_skip': [{'text': 'Skip'}], 'onb_continue': [{'text': 'Continue'}], 'onb_open': [{'text': 'Open Featherline'}], 'tab_plan': [{'text': 'Plan'}, {'desc': 'Plan'}], 'tab_home': [{'text': 'Home'}, {'desc': 'Home'}], 'medicines_icon': [{'desc': 'Medicines'}, {'text': 'Medicines'}], 'add_group': [{'text': 'Add'}], 'group_add_medication': [{'text': 'Add'}], 'add_medicine_btn': [{'text': 'Add medicine'}], 'display_name_field': [{'text': 'Display name'}], 'start_date_row': [{'text': 'Start date'}], 'date_ok': [{'text': 'OK'}], 'date_prev_month': [{'desc': 'Change to previous month'}, {'desc': 'Switch to previous month'}, {'desc': 'previous month'}], 'past_completed': [{'text': 'Mark as completed'}], 'stock_enable': [{'text': 'Enable stock tracking'}], 'stock_plus10': [{'text': '+10'}], 'stock_plus14': [{'text': '+14'}], 'stock_add': [{'text': 'Add'}]}}


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


STOCK_N = _re.compile(r"(\d+)\s*/\s*\d+\s*tablets?\b")   # current stock of "N / M tablets"


def _to_plan(dev):
    for _ in range(5):
        if h.has_exact_ci(dev, "Plan") and h.has_exact_ci(dev, "Home"):
            return
        dev.back()
        dev.wait_idle()


def _create_tracked_medicine(dev, p, name, chip):
    """Plan > Medicines > Add medicine (Estradiol tablet, 2 mg) > details page > Enable stock tracking."""
    h.go(dev, p, "tab_plan")
    h.go(dev, p, "medicines_icon")
    h.go(dev, p, "add_medicine_btn")
    h.type_into(dev, p, "display_name_field", name)
    dev.back()   # close the keyboard that hides the lower fields
    dev.wait_idle()
    _reveal(dev, {"text": "Tablet strength (mg)"})
    h.type_into(dev, p, "strength_field", "2")
    if h.find(dev, p["nav"]["save"]) is None:
        dev.back()   # close the keyboard that covers Save
        dev.wait_idle()
    h.go(dev, p, "save")
    _reveal(dev, {"text": "Enable stock tracking"})
    h.go(dev, p, "stock_enable")
    h.go(dev, p, chip)
    h.go(dev, p, "stock_add")
    dev.wait_idle()
    _to_plan(dev)


def _pick_yesterday(dev, p):
    """Start date row > date picker > the day before today (previous month when today is the 1st) > OK."""
    h.go(dev, p, "start_date_row")

    def cells():
        out = []
        for n in h.nodes(dev):
            lab = n.get("desc") or n.get("text") or ""
            if n.get("clickable") and _re.search(r",.*\b(19|20)\d\d\b", lab):
                out.append((lab, "desc" if n.get("desc") else "text", n))
        return out

    cs = cells()
    idx = next((i for i, c in enumerate(cs) if "today" in c[0].casefold()), None)
    if idx is None:
        idx = next((i for i, c in enumerate(cs) if c[2].get("selected")), None)
    if idx is None:
        raise h.StepMissing("date_picker_today_cell")
    if idx == 0:
        h.go(dev, p, "date_prev_month")
        cs = cells()
        if not cs:
            raise h.StepMissing("date_picker_prev_month_cells")
        pick = cs[-1]
    else:
        pick = cs[idx - 1]
    dev.tap({pick[1]: pick[0]})
    dev.wait_idle()
    h.go(dev, p, "date_ok")


def _group_with_medicine(dev, p, name, past):
    h.go(dev, p, "tab_plan")
    _reveal(dev, {"text": "Add"})
    h.go(dev, p, "add_group")
    _reveal(dev, {"text": "Add"})
    h.go(dev, p, "group_add_medication")
    try:
        h.tap_text(dev, name)
    except h.StepMissing:
        h.tap_text(dev, "Estradiol valerate")   # the list shows the catalogue name
    h.go(dev, p, "save")   # dose sheet, keep the default whole tablet
    dev.wait_idle()
    if past:
        _pick_yesterday(dev, p)
        _reveal(dev, {"text": "Mark as completed"})
        h.go(dev, p, "past_completed")
    h.go(dev, p, "save")   # group editor
    dev.wait_idle()


def _stock_numbers(dev, p, name):
    _to_plan(dev)
    h.go(dev, p, "tab_plan")
    h.go(dev, p, "medicines_icon")
    try:
        h.tap_text(dev, name)
    except h.StepMissing:
        h.tap_text(dev, "Estradiol valerate")
    _reveal(dev, {"text": "Stock"})
    ts = list(h.texts(dev))
    try:
        h.swipe(dev, "Stock", "up")
    except Exception:
        pass
    ts += list(h.texts(dev))
    nums = sorted({int(m) for t in ts for m in STOCK_N.findall(t)})
    return nums, ts


# Bug: "Mark as completed" on a past start date records the past doses through the path that
# deducts stock, so a tracked medicine drops below what was entered.
def _target(dev, p):
    _onboard(dev, p)
    _create_tracked_medicine(dev, p, "StockMed", "stock_plus10")
    _group_with_medicine(dev, p, "StockMed", True)
    nums, ts = _stock_numbers(dev, p, "StockMed")
    return 10 in nums, {"stock_numbers": nums, "texts": ts[:60]}


def _held(dev, p):
    _onboard(dev, p)
    _create_tracked_medicine(dev, p, "StockMedB", "stock_plus14")
    _group_with_medicine(dev, p, "StockMedB", True)
    h.relaunch(dev, PACKAGE)
    nums, ts = _stock_numbers(dev, p, "StockMedB")
    return 14 in nums, {"stock_numbers": nums, "texts": ts[:60]}


def _keep(dev, p):
    # same group save without a past start: no past records, stock untouched in both builds
    _onboard(dev, p)
    _create_tracked_medicine(dev, p, "StockMedK", "stock_plus10")
    _group_with_medicine(dev, p, "StockMedK", False)
    nums, ts = _stock_numbers(dev, p, "StockMedK")
    return 10 in nums, {"stock_numbers": nums, "texts": ts[:60]}


def target(dev, params):
    return h.run(_target, dev, _p(params), TIER)


def held_out(dev, params):
    return h.run(_held, dev, _p(params), TIER)


def preserve(dev, params):
    return h.run(_keep, dev, _p(params), "A" if DB else "B")


CHECKS = {"target": target, "held_out": [held_out], "preservation": [preserve]}
