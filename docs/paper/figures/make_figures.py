#!/usr/bin/env python3
"""Leaderboard-style figures for the paper, as standalone SVG (and PNG / PDF when rsvg-convert exists).

    python3 docs/paper/data/collect.py          # refresh docs/paper/data/results.json
    python3 docs/paper/figures/make_figures.py  # write docs/paper/figures/*.svg

No plotting library: the SVG is written directly so the figures need nothing beyond Python.
Colour follows the provider (fixed order, validated all-pairs for three slots); every point and bar
is also labelled directly, so identity never depends on colour alone.
"""
from __future__ import annotations

import json
import math
import shutil
import subprocess
from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = json.loads((HERE.parent / "data" / "results.json").read_text())

# Reference palette (light). Provider -> categorical slot, in fixed order.
PROVIDER = {"OpenAI": "#2a78d6", "Anthropic": "#eb6834", "DeepSeek": "#1baf7a"}
SURFACE, INK, INK2, MUTED = "#fcfcfb", "#0b0b0b", "#52514e", "#898781"
GRID, AXIS, WASH = "#e1e0d9", "#c3c2b7", "#f0efec"
GOOD, CRITICAL, WARNING = "#0ca30c", "#d03b3b", "#fab219"
BLUE = {"250": "#86b6ef", "450": "#2a78d6", "650": "#104281"}
FONT = "'IBM Plex Sans', system-ui, -apple-system, 'Segoe UI', sans-serif"
W, H = 960, 540
SOURCE = "Source: AQB episode suite, 51 episodes per model (9 Android apps, 91 planted regressions)."


def name(c):
    return f"{c['label']} ({c['setting']})" if c["setting"] != "default" else c["label"]


class Svg:
    def __init__(self, w=W, h=H):
        self.w, self.h, self.parts = w, h, []

    def add(self, s):
        self.parts.append(s)

    def text(self, x, y, s, size=13, fill=INK2, anchor="start", weight=400, extra=""):
        self.add(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" text-anchor="{anchor}" '
                 f'font-weight="{weight}" {extra}>{escape(s)}</text>')

    def line(self, x1, y1, x2, y2, stroke=GRID, width=1, dash=""):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{stroke}" '
                 f'stroke-width="{width}"{d}/>')

    def header(self, title, subtitle, note=SOURCE):
        self.text(32, 44, title, size=22, fill=INK, weight=600)
        self.text(32, 70, subtitle, size=14, fill=INK2)
        self.text(32, self.h - 18, note, size=11, fill=MUTED)

    def save(self, stem):
        body = "\n".join(self.parts)
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" width="{self.w}" '
               f'height="{self.h}" font-family="{FONT}">\n<rect width="100%" height="100%" fill="{SURFACE}"/>\n'
               f'{body}\n</svg>\n')
        p = HERE / f"{stem}.svg"
        p.write_text(svg)
        if shutil.which("rsvg-convert"):
            subprocess.run(["rsvg-convert", "-z", "2", "-o", str(HERE / f"{stem}.png"), str(p)], check=True)
            subprocess.run(["rsvg-convert", "-f", "pdf", "-o", str(HERE / f"{stem}.pdf"), str(p)], check=True)
        print("wrote", p.name)


def bar_path(x, y, w, h, r=4):
    """A bar with rounded data-end (top), square at the baseline."""
    r = min(r, h, w / 2)
    return (f"M{x:.1f},{y + h:.1f} L{x:.1f},{y + r:.1f} Q{x:.1f},{y:.1f} {x + r:.1f},{y:.1f} "
            f"L{x + w - r:.1f},{y:.1f} Q{x + w:.1f},{y:.1f} {x + w:.1f},{y + r:.1f} L{x + w:.1f},{y + h:.1f} Z")


def legend(s, x, y, items):
    """items: [(colour, label)] laid out in one row."""
    for col, lab in items:
        s.add(f'<rect x="{x}" y="{y - 10}" width="12" height="12" rx="3" fill="{col}"/>')
        s.text(x + 18, y, lab, size=12, fill=INK2)
        x += 18 + 6.6 * len(lab) + 24
    return x


