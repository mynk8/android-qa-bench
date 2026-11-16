#!/usr/bin/env python3
"""Export the scored episode runs of each agent configuration into results/<config>/.

    python3 tools/export_results.py

A configuration may have run as several slices (runs/<name>, runs/<name>-b, ...). The export merges
them and keeps, per episode, only the scored attempt (the latest result that is not an
infrastructure error): its row in results.jsonl, its result.json and trace.jsonl, and the part of
the agent transcript that belongs to it. Screenshots inside transcripts are replaced by a
placeholder with their size and SHA-256, so the transcripts stay small; every text the agent saw is
kept. Output layout matches a run directory, so tools/leaderboard.py, tools/changelog_coverage.py
and tools/rescore_episodes.py read results/<config> directly.
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "runs"
OUT = ROOT / "results"

CONFIGS = {
    "claude-sonnet-5.5-medium": ["eps-v4-sonnet"],
    "claude-haiku-5.5": ["eps-v4-haiku"],
    "gpt-6.1-sol-low": ["eps-v4.1-gpt-6.1-sol-low", "eps-v4.1-gpt-6.1-sol-low-b", "eps-v4.1-gpt-6.1-sol-low-c"],
    "gpt-6-luna-medium": ["eps-v4.1-gpt-6-luna-med", "eps-v4.1-gpt-6-luna-med-b", "eps-v4.1-gpt-6-luna-med-c"],
    "gpt-6-luna-max": ["eps-v4.1-gpt-6-luna-max", "eps-v4.1-gpt-6-luna-max-b", "eps-v4.1-gpt-6-luna-max-c"],
    "deepseek-v4.1-flash-high": ["eps-v4-dsh-deepseek-v4.1-flash", "eps-v4-dsh-deepseek-v4.1-flash-b",
                                 "eps-v4-dsh-deepseek-v4.1-flash-c"],
}

# a line that starts one agent session, per harness (Claude Code, Codex CLI, DeepSeek Harness)
START = re.compile(r'^\{"type": ?"(system", ?"subtype": ?"init|thread\.started|session)"')
B64 = re.compile(r"^[A-Za-z0-9+/=\s]{2000,}$")


def strip_images(x):
    if isinstance(x, dict):
        return {k: strip_images(v) for k, v in x.items()}
    if isinstance(x, list):
        return [strip_images(v) for v in x]
    if isinstance(x, str) and len(x) >= 2000 and B64.match(x):
        try:
            raw = base64.b64decode(x, validate=False)
        except ValueError:
            raw = x.encode()
        return f"<image omitted: {len(raw)} bytes, sha256 {hashlib.sha256(raw).hexdigest()[:16]}>"
    return x


def last_session(lines: list[str]) -> list[str]:
    starts = [i for i, l in enumerate(lines) if START.match(l)]
    return lines[starts[-1]:] if starts else lines


def export(name: str, slices: list[str]) -> dict:
    dst = OUT / name
    if dst.exists():
        shutil.rmtree(dst)
    (dst / "episodes").mkdir(parents=True)
    (dst / "agent_logs").mkdir()
    rows, meta = [], None
    for s in slices:
        run = RUNS / s
        meta = meta or json.loads((run / "run.json").read_text())
        last = {}
        for line in (run / "results.jsonl").read_text().splitlines():
            if line.strip():
                q = json.loads(line)
                last[(q["instance_id"], q.get("repeat", 0))] = q
        for (item, rep), q in sorted(last.items()):
            if q["outcome"] == "error":
                raise SystemExit(f"{s}: {item} has no scored attempt")
            rows.append(q)
            src = run / "episodes" / item / q["run_id"]
            ep = dst / "episodes" / item / q["run_id"]
            ep.mkdir(parents=True)
            for f in ("result.json", "trace.jsonl"):
                shutil.copy2(src / f, ep / f)
            log = run / "agent_logs" / f"{item}-rep{rep}.log"
            if not log.exists():  # the run's supervisor moved it aside; take the copy written with the result
                t = (src / "result.json").stat().st_mtime
                cands = sorted(RUNS.glob(f"archive/*/{s}--{item}-rep{rep}.log*"),
                               key=lambda p: abs(p.stat().st_mtime - t))
                if not cands or abs(cands[0].stat().st_mtime - t) > 120:
                    raise SystemExit(f"{s}: no transcript for {item}")
                log = cands[0]
            out = []
            for l in last_session(log.read_text(errors="replace").splitlines()):
                if l.startswith("{"):
                    try:
                        e = json.loads(l)
                        if isinstance(e, dict):
                            e.pop("tool_use_result", None)  # Claude Code repeats the tool result here
                        l = json.dumps(strip_images(e), ensure_ascii=False)
                    except ValueError:
                        pass
                out.append(l)
            (dst / "agent_logs" / f"{item}-rep{rep}.log").write_text("\n".join(out) + "\n")
    rows.sort(key=lambda q: q["instance_id"])
    (dst / "results.jsonl").write_text("".join(json.dumps(q) + "\n" for q in rows))
    keep = ("model", "agent_mcp", "protocol", "episode_prompt", "repeats", "seed", "limits", "device",
            "dataset_fingerprint", "host")
    run_meta = {"name": name, **{k: meta.get(k) for k in keep},
                "agent_mcp": (meta.get("agent_mcp") or "").replace(str(ROOT) + "/", ""),
                "instances": sorted(q["instance_id"] for q in rows), "source_runs": slices}
    (dst / "run.json").write_text(json.dumps(run_meta, indent=1) + "\n")
    return {"config": name, "episodes": len(rows)}


def main():
    OUT.mkdir(exist_ok=True)
    for name, slices in CONFIGS.items():
        print(export(name, slices))


if __name__ == "__main__":
    main()
