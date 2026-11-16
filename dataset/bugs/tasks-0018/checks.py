"""Deterministic checks for tasks-0018. passed=True means intended behaviour (bug absent).
Each check re-seeds, drives the trigger through the Device API, then observes.
No wall-clock reads or sleeps; labels live in params["nav"] (bug.json)."""
from __future__ import annotations
from dataset_tools import check_helpers as h

APP = 'tasks'
PACKAGE = 'org.tasks'
SEED = 'inbox_basic'
DB = 'database'
TIER = 'B'
PARAMS_DEFAULT = {'nav': {'sort_icon': [{'desc': 'Sort'}, {'text': 'Sort'}], 'group_row': [{'text': 'Grouping'}], 'group_none': [{'text': 'None'}], 'sorting_row': [{'text': 'Sorting'}], 'sort_title': [{'text': 'By title'}]}}

def _p(params):
    p = dict(PARAMS_DEFAULT)
    p.update(params or {})
    return p

def _app_texts(dev):
    out = []
    for n in h.nodes(dev):
        pk = n.get("package")
        if pk and pk != PACKAGE:
            continue
        for k in ("text", "desc"):
            v = n.get(k)
            if v:
                out.append(str(v))
    return out

def _write(dev, stmts):
    dev.write_seed_sql(DB, stmts)
    dev.launch(PACKAGE)
    dev.wait_idle()

def _rename(old, new):
    return "UPDATE tasks SET title='" + new + "' WHERE title='" + old + "'"

def _by_title(dev, p):
    h.go(dev, p, "sort_icon")
    h.go(dev, p, "group_row")
    h.go(dev, p, "group_none")
    h.go(dev, p, "sorting_row")
    h.go(dev, p, "sort_title")
    dev.back()
    dev.wait_idle()

def _order(dev, names):
    ts = _app_texts(dev)
    idx = [h.index_of(ts, n) for n in names]
    return idx, ts

def _target(dev, p):
    h.fresh(dev, APP, SEED)
    _write(dev, [_rename("Buy milk", "Zucchini")])
    _by_title(dev, p)
    idx, ts = _order(dev, ["Pack for trip", "Pay rent", "Read docs", "Zucchini"])
    return all(i >= 0 for i in idx) and idx == sorted(idx), {"idx": idx, "texts": ts[:60]}

def _held(dev, p):
    h.fresh(dev, APP, SEED)
    _write(dev, [_rename("Read docs", "Aardvark")])
    _by_title(dev, p)
    idx, ts = _order(dev, ["Aardvark", "Buy milk", "Pack for trip", "Pay rent"])
    return all(i >= 0 for i in idx) and idx == sorted(idx), {"idx": idx, "texts": ts[:60]}

def _keep(dev, p):
    h.fresh(dev, APP, SEED)
    _write(dev, [_rename("Buy milk", "Zucchini")])
    idx, ts = _order(dev, ["Zucchini", "Pack for trip", "Pay rent", "Read docs"])
    return all(i >= 0 for i in idx) and idx == sorted(idx), {"idx": idx, "texts": ts[:60]}


def target(dev, params):
    return h.run(_target, dev, _p(params), TIER)


def held_out(dev, params):
    return h.run(_held, dev, _p(params), TIER)


def preserve(dev, params):
    return h.run(_keep, dev, _p(params), "A" if DB else "B")


CHECKS = {"target": target, "held_out": [held_out], "preservation": [preserve]}
