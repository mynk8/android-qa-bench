"""Deterministic checks for idlefantasy-0006. passed=True means intended behaviour (bug absent).
Each check re-seeds, drives the trigger through the Device API, then observes.
No wall-clock reads or sleeps; labels live in params["nav"] (bug.json)."""
from __future__ import annotations
import re
from dataset_tools import check_helpers as h

APP = 'idlefantasy'
PACKAGE = 'com.tristinbaker.idlefantasy'
SEED = 'idle_basic'
DB = 'fantasy_idler.db'
TIER = 'B'
PARAMS_DEFAULT = {'nav': {'nav_combat': [{'desc': 'Combat'}, {'text': 'Combat'}], 'gear_tab': [{'text': 'Gear'}], 'slot_body': [{'text': 'Body'}], 'slot_head': [{'text': 'Head'}], 'slot_weapon': [{'text': 'Weapon (Atk)'}], 'dismiss': [{'text': 'Got it'}]}}

def _p(params):
    p = dict(PARAMS_DEFAULT)
    p.update(params or {})
    return p


def _start(dev, p):
    h.fresh(dev, APP, SEED)
    h.go_opt(dev, p, "dismiss")


def _sql_relaunch(dev, p, stmts):
    """Edit the seeded data while the app is stopped, then start it again."""
    dev.force_stop(PACKAGE)
    dev.write_seed_sql(DB, stmts)
    dev.launch(PACKAGE)
    dev.wait_idle()
    h.go_opt(dev, p, "dismiss")


def _scroll_has(dev, sub):
    """True when some on-screen text contains `sub`, scrolling the list towards it if needed."""
    if h.has(dev, sub):
        return True
    dev.scroll_to({"text": sub})
    dev.wait_idle()
    return h.has(dev, sub)


def _open_shop(dev, p, sell=True):
    if not h.has_exact_ci(dev, "Shop"):
        dev.scroll_to({"text": "Shop"})
    h.go(dev, p, "shop")
    if sell:
        h.go(dev, p, "sell_tab")


def _price_of(dev, name):
    """Sell-list price (coins ea.) of the row called `name`."""
    dev.scroll_to({"text": name})
    ts = h.texts(dev)
    for i, t in enumerate(ts):
        if t == name or t.startswith(name + "\n") or t.startswith(name + " "):
            for u in ts[i:i + 5]:
                m = re.search(r"(\d[\d,]*) coins ea", u)
                if m:
                    return int(m.group(1).replace(",", "")), ts[:60]
    return None, ts[:60]


def _toggle_keep_one(dev, p):
    """Flip the 'Keep one of each item' switch on the Sell tab."""
    ns = h.nodes(dev)
    sw = next((n for n in ns if "Switch" in (n.get("class") or "") and n.get("bounds")), None)
    if sw is None:
        label = next((n for n in ns if n.get("text") == "Keep one of each item" and n.get("bounds")), None)
        if label is None or not hasattr(dev, "tap_xy"):
            raise h.StepMissing("keep_one_switch")
        x1, y1, x2, y2 = label["bounds"]
        dev.tap_xy(x2 + 80, (y1 + y2) // 2)
    else:
        x1, y1, x2, y2 = sw["bounds"]
        dev.tap_xy((x1 + x2) // 2, (y1 + y2) // 2)
    dev.wait_idle()


def _index(ts, name):
    for i, t in enumerate(ts):
        if t == name or t.startswith(name + " (") or t.startswith(name + "\n"):
            return i
    return -1


def _has_label(dev, label):
    return any(t == label or t.startswith(label + "\n") or t.startswith(label + " (") for t in h.texts(dev))

def _picker(dev, p, slot_step, slot_label):
    h.go(dev, p, "nav_combat")
    h.go(dev, p, "gear_tab")
    dev.scroll_to({"text": slot_label})
    h.go(dev, p, slot_step)
    ts = h.texts(dev)
    if not any(t.startswith("Choose ") for t in ts):
        raise h.StepMissing("picker_sheet")
    return ts


def _target(dev, p):
    _start(dev, p)
    ts = _picker(dev, p, "slot_body", "Body")
    a = _index(ts, "Runite Chainbody")
    b = _index(ts, "Adamantite Platebody")
    return a >= 0 and b >= 0 and a < b, {"order": [t for t in ts if "body" in t.lower() or "plate" in t.lower()][:10]}


def _held(dev, p):
    _start(dev, p)
    ts = _picker(dev, p, "slot_head", "Head")
    a = _index(ts, "Mithril Med Helmet")
    b = _index(ts, "Steel Full Helmet")
    return a >= 0 and b >= 0 and a < b, {"order": [t for t in ts if "helmet" in t.lower()][:10]}


def _keep(dev, p):
    # weapon picker: dagger then sword under either ordering
    _start(dev, p)
    ts = _picker(dev, p, "slot_weapon", "Weapon (Atk)")
    a = _index(ts, "Bronze Dagger")
    b = _index(ts, "Iron Sword")
    return a >= 0 and b >= 0 and a < b, {"texts": ts[:30]}


def target(dev, params):
    return h.run(_target, dev, _p(params), TIER)


def held_out(dev, params):
    return h.run(_held, dev, _p(params), TIER)


def preserve(dev, params):
    return h.run(_keep, dev, _p(params), TIER)


CHECKS = {"target": target, "held_out": [held_out], "preservation": [preserve]}
