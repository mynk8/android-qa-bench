#!/usr/bin/env python3
"""Data figures for the conference paper (vector PDF, ACM sigconf widths).

    pip install matplotlib==3.* numpy        # not needed by the benchmark itself
    python3 docs/paper/data/collect.py && python3 docs/paper/data/analysis.py \
        && python3 docs/paper/data/stats_extra.py
    python3 docs/paper/conference/make_figs.py

Every value is read from docs/paper/data/{results,analysis,stats}.json or, for sign-off
confidences, from the stored runs through tools/leaderboard.load. Palette: Okabe-Ito; provider is
shown by colour and marker shape, so no panel depends on colour alone.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DATA = ROOT / "docs" / "paper" / "data"
OUT = HERE / "figs"
sys.path.insert(0, str(ROOT))
from tools.leaderboard import load  # noqa: E402

R = {c["runs"][0].split("/")[-1]: c for c in json.loads((DATA / "results.json").read_text())}
S = json.loads((DATA / "stats.json").read_text())
KEY = {"gpt-6.1-sol-low": "sol", "deepseek-v4.1-flash-high": "deepseek", "claude-sonnet-5.5-medium": "sonnet",
       "claude-haiku-5.5": "haiku", "gpt-6-luna-max": "luna_max", "gpt-6-luna-medium": "luna_med"}
# one short name per configuration, used in every figure and defined in Table 3 of the paper
LABEL = {"sol": "Sol", "deepseek": "DeepSeek", "sonnet": "Sonnet", "haiku": "Haiku",
         "luna_max": "Luna max", "luna_med": "Luna med."}
# outcome colours never reuse a provider hue (providers: orange, blue, green)
OUTC = {"good": "#3B3B3B", "bad": "#CC79A7", "mid": "#F0E442", "none": "#BBBBBB", "cap": "#56B4E9"}
ORDER = ["sol", "deepseek", "sonnet", "haiku", "luna_max", "luna_med"]  # by recall
RUN = {v: k for k, v in KEY.items()}
OI = {"orange": "#E69F00", "sky": "#56B4E9", "green": "#009E73", "yellow": "#F0E442",
      "blue": "#0072B2", "verm": "#D55E00", "pink": "#CC79A7", "grey": "#7F7F7F"}
PROV = {"sol": ("blue", "s"), "luna_max": ("blue", "s"), "luna_med": ("blue", "s"),
        "sonnet": ("orange", "o"), "haiku": ("orange", "o"), "deepseek": ("green", "^")}
COL, FULL = 3.33, 7.0  # inches: sigconf column and text width

mpl.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"],
    "font.size": 7, "axes.titlesize": 7.5, "axes.labelsize": 7, "xtick.labelsize": 6.5,
    "ytick.labelsize": 6.5, "legend.fontsize": 6.5, "axes.spines.top": False,
    "axes.spines.right": False, "axes.linewidth": 0.6, "xtick.major.width": 0.6,
    "ytick.major.width": 0.6, "pdf.fonttype": 42, "ps.fonttype": 42, "savefig.dpi": 600,
    "figure.facecolor": "white", "axes.facecolor": "white",
})


def ep(k: str) -> dict:
    return R[RUN[k]]["episodes"]


def save(fig, name: str) -> None:
    OUT.mkdir(exist_ok=True)
    fig.savefig(OUT / f"{name}.pdf")
    plt.close(fig)


def dot(ax, k: str, x: float, y: float, **kw) -> None:
    c, m = PROV[k]
    ax.plot(x, y, marker=m, color=OI[c], ms=4.5, mec="black", mew=0.4, ls="none", zorder=3, **kw)


def fig_headline() -> None:
    """Recall and Episode Score (episode bootstrap CI), strict pass (Wilson CI)."""
    fig, axes = plt.subplots(1, 3, figsize=(FULL, 1.55), sharey=True, layout="constrained")
    y = np.arange(len(ORDER))[::-1]
    panels = [
        ("(a) Recall", lambda k: (ep(k)["bug_recall"], ep(k)["bug_recall_ci95"]), (0, 0.8), True),
        ("(b) Strict pass", lambda k: (ep(k)["solve_rate"], ep(k)["solve_rate_ci95"]), (0, 0.5), True),
        ("(c) Episode Score", lambda k: (ep(k)["episode_score"], ep(k)["episode_score_ci95"]), (0, 0.6), False),
    ]
    for ax, (title, get, lim, is_pct) in zip(axes, panels):
        for yi, k in zip(y, ORDER):
            v, ci = get(k)
            ax.plot(ci, [yi, yi], color="black", lw=0.8, zorder=2)
            dot(ax, k, v, yi)
            ax.text(ci[1] + 0.012 * (lim[1] - lim[0]) * 2, yi, f"{100 * v:.0f}%" if is_pct else f"{v:.2f}",
                    va="center", fontsize=6)
        ax.set_xlim(*lim)
        ax.set_title(title, loc="left")
        if is_pct:
            ax.xaxis.set_major_formatter(mpl.ticker.PercentFormatter(1.0, decimals=0))
        ax.grid(axis="x", lw=0.3, color="#DDDDDD")
    axes[0].set_yticks(y, [LABEL[k] for k in ORDER])
    save(fig, "headline")


def fig_recall_precision() -> None:
    fig, ax = plt.subplots(figsize=(COL, 2.2), layout="constrained")
    p = np.linspace(0.11, 0.62, 300)
    for f1 in (0.2, 0.3, 0.4, 0.5):
        r = f1 * p / (2 * p - f1)
        ok = (r > 0.05) & (r < 0.72) & (2 * p > f1)
        ax.plot(p[ok], r[ok], ls=":", lw=0.6, color=OI["grey"])
        ax.text(0.623, f1 * 0.62 / (2 * 0.62 - f1), f"F1 {f1}", fontsize=5.5, color=OI["grey"], va="center")
    # label positions in data coordinates (no label covers a point or another label)
    pos = {"sol": (0.35, 0.60, "left"), "deepseek": (0.35, 0.50, "left"), "sonnet": (0.452, 0.47, "left"),
           "haiku": (0.268, 0.43, "right"), "luna_max": (0.255, 0.34, "left"), "luna_med": (0.49, 0.155, "right")}
    for k in ORDER:
        e = ep(k)
        dot(ax, k, e["report_precision"], e["bug_recall"])
        x, y, ha = pos[k]
        ax.text(x, y, LABEL[k], fontsize=5.8, ha=ha, va="center")
    ax.set(xlim=(0.15, 0.66), ylim=(0.05, 0.72), xlabel="Report precision", ylabel="Recall")
    ax.xaxis.set_major_formatter(mpl.ticker.PercentFormatter(1.0, decimals=0))
    ax.yaxis.set_major_formatter(mpl.ticker.PercentFormatter(1.0, decimals=0))
    save(fig, "recall_precision")


def fig_endings() -> None:
    parts = [("correct_signoff", "Correct sign-off", OUTC["good"], ""),
             ("false_signoff", "Signed off, regressions missed", OUTC["bad"], "////"),
             ("gave_up", "Stopped, no sign-off", OUTC["mid"], ""),
             ("cut_off", "Cut off at action cap", OUTC["none"], "...."),
             ("report_cap", "Stopped at report limit", OUTC["cap"], "xxx")]
    fig, ax = plt.subplots(figsize=(COL, 1.9), layout="constrained")
    y = np.arange(len(ORDER))[::-1]
    left = np.zeros(len(ORDER))
    for key, lab, col, hatch in parts:
        vals = np.array([ep(k)["stopping"][key] for k in ORDER])
        ax.barh(y, vals, left=left, color=col, hatch=hatch, edgecolor="black", lw=0.3, label=lab, height=0.7)
        for yi, l, v in zip(y, left, vals):
            if v >= 0.1:
                ax.text(l + v / 2, yi, f"{100 * v:.0f}", ha="center", va="center", fontsize=5.8,
                        bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none", alpha=0.85))
        left += vals
    ax.set_yticks(y, [LABEL[k] for k in ORDER])
    ax.set_xlim(0, 1)
    ax.xaxis.set_major_formatter(mpl.ticker.PercentFormatter(1.0, decimals=0))
    ax.set_xlabel("Share of 51 episodes")
    ax.legend(ncol=2, loc="upper center", bbox_to_anchor=(0.4, -0.32), frameon=False, handlelength=1.4,
              columnspacing=0.8)
    save(fig, "endings")


def fig_effort_cost() -> None:
    fig, (a, b) = plt.subplots(1, 2, figsize=(FULL, 1.75), layout="constrained")
    # label positions in data coordinates (chosen so no label covers a point or another label)
    pos_a = {"sonnet": (75, 0.39, "left"), "sol": (210, 0.29, "left"), "haiku": (225, 0.237, "left"),
             "luna_max": (158, 0.209, "right"), "deepseek": (286, 0.183, "right"), "luna_med": (47, 0.144, "left")}
    pos_b = {"sonnet": (0.6, 0.39, "left"), "sol": (0.72, 0.29, "left"), "haiku": (0.72, 0.237, "left"),
             "luna_max": (0.15, 0.235, "right"), "deepseek": (0.055, 0.17, "right"), "luna_med": (0.017, 0.144, "left")}
    for k in ORDER:
        e = ep(k)
        dot(a, k, e["steps_mean"], e["episode_score"])
        x, y, ha = pos_a[k]
        a.text(x, y, LABEL[k], fontsize=5.8, ha=ha, va="center")
        partial = e["cost_episodes_logged"] < e["episodes"]
        c, m = PROV[k]
        b.plot(e["cost_usd_per_episode"], e["episode_score"], marker=m, ms=4.5, ls="none", mec="black", mew=0.4,
               color="white" if partial else OI[c], zorder=3)
        tag = f" ({e['cost_episodes_logged']}/{e['episodes']})" if partial else ""
        x, y, ha = pos_b[k]
        b.text(x, y, LABEL[k] + tag, fontsize=5.8, ha=ha, va="center")
    a.axvline(300, ls="--", lw=0.6, color="#555555")
    a.text(298, 0.47, "action cap", ha="right", fontsize=5.8, color="#555555")
    a.set(xlim=(0, 340), ylim=(0, 0.5), xlabel="Agent actions per episode (mean)", ylabel="Episode Score")
    a.set_title("(a) Effort", loc="left")
    b.set_xscale("log")
    b.set(xlim=(0.01, 2), ylim=(0, 0.5), xlabel="Cost per episode, USD (log scale; hollow = partly logged)")
    b.set_title("(b) Cost", loc="left")
    for ax in (a, b):
        ax.grid(lw=0.3, color="#DDDDDD")
    save(fig, "effort_cost")


def fig_coverage() -> None:
    parts = [("caught", "Caught", OUTC["good"], ""),
             ("miss_tested_not_noticed", "Exercised, not noticed", OUTC["bad"], "////"),
             ("miss_shallow", "Reached, not exercised", OUTC["mid"], ""),
             ("miss_ignored", "Never reached", OUTC["none"], "....")]
    fig, ax = plt.subplots(figsize=(COL, 1.9), layout="constrained")
    y = np.arange(len(ORDER))[::-1]
    left = np.zeros(len(ORDER))
    n_lines = R[RUN["sol"]]["coverage"]["real"]["lines"]
    for key, lab, col, hatch in parts:
        vals = np.array([R[RUN[k]]["coverage"]["real"][key] for k in ORDER], dtype=float)
        ax.barh(y, vals, left=left, color=col, hatch=hatch, edgecolor="black", lw=0.3, label=lab, height=0.7)
        for yi, l, v in zip(y, left, vals):
            if v >= 8:
                ax.text(l + v / 2, yi, f"{v:.0f}", ha="center", va="center", fontsize=5.8,
                        bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none", alpha=0.85))
        left += vals
    ax.set_yticks(y, [LABEL[k] for k in ORDER])
    ax.set_xlim(0, n_lines)
    ax.set_xlabel(f"Release-note lines that hide a regression (of {n_lines})")
    ax.legend(ncol=2, loc="upper center", bbox_to_anchor=(0.4, -0.32), frameon=False, handlelength=1.4,
              columnspacing=0.8)
    save(fig, "coverage")


def fig_difficulty() -> None:
    fig, (a, b) = plt.subplots(1, 2, figsize=(FULL, 1.75), layout="constrained",
                               gridspec_kw={"width_ratios": [1, 1]})
    h = S["caught_by_n_configs"]
    xs = list(range(7))
    a.bar(xs, [h[str(x)] for x in xs], color="#9A9A9A", edgecolor="black", lw=0.4, width=0.75)
    for x in xs:
        a.text(x, h[str(x)] + 0.4, str(h[str(x)]), ha="center", fontsize=6)
    a.set(xlabel="Configurations that caught the regression", ylabel="Regressions (of 91)", xticks=xs)
    a.set_title("(a) Item difficulty", loc="left")
    m = np.full((6, 6), np.nan)
    for i, ka in enumerate(ORDER):
        for j, kb in enumerate(ORDER):
            if i == j:
                continue
            pair = S["pairs"].get(f"{ka}-{kb}") or S["pairs"].get(f"{kb}-{ka}")
            m[i, j] = pair["overlap_obs"] / pair["overlap_exp"]
    im = b.imshow(m, cmap="cividis", vmin=1.0, vmax=2.4, aspect="auto")
    for i in range(6):
        for j in range(6):
            if not np.isnan(m[i, j]):
                b.text(j, i, f"{m[i, j]:.2f}", ha="center", va="center", fontsize=5.6,
                       color="white" if m[i, j] < 1.7 else "black")
    short = [LABEL[k] for k in ORDER]
    b.set_xticks(range(6), short, rotation=30, ha="right")
    b.set_yticks(range(6), short)
    b.spines[:].set_visible(False)
    b.set_title("(b) Shared catches, observed / expected", loc="left")
    fig.colorbar(im, ax=b, shrink=0.85, pad=0.01, label="Overlap ratio")
    save(fig, "difficulty")


def fig_confidence() -> None:
    fig, ax = plt.subplots(figsize=(COL, 1.9), layout="constrained")
    rng = np.random.default_rng(20261116)
    for i, k in enumerate(ORDER):
        eps, _ = load([ROOT / "results" / RUN[k]])
        for r in eps:
            so = r.get("sign_off") or {}
            if so.get("verdict") != "PASS" or so.get("confidence") is None:
                continue
            ok = not (set(r.get("required") or []) - set(r.get("found") or []))
            x = i + (-0.17 if ok else 0.17) + rng.uniform(-0.08, 0.08)
            ax.plot(x, float(so["confidence"]), marker="o" if ok else "x", ms=2.6 if ok else 2.8,
                    color=OUTC["good"] if ok else OUTC["bad"], mew=0.7, ls="none", alpha=0.85)
        au = S["signoff_auroc"][k]["auroc"]
        ax.text(i, 1.06, f"AUROC\n{au:.2f}", ha="center", fontsize=5.5)
    ax.set_xticks(range(6), [LABEL[k] for k in ORDER])
    ax.set(ylim=(0, 1.16), ylabel="Stated sign-off confidence")
    ax.plot([], [], "o", color=OUTC["good"], ms=3, label="All regressions reported")
    ax.plot([], [], "x", color=OUTC["bad"], ms=3, label="Regressions missed")
    ax.legend(loc="lower left", frameon=False, ncol=2)
    save(fig, "confidence")


if __name__ == "__main__":
    for f in (fig_headline, fig_recall_precision, fig_endings, fig_effort_cost, fig_coverage, fig_difficulty,
              fig_confidence):
        f()
    print("wrote", sorted(p.name for p in OUT.glob("*.pdf")))
