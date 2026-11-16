"""Statistics for the paper beyond analysis.py: cluster-bootstrap recall, pairwise tests with Holm
correction, catch overlap, item difficulty, contamination split, rank correlations, sign-off
AUROC, grounding and key-widening sensitivity, and the prompt version of each run.

    python3 docs/paper/data/stats_extra.py      # writes docs/paper/data/stats.json
"""
from __future__ import annotations

import collections
import glob
import itertools
import json
import math
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from tools.leaderboard import catch_credit, episode_score, finished, load  # noqa: E402

CFG = {
    "sol": "gpt-6.1-sol-low", "deepseek": "deepseek-v4.1-flash-high",
    "sonnet": "claude-sonnet-5.5-medium", "haiku": "claude-haiku-5.5",
    "luna_max": "gpt-6-luna-max", "luna_med": "gpt-6-luna-medium",
}
B = 10_000
RNG = random.Random(20261116)
out: dict = {}


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    p = k / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return c - h, c + h


def pct(xs: list[float], lo: float = 2.5, hi: float = 97.5) -> tuple[float, float]:
    xs = sorted(xs)
    return xs[int(len(xs) * lo / 100)], xs[min(len(xs) - 1, int(len(xs) * hi / 100))]


def binom_two_sided(k: int, n: int) -> float:
    k = min(k, n - k)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)


def hyper_upper(obs: int, N: int, K: int, m: int) -> float:
    return sum(math.comb(K, i) * math.comb(N - K, m - i) for i in range(obs, min(K, m) + 1)) / math.comb(N, m)


def fisher_two_sided(a: int, b: int, c: int, d: int) -> float:
    """2x2 table [[a,b],[c,d]]; sum of probabilities <= observed."""
    r1, c1, n = a + b, a + c, a + b + c + d
    p = lambda x: math.comb(c1, x) * math.comb(n - c1, r1 - x) / math.comb(n, r1)
    p0 = p(a)
    lo, hi = max(0, r1 + c1 - n), min(r1, c1)
    return min(1.0, sum(p(x) for x in range(lo, hi + 1) if p(x) <= p0 * (1 + 1e-9)))


def holm(ps: dict) -> dict:
    items = sorted(ps.items(), key=lambda kv: kv[1])
    m, adj, run = len(items), {}, 0.0
    for i, (k, p) in enumerate(items):
        run = max(run, min(1.0, (m - i) * p))
        adj[k] = run
    return adj


def ranks(xs: list[float]) -> list[float]:
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    r = [0.0] * len(xs)
    i = 0
    while i < len(xs):
        j = i
        while j + 1 < len(xs) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        for t in range(i, j + 1):
            r[order[t]] = (i + j) / 2 + 1
        i = j + 1
    return r


def spearman(x: list[float], y: list[float]) -> float:
    rx, ry = ranks(x), ranks(y)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return num / den if den else float("nan")


def auroc(pos: list[float], neg: list[float]) -> float | None:
    if not pos or not neg:
        return None
    s = sum((p > q) + 0.5 * (p == q) for p in pos for q in neg)
    return s / (len(pos) * len(neg))


# ---------- dataset composition ----------
bugs = {json.load(open(f))["bug_id"]: json.load(open(f)) for f in sorted(glob.glob(str(ROOT / "dataset/bugs/*/bug.json")))}
episodes = {json.load(open(f))["episode_id"]: json.load(open(f)) for f in sorted(glob.glob(str(ROOT / "dataset/episodes/*/episode.json")))}
planted = [(e, b) for e, ep in episodes.items() for b in ep["bugs"]]
per_app = collections.Counter(bugs[b]["app_id"] for _, b in planted)
mature = {"amaze", "ankidroid", "markor", "tasks"}
out["dataset"] = {
    "bugs_total": len(bugs),
    "episodes": len(episodes),
    "episode_sizes": dict(collections.Counter(len(ep["bugs"]) for ep in episodes.values())),
    "planted": len(planted),
    "planted_per_app": dict(sorted(per_app.items())),
    "planted_mature": sum(v for k, v in per_app.items() if k in mature),
    "planted_2026": sum(v for k, v in per_app.items() if k not in mature),
    "families_planted": dict(collections.Counter(bugs[b]["family"] for _, b in planted)),
    "families_all_bugs": dict(collections.Counter(b["family"] for b in bugs.values())),
    "fixed_2026_planted": sum(1 for _, b in planted if (bugs[b].get("fix_date") or "") >= "2026-01-01"),
    "bug_status": dict(collections.Counter(b.get("status") for b in bugs.values())),
}

