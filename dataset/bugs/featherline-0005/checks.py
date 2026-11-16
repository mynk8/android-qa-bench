"""Deterministic checks for featherline-0005. passed=True means intended behaviour (bug absent).
Each check re-seeds, drives the trigger through the Device API, then observes.
No wall-clock reads or sleeps; labels live in params["nav"] (bug.json)."""
from __future__ import annotations
from dataset_tools import check_helpers as h

APP = 'featherline'
PACKAGE = 'com.mkx.hrttracker'
SEED = 'plan_empty'
DB = ''
TIER = 'B'
PARAMS_DEFAULT = {'nav': {'onboarding_skip': [{'text': 'Skip'}, {'text': 'Get started'}, {'text': 'Continue'}], 'add_medication': [{'text': 'Add medicine'}, {'text': 'Add medication'}, {'desc': 'Add medication'}, {'text': '+ New medicine'}], 'new_medicine': [{'text': 'Add medicine'}, {'text': '+ New medicine'}], 'route_gel': [{'text': 'Gel'}], 'route_oral': [{'text': 'Oral'}], 'prep_tablet': [{'text': 'Tablet'}], 'name_field': [{'text': 'Name'}, {'text': 'Medicine name'}], 'strength_field': [{'text': 'Tablet strength'}], 'per_dose_field': [{'text': 'Tablets per dose'}], 'save': [{'text': 'Save'}, {'desc': 'Save'}], 'calibration': [{'text': 'Calibration'}, {'desc': 'Calibration'}], 'e2_field': [{'text': 'E2'}], 'ime_next': [{'desc': 'Next'}], 'focused_field': [{'text': ''}], 'stock_field': [{'text': 'Stock'}, {'desc': 'Stock'}], 'add_stock': [{'text': 'Add'}, {'text': 'Add stock'}], 'log_dose': [{'text': 'Log now'}, {'text': 'Quick log'}, {'text': 'Logged'}], 'backfill': [{'text': 'Past schedule'}, {'text': 'Past due'}], 'labs': [{'text': 'Labs'}, {'text': 'Test results'}, {'text': 'Add result'}], 'add_result': [{'text': 'Add result'}, {'text': 'Add'}], 'result_name': [{'text': 'Name'}], 'result_value': [{'text': 'Value'}, {'text': 'Result'}], 'medicine_list': [{'text': 'Medications'}, {'text': 'Plan'}], 'prep_patch': [{'text': 'Patch'}, {'text': 'Patch release rate'}]}}


def _p(params):
    p = dict(PARAMS_DEFAULT)
    p.update(params or {})
    return p

def _open_editor(dev, p):
    h.fresh(dev, APP, SEED)
    h.go_opt(dev, p, "onboarding_skip")
    h.go(dev, p, "add_medication")
    h.go_opt(dev, p, "new_medicine")

def _switch_back(dev, p, first, second, typed):
    # Diff: changeMedicationKey clears dose-value fields on a real kind switch, so a value
    # typed before the switch does not reappear when the user switches back.
    _open_editor(dev, p)
    h.go_opt(dev, p, first)
    h.go_opt(dev, p, "strength_field")
    h.type_into(dev, p, "strength_field", typed)
    h.go(dev, p, second)
    dev.wait_idle()
    h.go(dev, p, first)
    dev.wait_idle()
    ts = h.texts(dev)
    # Intended: leftover dose value is gone. Buggy: typed value is resurrected.
    return typed not in ts and not any(t.strip() == typed for t in ts), {"texts": ts[:40]}

def _target(dev, p):
    return _switch_back(dev, p, "prep_tablet", "prep_patch", "100")

def _held(dev, p):
    return _switch_back(dev, p, "prep_tablet", "prep_patch", "250")

def _keep(dev, p):
    _open_editor(dev, p)
    return h.has(dev, "Tablet") or h.has(dev, "Name") or h.has(dev, "Preparation"), {"texts": h.texts(dev)[:40]}


def target(dev, params):
    return h.run(_target, dev, _p(params), TIER)


def held_out(dev, params):
    return h.run(_held, dev, _p(params), TIER)


def preserve(dev, params):
    return h.run(_keep, dev, _p(params), "A" if DB else "B")


CHECKS = {"target": target, "held_out": [held_out], "preservation": [preserve]}
