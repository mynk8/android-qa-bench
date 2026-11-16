#!/usr/bin/env python3
"""Changelog coverage: did the agent regression-test each "Changed in this build" line?

    python3 tools/changelog_coverage.py runs/<name> [runs/<name2> ...] [--detail]

Every release-note line (real or decoy) is a test duty. Per line, from the agent's transcript
(what the device tools showed it, action by action):

  reached   the feature was on screen at least once: one observation contains the line's
            feature words (2 of them when the line has 2 or more)
  worked    the agent spent at least WORK_MIN actions with the feature on screen
            (a one-pass look is below this; repeat / reverse / revisit is above)
  caught    real lines only: the planted bug behind the line was credited

So a miss splits into: ignored the note (not reached), shallow (reached, not worked), or
tested and not noticed (worked, not caught). Decoys measure the same duty on harmless
changes, so an agent that only digs where it already found something shows up.

A line is on screen when one observation contains any of its screen anchors
(private/release_notes/screen_anchors.json: exact UI strings of that feature, e.g. a dialog's
title or buttons, verified against real observations). Lines without anchors fall back to the
line's own feature words (2 of them). Deterministic; no model involved.
"""
from __future__ import annotations

import argparse
import collections
import glob
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NOTES = ROOT / "private" / "release_notes" / "notes.json"
ANCHORS = ROOT / "private" / "release_notes" / "screen_anchors.json"
WORK_MIN = 6

GENERIC = set("""
the a an of to in on for and or with its into at by from was were got new this that each
updated reworked redesigned refreshed restyled reorganised rearranged
screen screens section dialog menu list layout view options option settings prompt panel header
bar button buttons picker sheet tab tabs area page item items row rows entry entries control controls
""".split())


def repeat_of(run: Path) -> dict:
    """run_id -> repeat index, from runs/<name>/results.jsonl (agent logs are <item>-rep<i>.log)."""
    out = {}
    p = run / "results.jsonl"
    if p.exists():
        for line in p.read_text().splitlines():
            if line.strip():
                q = json.loads(line)
                out[q["run_id"]] = q["repeat"]
    return out


def scored_run_ids(run: Path) -> set | None:
    """run_ids of each episode's latest result that is not an infrastructure error (a re-run with
    --resume adds a new row; the errored attempt stays in results.jsonl). None without results.jsonl."""
    p = run / "results.jsonl"
    if not p.exists():
        return None
    last = {}
    for line in p.read_text().splitlines():
        if line.strip():
            q = json.loads(line)
            last[(q["instance_id"], q.get("repeat", 0))] = q
    return {q["run_id"] for q in last.values() if q.get("outcome") != "error"}


def agent_log(run: Path, item: str, run_id: str, reps: dict) -> Path | None:
    """The transcript of this result's own repeat; falls back to the only log when there is one."""
    if run_id in reps:
        f = run / "agent_logs" / f"{item}-rep{reps[run_id]}.log"
        if f.exists():
            return f
    logs = sorted(glob.glob(str(run / "agent_logs" / f"{item}-rep*.log")))
    return Path(logs[0]) if len(logs) == 1 else None


def words(line: str) -> list[str]:
    toks = re.findall(r"[a-z0-9_%+]+", line.lower().replace("'s", ""))
    out = []
    for t in toks:
        t = t.rstrip("s") if len(t) > 4 and t.endswith("s") and not t.endswith("ss") else t
        if t not in GENERIC and len(t) >= 3 and t not in out:
            out.append(t)
    return out


def observations(log: Path) -> list[str]:
    """Text of every device-tool result, in order (one per agent action).

    Reads the three agent log formats: Claude Code stream-json (user tool_result blocks), Codex
    --json (item.completed mcp_tool_call items) and DeepSeek Harness (tool_result events)."""
    def text_of(c) -> str:
        if isinstance(c, str):
            return c
        if isinstance(c, dict):
            c = c.get("content", c.get("text", ""))
            if isinstance(c, str):
                return c
        if isinstance(c, list):
            return " ".join(x.get("text", "") for x in c if isinstance(x, dict) and x.get("type") == "text")
        return ""

    out = []
    for line in log.open(errors="replace"):
        if not line.startswith("{"):
            continue
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if not isinstance(e, dict):
            continue
        t = e.get("type")
        if t == "user":  # Claude Code
            for b in (e.get("message") or {}).get("content") or []:
                if isinstance(b, dict) and b.get("type") == "tool_result":
                    out.append(text_of(b.get("content")).lower())
        elif t == "item.completed":  # Codex
            it = e.get("item") or {}
            if it.get("type") == "mcp_tool_call" and it.get("server", "device") == "device":
                out.append(text_of(it.get("result") or "").lower())
        elif t == "tool_result":  # DeepSeek Harness
            out.append(text_of(e.get("result")).lower())
    return out


