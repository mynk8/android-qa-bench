#!/usr/bin/env python3
"""Extract one Claude Code episode transcript as a timeline: every action, the agent's text, the
screenshots it was shown (saved as PNG), its reports and the developer's replies.

    python3 docs/paper/figures/extract_liveview.py runs/eps-v4-sonnet tasks-E05
"""
import base64, json, sys
from pathlib import Path

run, ep = Path(sys.argv[1]), sys.argv[2]
out = Path(__file__).resolve().parent / "live" / ep
out.mkdir(parents=True, exist_ok=True)
log = run / "agent_logs" / f"{ep}-rep0.log"
steps, n, pending = [], 0, {}
for line in log.open(errors="replace"):
    if not line.startswith("{"):
        continue
    e = json.loads(line)
    if e.get("type") == "assistant":
        for b in e["message"].get("content") or []:
            if b.get("type") == "text" and b["text"].strip():
                steps.append({"kind": "say", "after": n, "text": b["text"].strip()})
            elif b.get("type") == "tool_use":
                n += 1
                s = {"kind": "act", "n": n, "tool": b["name"].split("__")[-1], "input": b.get("input")}
                pending[b["id"]] = s
                steps.append(s)
    elif e.get("type") == "user":
        for b in e["message"].get("content") or []:
            if b.get("type") != "tool_result":
                continue
            s = pending.get(b.get("tool_use_id"))
            if s is None:
                continue
            c = b.get("content")
            parts = c if isinstance(c, list) else [{"type": "text", "text": str(c)}]
            s["result"] = " ".join(p.get("text", "") for p in parts if p.get("type") == "text")[:4000]
            for p in parts:
                if p.get("type") == "image":
                    f = out / f"step{s['n']:03d}.png"
                    f.write_bytes(base64.b64decode(p["source"]["data"]))
                    s["image"] = f.name
json.dump(steps, open(out / "timeline.json", "w"), indent=1)
print(f"{n} actions, {sum(1 for s in steps if s.get('image'))} screenshots -> {out}")