# ---------- runs ----------
runs = {k: {r["item_id"]: r for r in load([ROOT / "results" / v])[0]} for k, v in CFG.items()}
eps_ids = sorted(next(iter(runs.values())))
req = {e: sorted(set(runs["sol"][e].get("required") or [])) for e in eps_ids}
regs = sorted({(e, b) for e in eps_ids for b in req[e]})
caught = {k: {(e, b) for e in eps_ids for b in set(runs[k][e].get("found") or []) & set(req[e])} for k in CFG}
out["observable_regressions"] = len(regs)
masked = sorted(set(planted) - set(regs))
out["masked"] = masked
out["observable_per_app"] = dict(sorted(collections.Counter(bugs[b]["app_id"] for _, b in regs).items()))
out["observable_families"] = dict(collections.Counter(bugs[b]["family"] for _, b in regs))

# ---------- recall: Wilson vs episode-cluster bootstrap ----------
rec = {}
for k in CFG:
    n_c = len(caught[k])
    boots = []
    for _ in range(B):
        s = [RNG.choice(eps_ids) for _ in eps_ids]
        num = sum(len(set(runs[k][e].get("found") or []) & set(req[e])) for e in s)
        den = sum(len(req[e]) for e in s)
        boots.append(num / den)
    w = wilson(n_c, len(regs))
    cb = pct(boots)
    rec[k] = {"caught": n_c, "recall": round(n_c / len(regs), 3),
              "wilson": [round(w[0], 3), round(w[1], 3)], "cluster_boot": [round(cb[0], 3), round(cb[1], 3)],
              "width_ratio": round((cb[1] - cb[0]) / (w[1] - w[0]), 2)}
out["recall"] = rec

# ---------- Episode Score, recomputed ----------
es = {k: {e: episode_score(runs[k][e]) for e in eps_ids} for k in CFG}
out["episode_score"] = {k: round(sum(v.values()) / len(v), 3) for k, v in es.items()}

# ---------- pairwise tests ----------
pairs = list(itertools.combinations(CFG, 2))
mc, boot_es, overlap = {}, {}, {}
for a, b in pairs:
    only_a, only_b = len(caught[a] - caught[b]), len(caught[b] - caught[a])
    mc[(a, b)] = binom_two_sided(only_a, only_a + only_b) if only_a + only_b else 1.0
    d = [es[a][e] - es[b][e] for e in eps_ids]
    bs = []
    for _ in range(B):
        s = [RNG.choice(d) for _ in d]
        bs.append(sum(s) / len(s))
    lo, hi = pct(bs)
    p_b = min(1.0, 2 * min(sum(x <= 0 for x in bs), sum(x >= 0 for x in bs)) / B)
    boot_es[(a, b)] = (round(sum(d) / len(d), 3), round(lo, 3), round(hi, 3), p_b)
    both = len(caught[a] & caught[b])
    exp = len(caught[a]) * len(caught[b]) / len(regs)
    overlap[(a, b)] = (both, round(exp, 1), round(hyper_upper(both, len(regs), len(caught[a]), len(caught[b])), 4),
                       round(both / len(caught[a] | caught[b]), 2), only_a, only_b)
mc_h, es_h = holm(mc), holm({k: v[3] for k, v in boot_es.items()})
out["pairs"] = {f"{a}-{b}": {"mcnemar_p": round(mc[(a, b)], 4), "mcnemar_holm": round(mc_h[(a, b)], 4),
                             "only_a": overlap[(a, b)][4], "only_b": overlap[(a, b)][5],
                             "es_diff": boot_es[(a, b)][:3], "es_boot_p": round(boot_es[(a, b)][3], 4),
                             "es_holm": round(es_h[(a, b)], 4),
                             "overlap_obs": overlap[(a, b)][0], "overlap_exp": overlap[(a, b)][1],
                             "overlap_p_upper": overlap[(a, b)][2], "jaccard": overlap[(a, b)][3]}
                 for a, b in pairs}

# ---------- item difficulty ----------
n_by = collections.Counter(sum((r in caught[k]) for k in CFG) for r in regs)
out["caught_by_n_configs"] = dict(sorted(n_by.items()))
fam_rec = {}
for fam in ("state", "display", "interaction"):
    rs = [r for r in regs if bugs[r[1]]["family"] == fam]
    tot = sum(sum((r in caught[k]) for k in CFG) for r in rs)
    fam_rec[fam] = (len(rs), round(tot / (6 * len(rs)), 3))
out["pooled_recall_by_family"] = fam_rec

