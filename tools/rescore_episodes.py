#!/usr/bin/env python3
"""Re-grade finished episode runs with the current match keys and quote rules.

    python3 tools/rescore_episodes.py runs/<name> [runs/<name2> ...] [--check] [--write]

Fast-protocol episodes keep every planted bug present for the whole session, so the agent's
reports can be replayed in order through the same classify_report() the harness uses. The
harness did not store the set of screen texts it showed; it is rebuilt from the agent's
transcript (agent_logs/<episode>-rep<k>.log), which holds every observation the agent got:
element texts, descriptions and `contains "A" | "B"` rows, up to the moment of each report.
A quote the original run accepted stays accepted (the harness saw at least as much text as the
transcript shows: the observation lists at most MAX_ELEMENTS nodes).

--check   replay with the quote flags the run recorded (no transcript rebuild) and report any
          episode whose replay differs from the stored result; with unchanged keys this must
          print no differences. Results already rescored from the transcript (they carry a
          "rescored" field) cannot be replayed from the recorded flags and are skipped.
--write   save the rescored fields into result.json (the first rescore keeps the original as
          result.pre_rescore.json). Without --write, only print what would change.
"""
from __future__ import annotations

import argparse
import glob
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dataset_tools.matcher import load_key  # noqa: E402
from tools.eval_lib import _norm_text, classify_report, quote_usable  # noqa: E402

DATASET = ROOT / "dataset"
JSTR = re.compile(r'"(?:[^"\\]|\\.)*"')


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


def agent_log(run: Path, item: str, run_id: str, reps: dict) -> Path | None:
    """The transcript of this result's own repeat; falls back to the only log when there is one."""
    if run_id in reps:
        f = run / "agent_logs" / f"{item}-rep{reps[run_id]}.log"
        if f.exists():
            return f
    logs = sorted(glob.glob(str(run / "agent_logs" / f"{item}-rep*.log")))
    return Path(logs[0]) if len(logs) == 1 else None


def _texts_of_line(line: str) -> tuple[list[str], list[str]]:
    """(single texts, row parts) of one rendered element line: [i] Class "text" desc="d" contains "A" | "B" ..."""
    head, _, rest = line.partition(" contains ")
    singles = [json.loads(s) for s in JSTR.findall(head)]
    parts = [json.loads(s) for s in JSTR.findall(rest.split(" id=")[0])] if rest else []
    return singles, parts


def seen_before_each_report(log: Path) -> list[set[str]]:
    """For each file_report call in the transcript, the normalised texts shown before it.

    Reads the three transcript formats: Claude Code stream-json, Codex --json (mcp_tool_call items)
    and DeepSeek Harness (tool_call / tool_result events)."""
    seen: set[str] = set()
    out: list[set[str]] = []

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

    def shown(text: str) -> None:
        for line in text.splitlines():
            if not line.startswith("["):
                continue
            try:
                singles, parts = _texts_of_line(line)
            except Exception:
                continue
            seen.update(_norm_text(s) for s in singles + parts if s)
            if len(parts) > 1:
                p = [_norm_text(x) for x in parts]
                seen.add(" | ".join(p))
                seen.add(" ".join(p))

    for raw in log.open(errors="replace"):
        if not raw.startswith("{"):
            continue
        try:
            ev = json.loads(raw)
        except Exception:
            continue
        if not isinstance(ev, dict):
            continue
        t = ev.get("type")
        if t in ("assistant", "user"):  # Claude Code
            msg = ev.get("message")
            blocks = msg.get("content") if isinstance(msg, dict) else None
            for b in blocks if isinstance(blocks, list) else []:
                if not isinstance(b, dict):
                    continue
                if t == "assistant" and b.get("type") == "tool_use" and b.get("name", "").endswith("file_report"):
                    out.append(set(seen))
                if t == "user" and b.get("type") == "tool_result":
                    shown(text_of(b.get("content")))
        elif t in ("item.started", "item.completed"):  # Codex
            it = ev.get("item") or {}
            if it.get("type") != "mcp_tool_call":
                continue
            if t == "item.started" and it.get("tool") == "file_report":
                out.append(set(seen))
            if t == "item.completed":
                shown(text_of(it.get("result") or ""))
        elif t == "tool_call":  # DeepSeek Harness
            if str(ev.get("tool") or ev.get("name") or "").endswith("file_report"):
                out.append(set(seen))
        elif t == "tool_result":
            shown(text_of(ev.get("result")))
    return out


def quote_in(quote: str, seen: set[str]) -> bool:
    q = _norm_text(quote or "")
    q2 = _norm_text(q.removeprefix("contains ").replace('"', ""))
    return any(q in t or (q2 and q2 in t) for t in seen)