def provider_legend(s, x=None, y=70):
    items = [(PROVIDER[p], p) for p in PROVIDER]
    width = sum(18 + 6.6 * len(l) + 24 for _, l in items) - 24
    legend(s, (x if x is not None else s.w - 32 - width), y, items)


# ---------------------------------------------------------------- 1. headline score
def fig_score():
    s = Svg()
    s.header("AQB Episode Score", "Bugs caught, discounted by false reports and by cut-offs at the action cap. "
             "Higher is better; whiskers are 95% CIs.")
    provider_legend(s, y=100)
    rows = sorted(DATA, key=lambda c: -c["episodes"]["episode_score"])
    left, right, top, bottom = 72, s.w - 32, 128, s.h - 96
    ymax = 0.6
    yv = lambda v: bottom - (bottom - top) * v / ymax
    for t in [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6]:
        s.line(left, yv(t), right, yv(t), stroke=AXIS if t == 0 else GRID)
        s.text(left - 10, yv(t) + 4, f"{t:.1f}", size=12, fill=MUTED, anchor="end",
               extra='font-variant-numeric="tabular-nums"')
    slot = (right - left) / len(rows)
    bw = min(64, slot * 0.5)
    for i, c in enumerate(rows):
        e = c["episodes"]
        v, (lo, hi) = e["episode_score"], e["episode_score_ci95"]
        cx = left + slot * (i + 0.5)
        col = PROVIDER[c["provider"]]
        s.add(f'<path d="{bar_path(cx - bw / 2, yv(v), bw, bottom - yv(v))}" fill="{col}">'
              f'<title>{escape(name(c))}: {v:.3f} (95% CI {lo:.3f}-{hi:.3f})</title></path>')
        s.line(cx, yv(hi), cx, yv(lo), stroke=INK2, width=1.5)
        s.line(cx - 6, yv(hi), cx + 6, yv(hi), stroke=INK2, width=1.5)
        s.line(cx - 6, yv(lo), cx + 6, yv(lo), stroke=INK2, width=1.5)
        s.text(cx, yv(hi) - 8, f"{v:.2f}", size=15, fill=INK, anchor="middle", weight=600)
        s.text(cx, bottom + 22, c["label"], size=13, fill=INK, anchor="middle", weight=500)
        s.text(cx, bottom + 40, c["setting"] if c["setting"] != "default" else "", size=12, fill=MUTED,
               anchor="middle")
    s.save("fig1_episode_score")


