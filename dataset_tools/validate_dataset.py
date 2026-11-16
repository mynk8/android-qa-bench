#!/usr/bin/env python3
"""Validate a dataset delivery against contract v1 (Parts 2 and 3 of BOT_BRIEF.md).

Usage:
  python dataset_tools/validate_dataset.py dataset/                 # structure, schemas, leaks
  python dataset_tools/validate_dataset.py dataset/ --hashes        # also verify APK sha256
  python dataset_tools/validate_dataset.py dataset/ --calibrate my_sandbox:AdbDevice --runs 3
      # re-run every bug's checks on its buggy/fixed builds using your Device implementation

Exit code 0 = accepted, 1 = errors found. Standard library only.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import importlib
import importlib.util
import itertools
import json
import re
import sys
from pathlib import Path

ID_RE = re.compile(r"^[a-z0-9_-]+$")
SOURCES = {"appeval", "mature_pr", "greenfield_pr", "agent_built", "seeded"}
FAMILIES = {"state", "display", "interaction"}
SYMPTOMS = {"wrong_value", "missing", "not_persisted", "cut_off", "wrong_navigation", "no_effect",
            "duplicated", "overlap"}
TASK_STATUS = {"todo", "in_progress", "done", "blocked", "dropped"}
INTERACTIONS = {"independent", "masking", "fix_reveals", "fix_regresses"}
VARIANT_TRUTH = {"faulty": "FAIL", "clean": "PASS", "partial_fix": "FAIL"}
CASE_SECTIONS = ["## Context", "## Preconditions", "## Steps", "## Rules", "## Answer format"]
BRIEF_SECTIONS = ["## Preconditions", "## How this works", "## Report format", "## Sign-off format"]
LEAK_PATTERNS = [re.compile(r"github\.com|gitlab\.com|/pull/|/issues/", re.I),
                 re.compile(r"\b[0-9a-f]{40}\b")]


class Report:
    def __init__(self):
        self.errors, self.warnings = [], []

    def err(self, where, msg):
        self.errors.append(f"ERROR   {where}: {msg}")

    def warn(self, where, msg):
        self.warnings.append(f"WARN    {where}: {msg}")


def load_json(path: Path, rep: Report):
    if not path.exists():
        rep.err(str(path), "missing")
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        rep.err(str(path), f"invalid JSON: {e}")
        return None


def need(obj, keys, where, rep):
    ok = True
    for k in keys:
        if k not in obj:
            rep.err(where, f"missing key '{k}'")
            ok = False
    return ok


def defines_function(py: Path, name: str) -> bool:
    try:
        tree = ast.parse(py.read_text(encoding="utf-8"))
    except SyntaxError:
        return False
    return any(isinstance(n, ast.FunctionDef) and n.name == name for n in tree.body)


def checks_shape(py: Path, rep: Report, where: str):
    """checks.py must define CHECKS = {"target": fn, "held_out": [fn,...], "preservation": [fn,...]}."""
    try:
        tree = ast.parse(py.read_text(encoding="utf-8"))
    except SyntaxError as e:
        rep.err(where, f"checks.py syntax error: {e}")
        return
    funcs = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}
    checks = None
    for n in tree.body:
        if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "CHECKS" for t in n.targets):
            checks = n.value
    if not isinstance(checks, ast.Dict):
        rep.err(where, "checks.py has no CHECKS dict")
        return
    entries = {k.value: v for k, v in zip(checks.keys, checks.values) if isinstance(k, ast.Constant)}
    if not isinstance(entries.get("target"), ast.Name) or entries["target"].id not in funcs:
        rep.err(where, "CHECKS['target'] must name one function defined in checks.py")
    for key in ("held_out", "preservation"):
        v = entries.get(key)
        if not isinstance(v, ast.List) or not v.elts:
            rep.err(where, f"CHECKS['{key}'] must be a non-empty list")
            continue
        for e in v.elts:
            if not isinstance(e, ast.Name) or e.id not in funcs:
                rep.err(where, f"CHECKS['{key}'] entry is not a function defined in checks.py")


def leak_check(text: str, forbidden: list[str], where: str, rep: Report):
    low = text.lower()
    for token in forbidden:
        if token and token.lower() in low:
            rep.err(where, f"agent-facing text contains private token '{token}'")
    for pat in LEAK_PATTERNS:
        if pat.search(text):
            rep.err(where, f"agent-facing text matches leak pattern {pat.pattern}")


def validate(root: Path, verify_hashes: bool) -> tuple[Report, dict]:
    rep = Report()
    man = load_json(root / "manifest.json", rep) or {}
    if man and man.get("contract") != "v1":
        rep.err("manifest.json", "contract must be 'v1'")
    need(man, ["contract", "emulator", "apps", "bugs", "episodes"], "manifest.json", rep)

    apps, bugs, builds_by_app = {}, {}, {}
    private_tokens: list[str] = []

    # ---- apps
    for app_id in man.get("apps", []):
        d = root / "apps" / app_id
        where = f"apps/{app_id}"
        if not ID_RE.match(app_id):
            rep.err(where, "bad id")
        a = load_json(d / "app.json", rep)
        if a:
            need(a, ["app_id", "repo", "licence", "package", "pinned_commit", "source_type"], where, rep)
            apps[app_id] = a
        idx = load_json(d / "builds" / "index.json", rep) or {}
        builds_by_app[app_id] = idx
        for bid, meta in idx.items():
            private_tokens.append(bid)
            if not need(meta, ["sha256", "bugs_present", "kind"], f"{where}/builds/{bid}", rep):
                continue
            apk = d / "builds" / f"{bid}.apk"
            if not apk.exists():
                rep.err(f"{where}/builds", f"{bid}.apk missing")
            elif verify_hashes and hashlib.sha256(apk.read_bytes()).hexdigest() != meta["sha256"]:
                rep.err(f"{where}/builds", f"{bid}.apk sha256 mismatch")
        if not (d / "seed.py").exists() or not defines_function(d / "seed.py", "apply"):
            rep.err(where, "seed.py must define apply(dev, seed)")
        t = load_json(d / "tasks.json", rep)
        if t:
            for task in t.get("tasks", []):
                if task.get("status") not in TASK_STATUS:
                    rep.err(f"{where}/tasks.json", f"bad status for {task.get('id')}")
            open_tasks = [x["id"] for x in t.get("tasks", []) if x.get("status") in ("todo", "in_progress", "blocked")]
            if open_tasks:
                rep.warn(where, f"open tasks: {', '.join(open_tasks)}")

    # ---- bugs
    for bug_id in man.get("bugs", []):
        d = root / "bugs" / bug_id
        where = f"bugs/{bug_id}"
        private_tokens.append(bug_id)
        b = load_json(d / "bug.json", rep)
        if not b:
            continue
        need(b, ["bug_id", "app_id", "source", "family", "fix_date", "seed_id", "builds", "calibration", "status"],
             where, rep)
        bugs[bug_id] = b
        if b.get("source") not in SOURCES:
            rep.err(where, f"source must be one of {sorted(SOURCES)}")
        if b.get("family") not in FAMILIES:
            rep.err(where, f"family must be one of {sorted(FAMILIES)}")
        app_builds = builds_by_app.get(b.get("app_id"), {})
        for role in ("buggy", "fixed"):
            bid = b.get("builds", {}).get(role)
            if bid not in app_builds:
                rep.err(where, f"builds.{role} '{bid}' not in app build index")
        cal = b.get("calibration", {})
        exp = {"buggy": (False, False, True), "fixed": (True, True, True)}
        for role, (t_ok, h_ok, p_ok) in exp.items():
            c = cal.get(role, {})
            if c.get("target") is not t_ok or any(x is not h_ok for x in c.get("held_out", [None])) \
                    or any(x is not p_ok for x in c.get("preservation", [None])):
                rep.err(where, f"calibration on {role} build does not match the gate")
        if cal.get("runs", 0) < 3:
            rep.err(where, "calibration.runs must be >= 3")
        for f in ("repro.py", "checks.py", "match.json", "reference_reports.json"):
            if not (d / f).exists():
                rep.err(where, f"{f} missing")
        if (d / "repro.py").exists() and not defines_function(d / "repro.py", "run"):
            rep.err(where, "repro.py must define run(dev)")
        if (d / "checks.py").exists():
            checks_shape(d / "checks.py", rep, where)
        m = load_json(d / "match.json", rep) if (d / "match.json").exists() else None
        if m:
            need(m, ["screens", "symptom_type"], f"{where}/match.json", rep)
            if not (m.get("elements") or m.get("fields")):
                rep.err(f"{where}/match.json", "needs elements or fields")
            if m.get("symptom_type") not in SYMPTOMS:
                rep.err(f"{where}/match.json", f"symptom_type must be one of {sorted(SYMPTOMS)}")
        r = load_json(d / "reference_reports.json", rep) if (d / "reference_reports.json").exists() else None
        if r:
            need(r, ["correct", "vague", "wrong_bug"], f"{where}/reference_reports.json", rep)
        if not (d / "private").is_dir():
            rep.warn(where, "private/ folder missing (issue/PR provenance)")

    # ---- cases
    case_dir = root / "cases"
    pairs: dict[tuple, dict] = {}
    for d in sorted(case_dir.iterdir()) if case_dir.exists() else []:
        where = f"cases/{d.name}"
        c = load_json(d / "case.json", rep)
        if not c:
            continue
        need(c, ["case_id", "bug_id", "_build_id", "_true_verdict", "_variant", "_conditions", "seed_id"], where, rep)
        b = bugs.get(c.get("bug_id"))
        if not b:
            rep.err(where, f"unknown bug_id {c.get('bug_id')}")
            continue
        if c.get("_build_id") not in builds_by_app.get(b["app_id"], {}):
            rep.err(where, "build not in app build index")
        if VARIANT_TRUTH.get(c.get("_variant")) != c.get("_true_verdict"):
            rep.err(where, "_true_verdict inconsistent with _variant")
        ai = d / "agent_input.md"
        if not ai.exists():
            rep.err(where, "agent_input.md missing")
            continue
        text = ai.read_text(encoding="utf-8")
        for s in CASE_SECTIONS:
            if s not in text:
                rep.err(where, f"agent_input.md missing section '{s}'")
        spec = c.get("_conditions", {}).get("instruction")
        if (spec == "specified") != ("## Expected results" in text):
            rep.err(where, "'Expected results' section must be present iff instruction == specified")
        leak_check(text, private_tokens, where, rep)
        key = (c.get("bug_id"), json.dumps(c.get("_conditions", {}), sort_keys=True))
        pairs.setdefault(key, {})[c.get("_variant")] = text
    for (bug_id, cond), variants in pairs.items():
        if "faulty" in variants and "clean" in variants and variants["faulty"] != variants["clean"]:
            rep.err(f"cases[{bug_id}]", "clean and faulty agent_input.md differ for the same conditions")
        if "faulty" in variants and "clean" not in variants:
            rep.warn(f"cases[{bug_id}]", f"faulty case without clean pair for conditions {cond}")

    # ---- episodes
    for ep_id in man.get("episodes", []):
        d = root / "episodes" / ep_id
        where = f"episodes/{ep_id}"
        e = load_json(d / "episode.json", rep)
        if not e:
            continue
        need(e, ["episode_id", "app_id", "bugs", "seed_id", "builds", "observable", "interactions", "status"],
             where, rep)
        ebugs = e.get("bugs", [])
        if not 1 <= len(ebugs) <= 4:  # single-bug episodes are part of the released design
            rep.warn(where, f"{len(ebugs)} bugs (expected 1-4)")
        for bid in ebugs:
            if bid not in bugs:
                rep.err(where, f"unknown bug {bid}")
            elif bugs[bid]["app_id"] != e.get("app_id"):
                rep.err(where, f"bug {bid} belongs to another app")
        app_builds = builds_by_app.get(e.get("app_id"), {})
        subsets = ["".join(bits) for bits in itertools.product("01", repeat=len(ebugs))]
        for s in subsets:
            bid = e.get("builds", {}).get(s)
            if bid not in app_builds:
                rep.err(where, f"subset {s}: build '{bid}' missing from app index")
                continue
            present = {x for x, bit in zip(ebugs, s) if bit == "1"}
            if set(app_builds[bid].get("bugs_present", [])) != present:
                rep.err(where, f"subset {s}: build bugs_present does not match bits")
            if s not in e.get("observable", {}):
                rep.err(where, f"subset {s}: observable entry missing")
        for it in e.get("interactions", []):
            if it.get("type") not in INTERACTIONS:
                rep.err(where, f"interaction type must be one of {sorted(INTERACTIONS)}")
        br = d / "brief.md"
        if not br.exists():
            rep.err(where, "brief.md missing")
        else:
            text = br.read_text(encoding="utf-8")
            for s in BRIEF_SECTIONS:
                if s not in text:
                    rep.err(where, f"brief.md missing section '{s}'")
            leak_check(text, private_tokens, where, rep)

    return rep, {"apps": apps, "bugs": bugs, "builds": builds_by_app}


def calibrate(root: Path, ctx: dict, device_spec: str, runs: int, rep: Report):
    """Re-run each bug's checks on buggy and fixed builds with the user's Device implementation."""
    mod_name, cls_name = device_spec.split(":")
    sys.path.insert(0, str(Path.cwd()))
    dev = getattr(importlib.import_module(mod_name), cls_name)()
    for bug_id, b in ctx["bugs"].items():
        spec = importlib.util.spec_from_file_location(f"checks_{bug_id}", root / "bugs" / bug_id / "checks.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        seed_spec = importlib.util.spec_from_file_location(f"seed_{b['app_id']}", root / "apps" / b["app_id"] / "seed.py")
        seed_mod = importlib.util.module_from_spec(seed_spec)
        seed_spec.loader.exec_module(seed_mod)
        seed = json.loads((root / "apps" / b["app_id"] / "seed" / f"{b['seed_id']}.json").read_text())
        for role, want in (("buggy", (False, False, True)), ("fixed", (True, True, True))):
            for _ in range(runs):
                dev.install(b["builds"][role])
                seed_mod.apply(dev, seed)
                params = b.get("params", {})
                got = (mod.CHECKS["target"](dev, params).passed,
                       all(f(dev, params).passed is want[1] for f in mod.CHECKS["held_out"]),
                       all(f(dev, params).passed is want[2] for f in mod.CHECKS["preservation"]))
                if (got[0] is not want[0]) or not got[1] or not got[2]:
                    rep.err(f"bugs/{bug_id}", f"calibration failed in sandbox on {role} build")
                    break


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path)
    ap.add_argument("--hashes", action="store_true")
    ap.add_argument("--calibrate", metavar="module:Class")
    ap.add_argument("--runs", type=int, default=3)
    args = ap.parse_args()
    rep, ctx = validate(args.root, args.hashes)
    if args.calibrate and not rep.errors:
        calibrate(args.root, ctx, args.calibrate, args.runs, rep)
    for line in rep.errors + rep.warnings:
        print(line)
    print(f"\n{len(rep.errors)} errors, {len(rep.warnings)} warnings -> "
          f"{'REJECTED' if rep.errors else 'ACCEPTED'}")
    sys.exit(1 if rep.errors else 0)


if __name__ == "__main__":
    main()
