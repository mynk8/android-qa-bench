#!/usr/bin/env python3
"""Collect the final metrics of every model configuration into docs/paper/data/results.json.

    python3 docs/paper/data/collect.py

Runs tools/leaderboard.py per configuration and adds the outcome counts (latest row per episode)."""
import collections, json, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


def outcomes(runs):
    last = {}
    for r in runs:
        p = ROOT / r / "results.jsonl"
        for line in p.read_text().splitlines():
            if line.strip():
                q = json.loads(line)
                last[(q["instance_id"], q.get("repeat", 0))] = q["outcome"]
    return dict(collections.Counter(last.values()))


def main():
    out = []
    for c in json.loads((HERE / "configs.json").read_text()):
        with tempfile.NamedTemporaryFile(suffix=".json") as f:
            subprocess.run([sys.executable, str(ROOT / "tools" / "leaderboard.py"),
                            *[str(ROOT / r) for r in c["runs"]], "--json", f.name],
                           check=True, capture_output=True)
            lb = json.loads(Path(f.name).read_text())
        out.append({**c, "outcomes": outcomes(c["runs"]), "episodes": lb["episodes"],
                    "by_family": lb["episode_bug_recall_by_family"], "by_app": lb["episode_bug_recall_by_app"],
                    "by_contamination": lb["episode_bug_recall_by_contamination"],
                    "coverage": lb["changelog_coverage"]})
    (HERE / "results.json").write_text(json.dumps(out, indent=1))
    for c in out:
        e = c["episodes"]
        print(f"{c['label']:22} {c['setting']:8} score {e['episode_score']:.3f} recall {e['bug_recall']:.2f} "
              f"prec {e['report_precision']:.2f} cost ${e['cost_usd']} steps {e['steps_mean']} {c['outcomes']}")


if __name__ == "__main__":
    main()