def rescore(res_dir: Path, run: Path, check: bool) -> dict | None:
    res = json.loads((res_dir / "result.json").read_text())
    if res.get("kind") != "episode" and "required" not in res:
        return None
    ep_id = res["item_id"]
    episode = json.loads((DATASET / "episodes" / ep_id / "episode.json").read_text())
    if res.get("settings", {}).get("protocol", "fast") != "fast":
        return None
    keys = {b: load_key(DATASET / "bugs" / b) for b in episode["bugs"]}
    reports = [r for r in res.get("verdicts_or_reports") or [] if isinstance(r, dict) and r.get("type") == "bug_report"]
    cap = (res.get("settings") or {}).get("max_reports")
    if cap:  # a report past the report limit ends the episode unscored
        reports = reports[:cap]
    trace = [json.loads(l) for l in (res_dir / "trace.jsonl").open() if l.strip()]
    recorded = {e["report_n"]: e.get("quote_seen") for e in trace if e.get("event") == "scored"}
    log = agent_log(run, ep_id, res["run_id"], repeat_of(run))
    seen_at = seen_before_each_report(log) if log and not check else []
    if seen_at and len(seen_at) != len(reports):
        # the transcript and the stored reports disagree: keep the recorded quote flags only
        # (reusing the last screen set would accept quotes first shown after a report)
        seen_at = []
    # the harness's unfixed set includes masked bugs (amaze-0005): a report that matches only a
    # masked bug is a false report there, so the replay must see the same set
    builds = res.get("builds_installed") or []
    unfixed = set(builds[0].get("unfixed") or []) if builds else set()
    unfixed = unfixed or set(res.get("required") or episode["bugs"])
    required = set(res.get("required") or unfixed)
    found: list[str] = []
    tp = fp = dup = 0
    kinds = []
    for i, rep in enumerate(reports, 1):
        a = dict(rep)
        q = rep.get("observed_quote")
        old = recorded.get(i)
        if q and quote_usable(q):  # an unusable quote ("- ") counts as no quote, as in the harness
            if check:
                a["_quote_seen"] = old
            else:
                a["_quote_seen"] = bool(old) or (bool(seen_at) and quote_in(q, seen_at[i - 1]))
        r = classify_report(a, episode, unfixed, keys, None, found)
        kind = r.get("kind") or "no_match"
        hit = [b for b in (r.get("bugs") or []) if b in required]
        if kind == "hit" and hit:
            new = [b for b in hit if b not in found]
            if new:
                tp += 1
                found += new
                kinds.append("hit")
            else:
                dup += 1
                kinds.append("duplicate")
        elif kind in ("no_match", "vague", "spray", "malformed"):
            fp += 1
            kinds.append(kind)
        else:
            kinds.append(kind)
    req = set(res.get("required") or [])
    signed = (res.get("sign_off") or {}).get("verdict") == "PASS"
    all_found = req <= set(found)
    outcome = res.get("outcome")
    if any(e.get("event") == "limit" and e.get("which") == "reports" for e in trace):
        outcome = "report_cap"  # ended by the report limit, not the action cap
    if outcome in ("success", "wrong_pass") and signed:
        outcome = "success" if all_found else "wrong_pass"
    return {"dir": res_dir, "res": res, "found": sorted(found), "true_positives": tp, "false_positives": fp,
            "duplicates": dup, "outcome": outcome, "success": outcome == "success", "kinds": kinds}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", nargs="+", type=Path)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    for run in a.runs:
        changed = skipped = 0
        for rf in sorted(glob.glob(str(run / "episodes" / "*" / "*" / "result.json"))):
            if a.check and "rescored" in json.loads(Path(rf).read_text()):
                skipped += 1  # its quote flags came from the transcript, not the harness
                continue
            out = rescore(Path(rf).parent, run, a.check)
            if not out:
                continue
            res = out["res"]
            before = (sorted(res.get("found") or []), res.get("true_positives"), res.get("false_positives"), res.get("outcome"))
            after = (out["found"], out["true_positives"], out["false_positives"], out["outcome"])
            if before != after:
                changed += 1
                print(f"{run.name:16} {res['item_id']:16} found {before[0]} -> {after[0]}  tp {before[1]}->{after[1]}  "
                      f"fp {before[2]}->{after[2]}  {before[3]}->{after[3]}")
                if a.write and not a.check:
                    d = out["dir"]
                    orig = d / "result.pre_rescore.json"
                    if not orig.exists():
                        orig.write_text((d / "result.json").read_text())
                    for k in ("found", "true_positives", "false_positives", "outcome", "success"):
                        res[k] = out[k]
                    res["missed"] = sorted(set(res.get("required") or []) - set(out["found"]))
                    res["rescored"] = {"tool": "tools/rescore_episodes.py", "report_kinds": out["kinds"]}
                    (d / "result.json").write_text(json.dumps(res, indent=2) + "\n")
        note = f" ({skipped} transcript-rescored skipped)" if a.check else ""
        print(f"{run}: {changed} episode(s) {'differ' if a.check else 'change'}{note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
