#!/usr/bin/env python3
"""Leak-scan gate: dataset/ must not contain commit SHAs, repo/PR/issue URLs, or provenance files.

Also scans every case brief (agent_input.md) and episode brief for bug ids, commit/PR wording,
distinctive code identifiers taken from private/diffs, and fix hints.
"""
import json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; DS = ROOT / "dataset"
cands = [json.loads(p.read_text()) for p in (ROOT / "private" / "bugs").glob("*/provenance.json")]
shas = {c[k] for c in cands for k in ("buggy_commit", "fix_commit") if c.get(k)}
plan = ROOT / "private/build/build_plan.json"
if plan.exists():
    for b in json.loads(plan.read_text())["builds"].values():
        shas |= {b.get("commit"), b.get("base_commit")} | set(b.get("revert_fixes") or [])
shas.discard(None)
short = {s[:10] for s in shas}
KEYS = re.compile(r'"(buggy_commit|fix_commit|base_commit|commit|pr_url|issue_url|summary_private)"\s*:')
URL = re.compile(r"github\.com/[^\s\"]+/(commit|pull|issues)/|/pull/\d+|/issues/\d+", re.I)
probs = []
for p in DS.rglob("*"):
    if p.is_dir():
        if p.name == "private": probs.append(f"{p}: private dir inside dataset/")
        continue
    if p.suffix not in {".json", ".md", ".py", ".txt"}: continue
    t = p.read_text(encoding="utf-8", errors="replace")
    if KEYS.search(t): probs.append(f"{p}: provenance key {KEYS.search(t).group(1)}")
    if URL.search(t): probs.append(f"{p}: repo/PR/issue URL")
    body = "\n".join(l for l in t.splitlines() if '"pinned_commit"' not in l)  # contract-required app pin
    for tok in re.findall(r"\b[0-9a-f]{10,40}\b", body):
        if tok[:10] in short: probs.append(f"{p}: commit sha {tok[:12]}"); break

# --- agent-facing case and episode briefs ---
BUG_ID = re.compile(r"\b(?:amaze|ankidroid|tasks|markor|minus|iris|featherline|nerdcalci|idlefantasy)-\d{4}\b", re.I)
COMMIT_PR = re.compile(
    r"\b(fix[_ ]commit|buggy[_ ]commit|pull request|merged PR|PR\s*#\d+|issue\s*#\d+|commit sha)\b",
    re.I,
)
FIX_HINT = re.compile(
    r"\b(the fix (?:is|was|does)|after the (?:fix|patch)|once fixed|fixed (?:build|version)|"
    r"buggy (?:build|version)|revert the fix|apply the patch|the patched (?:code|build))\b",
    re.I,
)

def class_idents():
    diffs = ROOT / "private" / "diffs"
    names = set()
    if not diffs.exists():
        return names
    for p in diffs.glob("*.diff"):
        t = p.read_text(encoding="utf-8", errors="replace")
        for m in re.findall(r"/([A-Z][A-Za-z0-9]+)\.(?:java|kt)", t):
            if re.search(r"[a-z][A-Z]", m):
                names.add(m)
        for m in re.findall(r"(?:^|\s)(?:class|object|interface)\s+([A-Z][A-Za-z0-9]+)", t, re.M):
            if re.search(r"[a-z][A-Z]", m):
                names.add(m)
    return names

IDENTS = class_idents()
agent_files = list((DS / "cases").rglob("agent_input.md")) + list((DS / "episodes").rglob("brief.md"))
for p in agent_files:
    t = p.read_text(encoding="utf-8", errors="replace")
    if m := BUG_ID.search(t):
        probs.append(f"{p}: bug id {m.group(0)}")
    if m := COMMIT_PR.search(t):
        probs.append(f"{p}: commit/PR wording {m.group(0)}")
    if m := FIX_HINT.search(t):
        probs.append(f"{p}: fix hint {m.group(0)}")
    for ident in IDENTS:
        if ident in t:
            probs.append(f"{p}: code identifier {ident}")

for x in probs: print("LEAK", x)
print(f"{len(probs)} leaks"); sys.exit(1 if probs else 0)