# ---------------------------------------------------------------- scatter helper
def scatter(stem, title, subtitle, xs, ys, xlab, ylab, xticks, yticks, xfmt, yfmt, logx=False,
            quadrant=None, extras=None, label_offsets=None, note=SOURCE):
    s = Svg()
    s.header(title, subtitle, note=note)
    provider_legend(s, y=100)
    left, right, top, bottom = 84, s.w - 48, 128, s.h - 96
    x0, x1 = xticks[0], xticks[-1]
    y0, y1 = yticks[0], yticks[-1]
    tx = (lambda v: math.log10(v)) if logx else (lambda v: v)
    xv = lambda v: left + (right - left) * (tx(v) - tx(x0)) / (tx(x1) - tx(x0))
    yv = lambda v: bottom - (bottom - top) * (v - y0) / (y1 - y0)
    if quadrant:  # shade the attractive quadrant (better on both axes), split at the medians
        qx, qy, corner = quadrant
        mx, my = sorted(xs)[len(xs) // 2], sorted(ys)[len(ys) // 2]
        mx = (sorted(xs)[len(xs) // 2 - 1] * sorted(xs)[len(xs) // 2]) ** 0.5 if logx else mx
        my = (sorted(ys)[len(ys) // 2 - 1] + sorted(ys)[len(ys) // 2]) / 2
        xa, xb = (left, xv(mx)) if corner == "left" else (xv(mx), right)
        s.add(f'<rect x="{xa:.1f}" y="{top:.1f}" width="{xb - xa:.1f}" height="{yv(my) - top:.1f}" fill="{WASH}"/>')
        s.text(xa + 10 if corner == "left" else xb - 10, top + 20, "Most attractive quadrant", size=12,
               fill=INK2, anchor="start" if corner == "left" else "end", weight=500)
    for t in yticks:
        s.line(left, yv(t), right, yv(t), stroke=AXIS if t == y0 else GRID)
        s.text(left - 10, yv(t) + 4, yfmt(t), size=12, fill=MUTED, anchor="end")
    for t in xticks:
        s.line(xv(t), top, xv(t), bottom, stroke=AXIS if t == x0 else GRID)
        s.text(xv(t), bottom + 20, xfmt(t), size=12, fill=MUTED, anchor="middle")
    s.text((left + right) / 2, bottom + 44, xlab, size=13, fill=INK2, anchor="middle", weight=500)
    s.text(0, 0, ylab, size=13, fill=INK2, anchor="middle", weight=500,
           extra=f'transform="translate({left - 54},{(top + bottom) / 2}) rotate(-90)"')
    if extras:
        extras(s, xv, yv, left, right, top, bottom)
    label_offsets = label_offsets or {}
    for c, x, y in zip(DATA, xs, ys):
        col = PROVIDER[c["provider"]]
        s.add(f'<circle cx="{xv(x):.1f}" cy="{yv(y):.1f}" r="8" fill="{col}" stroke="{SURFACE}" stroke-width="2">'
              f'<title>{escape(name(c))}: {xlab} {xfmt(x)}, {ylab} {yfmt(y)}</title></circle>')
        dx, dy, anchor = label_offsets.get(c["key"], (13, 5, "start"))
        s.text(xv(x) + dx, yv(y) + dy, name(c), size=13, fill=INK, anchor=anchor, weight=500)
    s.save(stem)


def fig_cost():
    per_ep = [c["episodes"]["cost_usd_per_episode"] for c in DATA]
    scatter("fig2_score_vs_cost", "Episode Score vs. Cost per Episode",
            "API-list-price cost of one 51-episode run divided by 51; log scale. Up and to the left is better.",
            per_ep, [c["episodes"]["episode_score"] for c in DATA],
            "Cost per episode (USD, log scale)", "Episode Score",
            [0.01, 0.03, 0.1, 0.3, 1.0], [0, 0.1, 0.2, 0.3, 0.4, 0.5],
            lambda v: f"${v:g}", lambda v: f"{v:.1f}", logx=True, quadrant=(None, None, "left"),
            label_offsets={"sonnet": (-13, 5, "end"), "haiku": (-13, 18, "end"), "sol": (-13, -6, "end")},
            note=SOURCE + " Codex runs priced at API list prices; they ran on a subscription.")


def fig_recall_precision():
    def iso(s, xv, yv, left, right, top, bottom):
        for f in (0.2, 0.3, 0.4, 0.5):
            pts = []
            for i in range(200):
                p = 0.01 + i * (0.7 - 0.01) / 199  # precision on x
                if 2 * p - f <= 0:
                    continue
                r = f * p / (2 * p - f)
                if 0 <= r <= 0.7:
                    pts.append(f"{xv(p):.1f},{yv(r):.1f}")
            s.add(f'<polyline points="{" ".join(pts)}" fill="none" stroke="{AXIS}" stroke-width="1" '
                  f'stroke-dasharray="4 4"/>')
            s.text(xv(0.69), yv(f * 0.69 / (2 * 0.69 - f)) - 6, f"F1 = {f}", size=11, fill=MUTED, anchor="end")
    scatter("fig3_recall_vs_precision", "Recall vs. Precision",
            "Share of planted regressions caught vs. share of bug reports that were real. Dashed: equal F1.",
            [c["episodes"]["report_precision"] for c in DATA], [c["episodes"]["bug_recall"] for c in DATA],
            "Report precision", "Bug recall",
            [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7], [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7],
            lambda v: f"{v:.0%}", lambda v: f"{v:.0%}", extras=iso,
            label_offsets={"deepseek": (13, -8, "start"), "sol": (13, -2, "start")})


def fig_steps():
    def cap(s, xv, yv, left, right, top, bottom):
        s.line(xv(300), top, xv(300), bottom, stroke=CRITICAL, width=1.5, dash="5 4")
        s.text(xv(300) - 8, top + 20, "Action cap (300)", size=12, fill=INK2, anchor="end", weight=500)
    scatter("fig4_score_vs_actions", "Episode Score vs. Actions per Episode",
            "Mean device actions an agent took before stopping. More testing is not always more score.",
            [c["episodes"]["steps_mean"] for c in DATA], [c["episodes"]["episode_score"] for c in DATA],
            "Actions per episode (mean)", "Episode Score",
            [0, 50, 100, 150, 200, 250, 300, 350], [0, 0.1, 0.2, 0.3, 0.4, 0.5],
            lambda v: f"{v:g}", lambda v: f"{v:.1f}", extras=cap,
            label_offsets={"deepseek": (-13, 5, "end"), "haiku": (13, 16, "start"), "sol": (-13, -8, "end")})


# ---------------------------------------------------------------- 5. how episodes ended
def fig_outcomes():
    s = Svg(h=500)
    s.header("How Each Episode Ended", "Share of 51 episodes. A sign-off is correct only when every planted "
             "regression was reported.")
    segs = [("correct_signoff", "Correct sign-off", GOOD, "#ffffff"),
            ("false_signoff", "Signed off, bugs missed", CRITICAL, "#ffffff"),
            ("gave_up", "Stopped without sign-off", WARNING, INK),
            ("cut_off", "Cut off at action cap", MUTED, "#ffffff")]
    legend(s, 32, 104, [(c, l) for _, l, c, _ in segs])
    rows = sorted(DATA, key=lambda c: -c["episodes"]["episode_score"])
    left, right, top = 250, s.w - 40, 128
    bh, gap = 34, 14
    for i, c in enumerate(rows):
        st = c["episodes"]["stopping"]
        y = top + i * (bh + gap)
        s.text(left - 14, y + bh / 2 + 5, name(c), size=13, fill=INK, anchor="end", weight=500)
        x = left
        for key, lab, col, ink in segs:
            v = st.get(key, 0)
            w = (right - left) * v
            if w <= 0:
                continue
            s.add(f'<rect x="{x:.1f}" y="{y}" width="{max(w - 2, 0.5):.1f}" height="{bh}" rx="3" fill="{col}">'
                  f'<title>{escape(name(c))}: {lab} {v:.0%}</title></rect>')
            if w > 40:
                s.text(x + 8, y + bh / 2 + 5, f"{v:.0%}", size=12, fill=ink, weight=600)
            x += w
    s.save("fig5_outcomes")


# ---------------------------------------------------------------- 6. changelog coverage
def fig_coverage():
    s = Svg()
    s.header("Did the Agent Test What Changed?", "Of the 92 release-note lines hiding a regression: how many the "
             "agent opened, exercised (6+ actions), and caught.")
    steps = [("reached", "Reached", BLUE["250"]), ("worked", "Exercised", BLUE["450"]), ("caught", "Caught", BLUE["650"])]
    legend(s, 32, 104, [(c, l) for _, l, c in steps])
    rows = sorted(DATA, key=lambda c: -c["episodes"]["episode_score"])
    left, right, top, bottom = 72, s.w - 32, 128, s.h - 96
    yv = lambda v: bottom - (bottom - top) * v / 100
    for t in range(0, 101, 20):
        s.line(left, yv(t), right, yv(t), stroke=AXIS if t == 0 else GRID)
        s.text(left - 10, yv(t) + 4, f"{t}%", size=12, fill=MUTED, anchor="end")
    slot = (right - left) / len(rows)
    bw = min(30, slot * 0.24)
    for i, c in enumerate(rows):
        real = c["coverage"]["real"]
        n = real["lines"]
        cx = left + slot * (i + 0.5)
        for j, (k, lab, col) in enumerate(steps):
            v = 100 * real[k] / n
            x = cx + (j - 1.5) * (bw + 2)
            s.add(f'<path d="{bar_path(x, yv(v), bw, bottom - yv(v))}" fill="{col}">'
                  f'<title>{escape(name(c))}: {lab} {real[k]}/{n} ({v:.0f}%)</title></path>')
        s.text(cx, yv(100 * real["caught"] / n) - 6 if False else bottom + 22, c["label"], size=13, fill=INK,
               anchor="middle", weight=500)
        s.text(cx, bottom + 40, c["setting"] if c["setting"] != "default" else "", size=12, fill=MUTED,
               anchor="middle")
        s.text(cx + (2 - 1.5) * (bw + 2) + bw / 2, yv(100 * real["caught"] / n) - 6, f"{real['caught']}",
               size=12, fill=INK, anchor="middle", weight=600)
    s.save("fig6_changelog_coverage")


def fig_aa():
    """AQB Episode Score against the Artificial Analysis Intelligence Index for the same setting."""
    rows = [c for c in DATA if c.get("aa_index") is not None]
    s = Svg()
    s.header("AQB vs. Artificial Analysis Intelligence Index", "Same model at the same reasoning effort. "
             "General intelligence does not order the agents the same way.",
             note="Source: Artificial Analysis Intelligence Index v5.0.1 (accessed 2026-11-16); AQB episode suite. "
                  "Haiku and DeepSeek omitted: their run settings have no matching index entry.")
    provider_legend(s, y=100)
    left, right, top, bottom = 84, s.w - 48, 128, s.h - 96
    xv = lambda v: left + (right - left) * (v - 10) / 30
    yv = lambda v: bottom - (bottom - top) * v / 0.5
    for t in (0, 0.1, 0.2, 0.3, 0.4, 0.5):
        s.line(left, yv(t), right, yv(t), stroke=AXIS if t == 0 else GRID)
        s.text(left - 10, yv(t) + 4, f"{t:.1f}", size=12, fill=MUTED, anchor="end")
    for t in (10, 15, 20, 25, 30, 35, 40):
        s.line(xv(t), top, xv(t), bottom, stroke=AXIS if t == 10 else GRID)
        s.text(xv(t), bottom + 20, str(t), size=12, fill=MUTED, anchor="middle")
    s.text((left + right) / 2, bottom + 44, "Artificial Analysis Intelligence Index", size=13, fill=INK2,
           anchor="middle", weight=500)
    s.text(0, 0, "AQB Episode Score", size=13, fill=INK2, anchor="middle", weight=500,
           extra=f'transform="translate({left - 54},{(top + bottom) / 2}) rotate(-90)"')
    off = {"sol": (-13, 5, "end"), "sonnet": (-13, 5, "end")}
    for c in rows:
        x, y = c["aa_index"], c["episodes"]["episode_score"]
        s.add(f'<circle cx="{xv(x):.1f}" cy="{yv(y):.1f}" r="8" fill="{PROVIDER[c["provider"]]}" stroke="{SURFACE}" '
              f'stroke-width="2"><title>{escape(name(c))}: index {x}, AQB {y:.3f}</title></circle>')
        dx, dy, a = off.get(c["key"], (13, 5, "start"))
        s.text(xv(x) + dx, yv(y) + dy, name(c), size=13, fill=INK, anchor=a, weight=500)
    s.save("fig7_aqb_vs_aa")


if __name__ == "__main__":
    fig_aa()
    fig_score()
    fig_cost()
    fig_recall_precision()
    fig_steps()
    fig_outcomes()
    fig_coverage()
