"""Deterministic checks for tasks-0017. passed=True means intended behaviour (bug absent).
Each check re-seeds, drives the trigger through the Device API, then observes.
No wall-clock reads or sleeps; labels live in params["nav"] (bug.json)."""
from __future__ import annotations
from dataset_tools import check_helpers as h

APP = 'tasks'
PACKAGE = 'org.tasks'
SEED = 'inbox_basic'
DB = 'database'
TIER = 'B'
PARAMS_DEFAULT = {'nav': {'sort_icon': [{'desc': 'Sort'}, {'text': 'Sort'}], 'group_row': [{'text': 'Grouping'}], 'group_start': [{'text': 'By start date'}], 'group_toggle': [{'text': 'Ascending'}]}}

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

def _start(title, days_back):
    return ("UPDATE tasks SET hideUntil = (CAST(strftime('%s','now','start of day','-" + str(days_back)
            + " days') AS INTEGER))*1000 WHERE title='" + title + "'")

def _group_start(dev, p, descending):
    h.go(dev, p, "sort_icon")
    h.go(dev, p, "group_row")
    h.go(dev, p, "group_start")
    if descending:
        h.go(dev, p, "group_toggle")
    dev.back()
    dev.wait_idle()

def _headers_before(ts, item):
    i, j = h.index_of(ts, "No start date"), h.index_of(ts, item)
    if i < 0 or j <= i:
        return None, i, j
    return [t for t in ts[i + 1:j] if t.strip().startswith("Start ")], i, j

def _scenario(dev, p, title, days_back, descending):
    h.fresh(dev, APP, SEED)
    _write(dev, [_start(title, days_back)])
    _group_start(dev, p, descending)
    ts = _app_texts(dev)
    return ts

def _target(dev, p):
    ts = _scenario(dev, p, "Buy milk", 0, True)
    hdrs, i, j = _headers_before(ts, "Buy milk")
    return bool(hdrs), {"no_start": i, "item": j, "headers": hdrs, "texts": ts[:60]}

def _held(dev, p):
    ts = _scenario(dev, p, "Pay rent", 2, True)
    hdrs, i, j = _headers_before(ts, "Pay rent")
    return bool(hdrs), {"no_start": i, "item": j, "headers": hdrs, "texts": ts[:60]}

def _keep(dev, p):
    ts = _scenario(dev, p, "Buy milk", 0, False)
    first = [k for k, t in enumerate(ts) if t.strip().startswith("Start ")]
    none = h.index_of(ts, "No start date")
    return bool(first) and none > first[0], {"start_header": first, "no_start": none, "texts": ts[:60]}


def target(dev, params):
    return h.run(_target, dev, _p(params), TIER)


def held_out(dev, params):
    return h.run(_held, dev, _p(params), TIER)


def preserve(dev, params):
    return h.run(_keep, dev, _p(params), "A" if DB else "B")


CHECKS = {"target": target, "held_out": [held_out], "preservation": [preserve]}
