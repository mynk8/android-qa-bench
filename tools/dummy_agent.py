#!/usr/bin/env python3
"""Example QA agent for the stdin/stdout JSONL protocol.

Each line on stdin is a harness message; each line on stdout is an agent
message. Flush after every write.

Harness -> agent:
  {"type": "start", "kind": "episode"|"case", "item_id": "...", "brief": "...", "package": "..."}
  {"type": "developer_reply", "kind": "hit|already_fixed|leftover_known|no_match|malformed", "text": "...", "build_n": 2}
  {"type": "observation", "ui": [...], "build_id": "..."}
  {"type": "end", "reason": "...", "status": "..."}

Agent -> harness:
  {"type": "bug_report", "screen": "...", "element": "...", "field": "...",
   "symptom_type": "...", "expected": "...", "observed": "...", "steps": ["..."]}
  {"type": "sign_off", "verdict": "PASS", "confidence": 0.0, "notes": "..."}
  {"type": "action", "name": "tap|back|home|...", "args": {...}}
  {"verdict": "PASS|FAIL|INCONCLUSIVE", "confidence": 0.0, "evidence": [...]}

Oracle mode (for dry-run smoke tests only; it reads the dataset):

    python tools/dummy_agent.py --oracle --dataset dataset

Scripted mode:

    python tools/dummy_agent.py --script path/to/messages.jsonl
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.eval_lib import OracleAgent, load_json, opaque_id


def emit(msg: dict) -> None:
    sys.stdout.write(json.dumps(msg, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def read_msg() -> dict | None:
    line = sys.stdin.readline()
    if not line:
        return None
    line = line.strip()
    if not line:
        return read_msg()
    return json.loads(line)


def _resolve_ids(dataset: Path) -> dict[str, str]:
    """The harness shows agents opaque ids; the oracle maps them back (it may read the dataset)."""
    man = load_json(dataset / "manifest.json")
    ids = list(man.get("episodes") or []) + [d.name for d in (dataset / "cases").iterdir() if d.is_dir()]
    return {opaque_id(i): i for i in ids}


def run_oracle(dataset: Path) -> None:
    agent = OracleAgent(dataset)
    real = _resolve_ids(dataset)
    while True:
        msg = read_msg()
        if msg is None:
            break
        if msg.get("type") == "start" and msg.get("item_id") in real:
            msg = dict(msg, _oracle_item_id=real[msg["item_id"]])
        agent.send(msg)
        if msg.get("type") == "end":
            break
        # After start, drain the first report/verdict. After a developer_reply,
        # drain the next queued message. Observations are ignored.
        typ = msg.get("type")
        if typ in ("start", "developer_reply"):
            out = agent.recv()
            if out is not None:
                emit(out)


def run_script(path: Path) -> None:
    planned = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            planned.append(json.loads(line) if line.startswith("{") else load_json(Path(line)))
    # wait for start, then play
    while True:
        msg = read_msg()
        if msg is None:
            break
        if msg.get("type") == "end":
            break
        if msg.get("type") == "start":
            break
    for out in planned:
        emit(out)
        # wait for a reply or end before sending the next, except we just fire
        # sequentially after each harness line if the script already includes
        # only agent-originated messages.
        nxt = read_msg()
        if nxt is None or nxt.get("type") == "end":
            break


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dataset", type=Path, default=ROOT / "dataset")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--oracle", action="store_true", default=True)
    g.add_argument("--script", type=Path)
    args = ap.parse_args()
    if args.script:
        run_script(args.script)
    else:
        run_oracle(args.dataset)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
