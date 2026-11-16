"""Deterministic checks for tasks-0021. passed=True means intended behaviour (bug absent).
Each check re-seeds, drives the trigger through the Device API, then observes.
No wall-clock reads or sleeps; labels live in params["nav"] (bug.json)."""
from __future__ import annotations
from dataset_tools import check_helpers as h

APP = 'tasks'
PACKAGE = 'org.tasks'
SEED = 'inbox_basic'
DB = 'database'
TIER = 'B'
PARAMS_DEFAULT = {'nav': {'sort_icon': [{'desc': 'Sort'}, {'text': 'Sort'}]}}

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

def _sheet_rows(dev):
    """Order buttons on the Sort sheet, keyed by the row title they sit in."""
    ns = [n for n in h.nodes(dev) if not n.get("package") or n.get("package") == PACKAGE]
    def y(n):
        b = n.get("bounds") or [0, 0, 0, 0]
        return (b[1] + b[3]) / 2
    titles = sorted((y(n), (n.get("text") or "").strip()) for n in ns
                    if (n.get("text") or "").strip() in ("Grouping", "Sorting", "Subtasks", "Completed"))
    btns = sorted((y(n), (n.get("text") or n.get("desc") or "").strip()) for n in ns
                  if (n.get("text") or n.get("desc") or "").strip() in ("Ascending", "Descending"))
    rows = {}
    for by, label in btns:
        owner = None
        for ty, t in titles:
            if ty <= by + 30:
                owner = t
        rows.setdefault(owner, []).append(label)
    return rows

def _open_sheet(dev, p):
    h.go(dev, p, "sort_icon")

def _target(dev, p):
    h.fresh(dev, APP, SEED)
    _open_sheet(dev, p)
    rows = _sheet_rows(dev)
    return rows.get("Sorting") == ["Ascending"], {"rows": {str(k): v for k, v in rows.items()}}

def _held(dev, p):
    h.fresh(dev, APP, SEED)
    h.relaunch(dev, PACKAGE)
    _open_sheet(dev, p)
    rows = _sheet_rows(dev)
    return rows.get("Sorting") == ["Ascending"], {"rows": {str(k): v for k, v in rows.items()}}

def _keep(dev, p):
    h.fresh(dev, APP, SEED)
    _open_sheet(dev, p)
    rows = _sheet_rows(dev)
    return rows.get("Grouping") == ["Ascending"], {"rows": {str(k): v for k, v in rows.items()}}


def target(dev, params):
    return h.run(_target, dev, _p(params), TIER)


def held_out(dev, params):
    return h.run(_held, dev, _p(params), TIER)


def preserve(dev, params):
    return h.run(_keep, dev, _p(params), "A" if DB else "B")


CHECKS = {"target": target, "held_out": [held_out], "preservation": [preserve]}
