"""Deterministic checks for nerdcalci-0007. passed=True means intended behaviour (bug absent).
Each check re-seeds, drives the trigger through the Device API, then observes.
No wall-clock reads or sleeps; labels live in params["nav"] (bug.json)."""
from __future__ import annotations
import re as _re
from dataset_tools import check_helpers as h

APP = 'nerdcalci'
PACKAGE = 'com.vishaltelangre.nerdcalci'
SEED = 'calci_basic'
DB = ''
TIER = 'B'
PARAMS_DEFAULT = {'nav': {'file_expenses': [{'text': 'Expenses'}], 'file_budget': [{'text': 'Monthly budget'}], 'file_temps': [{'text': 'Temperatures'}], 'file_sums': [{'text': 'Temperature sums'}], 'file_bases': [{'text': 'Number bases'}], 'file_dates': [{'text': 'Date gaps'}], 'file_times': [{'text': 'Time differences'}], 'file_rem': [{'text': 'Remainders'}], 'file_pct': [{'text': 'Percentages'}], 'back': [{'desc': 'Back'}]}}


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


def _open_file(dev, p, key):
    """Home screen > tap the file row (scrolling the list when needed)."""
    sel = p["nav"][key]
    if h.find(dev, sel) is None:
        _reveal(dev, sel[0])
    h.go(dev, p, key)


def _norm(t):
    return t.replace(",", "").replace("\u202f", " ").replace("\u00a0", " ").strip()


def _num(n, unit=""):
    pat = _re.compile("^" + _re.escape(n) + r"(\.0+)?" + (r"\s*" + _re.escape(unit) if unit else "") + "$")
    return lambda t: bool(pat.match(t))


def _lit(s):
    return lambda t: t == s


def _read(dev, matchers):
    """Result texts of the open file, re-read until every matcher is satisfied (results are computed on open)."""
    ts = []
    for _ in range(6):
        ts = [_norm(t) for t in h.texts(dev)]
        if all(any(m(t) for t in ts) for m in matchers):
            return ts, True
        dev.wait_idle()
    return ts, False


# The modulo operator % gives Err instead of the remainder.
def _target(dev, p):
    h.fresh(dev, APP, SEED)
    _open_file(dev, p, "file_rem")
    ts, ok = _read(dev, [_num('9')])
    return ok, {"texts": ts[:60]}


def _held(dev, p):
    h.fresh(dev, APP, SEED)
    h.relaunch(dev, PACKAGE)
    _open_file(dev, p, "file_rem")
    ts, ok = _read(dev, [_num('7'), _num('8')])
    return ok, {"texts": ts[:60]}


def _keep(dev, p):
    # a result the patched logic does not touch is the same in both builds
    h.fresh(dev, APP, SEED)
    _open_file(dev, p, "file_rem")
    ts, ok = _read(dev, [_num('300')])
    return ok, {"texts": ts[:60]}


def target(dev, params):
    return h.run(_target, dev, _p(params), TIER)


def held_out(dev, params):
    return h.run(_held, dev, _p(params), TIER)


def preserve(dev, params):
    return h.run(_keep, dev, _p(params), "A" if DB else "B")


CHECKS = {"target": target, "held_out": [held_out], "preservation": [preserve]}
