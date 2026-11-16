"""Deterministic checks for tasks-0016. passed=True means intended behaviour (bug absent).
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

DONE = "UPDATE tasks SET completed = (CAST(strftime('%s','now') AS INTEGER))*1000 WHERE title='{}'"

def _counts(dev):
    return [t.strip() for t in _app_texts(dev) if t.strip().isdigit()]

def _run(dev, p, done):
    h.fresh(dev, APP, SEED)
    if done:
        _write(dev, [DONE.format(done)])
    return h.has(dev, "Pack for trip"), _counts(dev)

def _target(dev, p):
    ok, c = _run(dev, p, "Charge phone")
    return ok and "1" in c and "2" not in c, {"chips": c}

def _held(dev, p):
    ok, c = _run(dev, p, "Print tickets")
    return ok and "1" in c and "2" not in c, {"chips": c}

def _keep(dev, p):
    ok, c = _run(dev, p, None)
    return ok and "2" in c and "1" not in c, {"chips": c}


def target(dev, params):
    return h.run(_target, dev, _p(params), TIER)


def held_out(dev, params):
    return h.run(_held, dev, _p(params), TIER)


def preserve(dev, params):
    return h.run(_keep, dev, _p(params), "A" if DB else "B")


CHECKS = {"target": target, "held_out": [held_out], "preservation": [preserve]}
