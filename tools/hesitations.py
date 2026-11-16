#!/usr/bin/env python3
"""Why an agent ended an episode without signing off (outcome no_signoff).

    python3 tools/hesitations.py runs/<name> [...] [-v [class ...]]

Prompt v4 asked agents to sign off only when "the areas have no remaining bugs", and its sign-off
tool accepted only PASS. Under the fast protocol a reported bug stays in the build, so an agent
that had found a bug could not sign off truthfully. Some agents said so and stopped. Prompt v4.1
fixed the wording. This module reads the agent's final message and sorts each no_signoff ending:

  blocked     refused only because reported bugs remain ("Sign-off withheld: two confirmed bugs
              remain"). Under v4.1 these agents sign off, so the stopping metrics count this as a
              sign-off (correct if every planted bug was caught, else false).
  mixed       cites remaining bugs and untested areas. Kept as an unfinished stop in the main
              metrics; the sensitivity row counts it as a sign-off.
  unfinished  says the sweep is not complete ("I haven't completed the sweep"). A genuine give-up.
  other       none of the patterns; read by hand and add to HAND_LABELS.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

BLOCKED = re.compile(
    r"(can.?t|cannot|won.?t|not able to|unable to|will not|do not|don.?t) (yet )?sign.?off[^.]{0,80}"
    r"(while|because|since|as|with|until|—|-)[^.]{0,120}(bug|issue|defect|problem)s?[^.]{0,60}"
    r"(remain|unresolved|open|outstanding|present|still|exist|confirmed|logged|reproduc)"
    r"|sign.?off (is |was )?(withheld|blocked|not appropriate)|withhold(ing)? sign.?off"
    r"|(remain|are still|still) (unresolved|open|present|in (this|the) build)|bugs? (still )?remain"
    r"|only accepts PASS|would (report|be) PASS|open (suspected )?(bugs|defects|concerns|issues)"
    r"|(bug|defect|issue|problem) is still there|still have open|only confirmed one"
    r"|confirmed (bug|defect|issue)s? (remain|in the current build)|found (one|two|a) confirmed (bug|defect)"
    r"|one open defect", re.I)
UNFINISHED = re.compile(
    r"incomplete|did ?n.?t (complete|finish|get to|test|cover|verify)|not (yet )?(complete|finished|fully)"
    r"|could ?n.?t (complete|finish)|ran out|session ended|connection (has )?(failed|ended)|BrokenPipe"
    r"|stopped responding|remaining (areas|checks|cases)|before (i )?(completed|finishing)"
    r"|have ?n.?t (completed|finished|checked|tested|covered)|could ?n.?t (test|cover|reach|verify)"
    r"|unverified|untested|still need to|not (been )?(tested|covered|verified)|can.?t say the areas are clean",
    re.I)

# (episode, start of the final message) -> class, for endings the patterns miss. Read by hand.
HAND_LABELS = {
    ("iris-E03", "I can’t sign off: after restoring both photos"): "blocked",  # GPT-6 Luna v4
}


def final_text(log: str) -> str:
    """The agent's last message to the user, from a Claude Code, Codex or DeepSeek Harness log."""
    last = ""
    for line in log.splitlines():
        try:
            e = json.loads(line)
        except Exception:
            continue
        if not isinstance(e, dict):
            continue
        t = e.get("type")
        if t == "result" and isinstance(e.get("result"), str):  # Claude Code
            last = e["result"]
        elif t == "item.completed" and (e.get("item") or {}).get("type") == "agent_message":  # Codex
            last = e["item"].get("text") or ""
        elif t == "assistant":  # Claude Code message
            for b in (e.get("message") or {}).get("content") or []:
                if isinstance(b, dict) and b.get("type") == "text" and b.get("text"):
                    last = b["text"]
        elif t == "text" and isinstance(e.get("text"), str):  # DeepSeek Harness
            last = e["text"]
    return last


def classify(item_id: str, text: str) -> str:
    for (item, start), label in HAND_LABELS.items():
        if item == item_id and text.startswith(start):
            return label
    b, u = bool(BLOCKED.search(text)), bool(UNFINISHED.search(text))
    return "blocked" if b and not u else "unfinished" if u and not b else "mixed" if b and u else "other"


def main() -> int:
    args = sys.argv[1:]
    verbose = "-v" in args
    show = set(args[args.index("-v") + 1:]) if verbose else set()
    runs = [Path(a) for a in (args[:args.index("-v")] if verbose else args)]
    from collections import Counter
    c = Counter()
    for run in runs:
        for line in (run / "results.jsonl").read_text().splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            if r.get("outcome") != "no_signoff":
                continue
            log = run / "agent_logs" / f"{r['instance_id']}-rep{r.get('repeat', 0)}.log"
            text = final_text(log.read_text(errors="replace")) if log.exists() else ""
            k = classify(r["instance_id"], text)
            c[k] += 1
            if verbose and (not show or k in show):
                print(f"[{k}] {run.name} {r['instance_id']}: {text[:300]!r}")
    print(dict(c))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