# ---------- contamination: Fisher per config, pre-2026 vs 2026 ----------
cont = {}
for k in CFG:
    pre = [r for r in regs if (bugs[r[1]].get("fix_date") or "") < "2026-01-01"]
    new = [r for r in regs if r not in pre]
    a = sum(r in caught[k] for r in pre)
    c = sum(r in caught[k] for r in new)
    cont[k] = {"pre": f"{a}/{len(pre)}", "y2026": f"{c}/{len(new)}",
               "diff_pp": round(100 * (c / len(new) - a / len(pre)), 1),
               "fisher_p": round(fisher_two_sided(a, len(pre) - a, c, len(new) - c), 3)}
out["contamination"] = cont

# ---------- actions, cost vs score (n = 6) ----------
lb = {k: json.load(open(ROOT / "results" / v / "leaderboard.json"))["episodes"] for k, v in CFG.items()}
acts = {k: lb[k]["steps_mean"] for k in CFG}
cost = {k: lb[k]["cost_usd_per_episode"] for k in CFG}
sc = [out["episode_score"][k] for k in CFG]
out["spearman_actions_score"] = round(spearman([acts[k] for k in CFG], sc), 3)
out["spearman_cost_score"] = round(spearman([cost[k] for k in CFG], sc), 3)
aa = {c["runs"][0].split("/")[-1]: c["aa_index"] for c in json.loads((HERE / "results.json").read_text())}
aa_k = [k for k in CFG if isinstance(aa.get(CFG[k]), (int, float))]
out["aa_index"] = {k: aa[CFG[k]] for k in aa_k}
out["spearman_aa_score"] = {"n": len(aa_k), "rho": round(spearman([aa[CFG[k]] for k in aa_k], [out["episode_score"][k] for k in aa_k]), 3)}

# ---------- sign-off confidence: AUROC (correct vs missed) ----------
cal = {}
for k in CFG:
    pos, neg = [], []
    for e in eps_ids:
        so = runs[k][e].get("sign_off") or {}
        if so.get("verdict") != "PASS" or so.get("confidence") is None:
            continue
        ok = not (set(req[e]) - set(runs[k][e].get("found") or []))
        (pos if ok else neg).append(float(so["confidence"]))
    a = auroc(pos, neg)
    cal[k] = {"n_correct": len(pos), "n_missed": len(neg), "auroc": None if a is None else round(a, 3)}
out["signoff_auroc"] = cal

# ---------- cost provenance ----------
out["cost"] = {k: {"per_episode": lb[k]["cost_usd_per_episode"], "logged": lb[k]["cost_episodes_logged"]} for k in CFG}


# ---------- grounding: credits from reports with no checked quote ----------
def trace(k: str, e: str) -> list[dict]:
    f = next((ROOT / "results" / CFG[k] / "episodes" / e).glob("*/trace.jsonl"))
    return [json.loads(l) for l in f.read_text().splitlines() if l.strip()]


ung = {}
for k in CFG:
    n = 0
    for e in eps_ids:
        tr = trace(k, e)
        for i, ev in enumerate(tr):
            if ev.get("event") == "scored" and ev.get("kind") == "hit" and ev.get("quote_seen") is None:
                nxt = next((x for x in tr[i + 1:] if x.get("event") in ("duplicate", "scored")), {})
                n += nxt.get("event") != "duplicate"
    ung[k] = {"credits_without_checked_quote": n, "strict_recall": round((len(caught[k]) - n) / len(regs), 3)}
out["grounding_sensitivity"] = ung

# ---------- key widening: credits added by the transcript rescore after the grader audit ----------
wid = {}
for k in CFG:
    gained = eps_n = 0
    for e in eps_ids:
        r = runs[k][e]
        kinds = (r.get("rescored") or {}).get("report_kinds")
        if not kinds:
            continue
        orig = {b for ev in trace(k, e) if ev.get("event") == "scored" and ev.get("kind") == "hit"
                for b in (ev.get("bugs") or []) if b in req[e]}
        g = len(set(r.get("found") or []) & set(req[e])) - len(orig)
        gained += g
        eps_n += 1
    wid[k] = {"rescored_episodes": eps_n, "net_credits_vs_live_harness": gained}
out["rescore_sensitivity"] = wid

# ---------- protocol of each run ----------
out["run_protocol"] = {k: {x: json.loads((ROOT / "results" / v / "run.json").read_text()).get(x)
                           for x in ("episode_prompt", "dataset_fingerprint")} for k, v in CFG.items()}

(HERE / "stats.json").write_text(json.dumps(out, indent=1, default=str, sort_keys=True) + "\n")
print("wrote", HERE / "stats.json")
