"""Deterministic checks for tasks-0020. passed=True means intended behaviour (bug absent).
Each check re-seeds, drives the trigger through the Device API, then observes.
No wall-clock reads or sleeps; labels live in params["nav"] (bug.json)."""
from __future__ import annotations
from dataset_tools import check_helpers as h

APP = 'tasks'
PACKAGE = 'org.tasks'
SEED = 'inbox_basic'
DB = 'database'
TIER = 'B'
PARAMS_DEFAULT = {'nav': {}}

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

def _order(dev, names):
    ts = _app_texts(dev)
    return [h.index_of(ts, n) for n in names], ts

def _target(dev, p):
    h.fresh(dev, APP, SEED)
    idx, ts = _order(dev, ["Buy milk", "Pack for trip", "Pay rent", "Read docs"])
    return all(i >= 0 for i in idx) and idx == sorted(idx), {"idx": idx, "texts": ts[:60]}

def _held(dev, p):
    h.fresh(dev, APP, SEED)
    h.relaunch(dev, PACKAGE)
    idx, ts = _order(dev, ["Buy milk", "Pay rent", "Read docs"])
    return all(i >= 0 for i in idx) and idx == sorted(idx), {"idx": idx, "texts": ts[:60]}

def _keep(dev, p):
    h.fresh(dev, APP, SEED)
    ts = _app_texts(dev)
    return all(h.index_of(ts, n) >= 0 for n in ["Buy milk", "Pack for trip", "Pay rent", "Read docs"]), {"texts": ts[:60]}


def target(dev, params):
    return h.run(_target, dev, _p(params), TIER)


def held_out(dev, params):
    return h.run(_held, dev, _p(params), TIER)


def preserve(dev, params):
    return h.run(_keep, dev, _p(params), "A" if DB else "B")


CHECKS = {"target": target, "held_out": [held_out], "preservation": [preserve]}
