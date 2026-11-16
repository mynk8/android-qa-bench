"""Shared, deterministic helpers for bugs/*/checks.py (r40).

Only Device API calls (device_api.py) plus the optional adb-backed extensions
listed in device_ext.py (long_press, list_external, read_external, ...).
No wall-clock reads, no sleeps, no randomness: waiting is dev.wait_idle().

UI steps are driven by selector lists kept in each bug's params["nav"], so the
calibration team can correct a label in bug.json without touching code. A step
whose selectors are all absent raises StepMissing; the check then reports
passed=False with observed["step_missing"], which calibration surfaces.
"""
from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

from dataset_tools.device_api import CheckResult

DATASET = Path(__file__).resolve().parents[1] / "dataset"


class StepMissing(Exception):
    pass


# ---------- seeding ----------
def fresh(dev, app_id: str, seed_id: str) -> None:
    """Re-apply the app's seed so every check starts from the same state."""
    spec = importlib.util.spec_from_file_location(f"seed_{app_id}", DATASET / "apps" / app_id / "seed.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    seed = json.loads((DATASET / "apps" / app_id / "seed" / f"{seed_id}.json").read_text(encoding="utf-8"))
    # start from cleared app data when the device supports it (AdbDevice does);
    # otherwise data created by an earlier check would leak into this one
    reset = getattr(dev, "reset_app", None)
    if reset is not None:
        reset(json.loads((DATASET / "apps" / app_id / "app.json").read_text(encoding="utf-8"))["package"])
    mod.apply(dev, seed)
    dismiss_first_run(dev, app_id)


def dismiss_first_run(dev, app_id: str, rounds: int = 4) -> None:
    """Tap through first-run screens (welcome, sync offers, tutorials) listed in the
    app's app.json "first_run": a list of selector alternatives, tried in order each
    round. Screens that are not shown are skipped; nothing here raises."""
    app = json.loads((DATASET / "apps" / app_id / "app.json").read_text(encoding="utf-8"))
    # Android's own "Viewing full screen" notice appears for any immersive app
    steps = [[{"text": "Got it"}]] + (app.get("first_run") or [])
    for _ in range(rounds):
        hit = False
        for alts in steps:
            sel = find(dev, alts)
            if sel is not None:
                dev.tap(sel)
                dev.wait_idle()
                hit = True
        if not hit:
            return


def relaunch(dev, package: str) -> None:
    dev.force_stop(package)
    dev.launch(package)
    dev.wait_idle()


# ---------- observation ----------
def nodes(dev) -> list[dict]:
    return [n for n in dev.ui() if n.get("visible", True) is not False]


def texts(dev) -> list[str]:
    out = []
    for n in nodes(dev):
        for k in ("text", "desc"):
            v = n.get(k)
            if v:
                out.append(str(v))
    return out


def has(dev, s: str) -> bool:
    return any(s in t for t in texts(dev))


def has_exact_ci(dev, s: str) -> bool:
    s = s.casefold()
    return any(t.strip().casefold() == s for t in texts(dev))


def index_of(ts: list[str], s: str) -> int:
    for i, t in enumerate(ts):
        if t == s:
            return i
    for i, t in enumerate(ts):
        if s in t:
            return i
    return -1


AMOUNT = re.compile(r"(?<![\d.,])(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{1,2})?)(?![\d])")


def amounts(ts: list[str]) -> set[str]:
    """Normalised money-like tokens, e.g. '$60.00' -> '60', '1,234.50' -> '1234.5'."""
    out = set()
    for t in ts:
        for m in AMOUNT.findall(t):
            v = m.replace(",", "")
            if "." in v:
                v = v.rstrip("0").rstrip(".")
            out.add(v)
    return out


# ---------- input ----------
def _matches(node: dict, sel: dict) -> bool:
    for k in ("id", "text", "desc"):
        if k in sel:
            v = node.get(k) or ""
            if k == "id":
                return v == sel[k] or v.endswith("/" + sel[k])
            return v == sel[k]
    return False


def find(dev, alternatives: list[dict]) -> dict | None:
    ns = nodes(dev)
    for sel in alternatives:
        for n in ns:
            if _matches(n, sel):
                return sel
    # case-insensitive containment fallback for text/desc only
    for sel in alternatives:
        for k in ("text", "desc"):
            if k in sel:
                want = sel[k].casefold()
                for n in ns:
                    if want and want in (n.get(k) or "").casefold():
                        return {k: n.get(k)}
    return None


def go(dev, p: dict, step: str) -> dict:
    alts = (p.get("nav") or {}).get(step)
    if not alts:
        raise StepMissing(step)
    sel = find(dev, alts)
    if sel is None:
        raise StepMissing(step)
    dev.tap(sel)
    dev.wait_idle()
    return sel


def go_opt(dev, p: dict, step: str) -> bool:
    try:
        go(dev, p, step)
        return True
    except StepMissing:
        return False


def tap_text(dev, label: str) -> None:
    sel = find(dev, [{"text": label}, {"desc": label}])
    if sel is None:
        raise StepMissing(f"text:{label}")
    dev.tap(sel)
    dev.wait_idle()


def type_into(dev, p: dict, step: str, value: str) -> None:
    alts = (p.get("nav") or {}).get(step)
    sel = find(dev, alts or [])
    if sel is None:
        raise StepMissing(step)
    dev.input_text(sel, value)
    dev.wait_idle()


def long_press(dev, label: str) -> None:
    fn = getattr(dev, "long_press", None)
    if fn is None:
        raise StepMissing("device lacks long_press (device_ext.py)")
    sel = find(dev, [{"text": label}, {"desc": label}])
    if sel is None:
        raise StepMissing(f"long_press:{label}")
    fn(sel)
    dev.wait_idle()


def key(dev, name: str) -> None:
    """Press a key (ENTER, SEARCH, TAB, ...) via device_ext; StepMissing if unsupported."""
    fn = getattr(dev, "key", None)
    if fn is None:
        raise StepMissing("device lacks key (device_ext.py)")
    fn(name)
    dev.wait_idle()


def swipe(dev, label: str, direction: str = "left") -> None:
    fn = getattr(dev, "swipe", None)
    if fn is None:
        raise StepMissing("device lacks swipe (device_ext.py)")
    sel = find(dev, [{"text": label}, {"desc": label}])
    if sel is None:
        raise StepMissing(f"swipe:{label}")
    fn(sel, direction)
    dev.wait_idle()


def open_path(dev, labels: list[str]) -> None:
    """Tap folder labels in order when they are on screen (skips ones already passed)."""
    for lab in labels:
        if find(dev, [{"text": lab}]) is not None:
            tap_text(dev, lab)


# ---------- storage ----------
def list_ext(dev, rel: str) -> list[str]:
    fn = getattr(dev, "list_external", None)
    if fn is None:
        raise StepMissing("device lacks list_external (device_ext.py)")
    try:
        return sorted(fn(rel))
    except FileNotFoundError:
        return []


def read_ext(dev, rel: str) -> str | None:
    fn = getattr(dev, "read_external", None)
    if fn is None:
        raise StepMissing("device lacks read_external (device_ext.py)")
    try:
        return fn(rel).decode("utf-8", "replace")
    except FileNotFoundError:
        return None


def sql(dev, db: str, q: str, params: tuple = ()) -> list[dict]:
    return dev.sql(db, q, params) or []


def sql_until(dev, db: str, q: str, params: tuple, pred, rounds: int = 8) -> list[dict]:
    """Re-read until pred(rows) holds or rounds run out; apps often write in the
    background (WorkManager, coroutines) after a tap. Waits with dev.wait_idle only.
    Returns the last rows read, so a check still sees the final state if pred never holds."""
    rows = sql(dev, db, q, params)
    for _ in range(rounds):
        if pred(rows):
            return rows
        dev.wait_idle()
        rows = sql(dev, db, q, params)
    return rows


# ---------- result ----------
def run(fn, dev, p: dict, tier: str) -> CheckResult:
    try:
        ok, observed = fn(dev, p)
    except StepMissing as e:
        return CheckResult(passed=False, observed={"step_missing": str(e)}, tier=tier)
    return CheckResult(passed=bool(ok), observed=observed, tier=tier)