def on_screen(obs: str, ws: list[str]) -> bool:
    need = 2 if len(ws) >= 2 else 1
    return sum(1 for w in ws if w in obs) >= need


def line_matcher(ep: str, line: str, anchors: dict):
    a = [x.lower() for x in ((anchors.get(ep) or {}).get(line) or {}).get("anchors") or []]
    if a:
        return (lambda o: any(x in o for x in a)), a
    ws = words(line)
    return (lambda o: on_screen(o, ws)), ws


def episode_lines(run: Path, notes: dict, anchors: dict | None = None):
    anchors = anchors or {}
    reps = repeat_of(run)
    keep = scored_run_ids(run)
    for res_f in sorted(glob.glob(str(run / "episodes" / "*" / "*" / "result.json"))):
        res = json.loads(Path(res_f).read_text())
        ep = res["item_id"]
        if ep not in notes or (reps and res["run_id"] not in reps) or (keep is not None and res["run_id"] not in keep):
            continue
        log = agent_log(run, ep, res["run_id"], reps)
        if not log:
            continue
        obs = observations(log)
        found = set(res.get("found") or [])
        real = {line: bug for bug, line in notes[ep]["real"].items()}
        for line in notes[ep]["lines"]:
            match, ws = line_matcher(ep, line, anchors)
            hits = sum(1 for o in obs if match(o))
            kind = "real" if line in real else "decoy"
            caught = kind == "real" and real[line] in found
            yield {"episode": ep, "line": line, "kind": kind, "words": ws, "actions_on_screen": hits,
                   "reached": hits > 0, "worked": hits >= WORK_MIN, "caught": caught}


def summarize(rows: list[dict]) -> dict:
    out = {}
    for kind in ("real", "decoy"):
        rs = [r for r in rows if r["kind"] == kind]
        n = len(rs)
        if not n:
            continue
        s = {"lines": n, "reached": sum(r["reached"] for r in rs), "worked": sum(r["worked"] for r in rs)}
        if kind == "real":
            s["caught"] = sum(r["caught"] for r in rs)
            s["miss_ignored"] = sum(1 for r in rs if not r["caught"] and not r["reached"])
            s["miss_shallow"] = sum(1 for r in rs if not r["caught"] and r["reached"] and not r["worked"])
            s["miss_tested_not_noticed"] = sum(1 for r in rs if not r["caught"] and r["worked"])
        out[kind] = s
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", nargs="+", type=Path)
    ap.add_argument("--detail", action="store_true")
    a = ap.parse_args()
    notes = json.loads(NOTES.read_text())
    anchors = json.loads(ANCHORS.read_text()) if ANCHORS.exists() else {}
    rows = [r for run in a.runs for r in episode_lines(run, notes, anchors)]
    s = summarize(rows)
    pct = lambda k, n: f"{k}/{n} ({100 * k // n}%)" if n else "-"
    print(f"Changelog coverage ({', '.join(map(str, a.runs))}; worked = {WORK_MIN}+ actions on the feature)")
    print("| lines | reached | worked | caught |")
    print("|---|---|---|---|")
    for kind, v in s.items():
        print(f"| {kind} ({v['lines']}) | {pct(v['reached'], v['lines'])} | {pct(v['worked'], v['lines'])} | "
              f"{pct(v['caught'], v['lines']) if kind == 'real' else '-'} |")
    if "real" in s:
        r = s["real"]
        print(f"\nReal-line misses: ignored {r['miss_ignored']}, shallow {r['miss_shallow']}, "
              f"tested but not noticed {r['miss_tested_not_noticed']}")
    if a.detail:
        for r in rows:
            print(f"  {r['episode']:16} {r['kind']:5} on-screen {r['actions_on_screen']:3}  "
                  f"{'CAUGHT' if r['caught'] else '':6} {r['line']}  {r['words']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
