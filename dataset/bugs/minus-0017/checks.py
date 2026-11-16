"""Deterministic checks for minus-0017. passed=True means intended behaviour (bug absent).
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
PARAMS_DEFAULT = {'nav': {'dismiss_tutorial': [{'text': 'Skip'}, {'text': 'Got it'}, {'text': 'OK'}], 'key_1': [{'text': '1'}], 'key_2': [{'text': '2'}], 'key_3': [{'text': '3'}], 'key_4': [{'text': '4'}], 'key_5': [{'text': '5'}], 'key_6': [{'text': '6'}], 'key_7': [{'text': '7'}], 'key_8': [{'text': '8'}], 'key_9': [{'text': '9'}], 'op_plus': [{'text': '+'}, {'desc': '+'}], 'op_minus': [{'text': '-'}, {'desc': '-'}], 'op_times': [{'text': '×'}, {'desc': '×'}], 'op_div': [{'text': '÷'}, {'desc': '÷'}]}}


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


AMT = re.compile(r"\d[\d,]*(?:\.\d+)?")


def _result_amounts(dev):
    """Normalised numbers in the result line shown under the typed expression ('= ...')."""
    ts = h.texts(dev)
    shown = [t for t in ts if "=" in t] or ts
    out = set()
    for t in shown:
        for m in AMT.findall(t):
            v = m.replace(",", "")
            if "." in v:
                v = v.rstrip("0").rstrip(".")
            out.add(v)
    return out, shown[:12]


def _type_expression(dev, p, seq):
    _start(dev, p)
    # the operator row is revealed by swiping up on the numpad
    h.swipe(dev, "5", "up")
    if h.find(dev, p["nav"]["op_plus"]) is None:
        raise h.StepMissing("calc_mode")
    for step in seq:
        h.go(dev, p, step)
    return _result_amounts(dev)


def _target(dev, p):
    # 2 + 3 x 4: multiplication first = 14 (left to right would give 20)
    amts, seen = _type_expression(dev, p, ["key_2", "op_plus", "key_3", "op_times", "key_4"])
    return "14" in amts and "20" not in amts, {"result_amounts": sorted(amts), "seen": seen}


def _held(dev, p):
    # 6 + 8 / 2: division first = 10 (left to right would give 7)
    amts, seen = _type_expression(dev, p, ["key_6", "op_plus", "key_8", "op_div", "key_2"])
    return "10" in amts and "7" not in amts, {"result_amounts": sorted(amts), "seen": seen}


def _keep(dev, p):
    # a sum with a single kind of operator is unaffected by precedence: 4 + 5 + 6 = 15
    amts, seen = _type_expression(dev, p, ["key_4", "op_plus", "key_5", "op_plus", "key_6"])
    return "15" in amts, {"result_amounts": sorted(amts), "seen": seen}


def target(dev, params):
    return h.run(_target, dev, _p(params), TIER)


def held_out(dev, params):
    return h.run(_held, dev, _p(params), TIER)


def preserve(dev, params):
    return h.run(_keep, dev, _p(params), "A" if DB else "B")


CHECKS = {"target": target, "held_out": [held_out], "preservation": [preserve]}
