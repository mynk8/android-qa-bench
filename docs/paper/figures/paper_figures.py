#!/usr/bin/env python3
"""Journal-style figures for the paper (docs/paper/figures/p*.pdf).

    python3 docs/paper/data/collect.py
    python3 docs/paper/figures/paper_figures.py

Style (after common journal figure rules): Helvetica-class sans, about 7 pt text at the printed
size (figures are drawn for a 165 mm text width), no in-figure titles (the caption carries them),
no gridlines, left/bottom spines only, panel labels (a), (b), a restrained palette (provider colour
plus status colours for outcomes), direct labels instead of legends where possible, vector output.
make_figures.py keeps the leaderboard-style versions for slides and the web.
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

FONT = "'Nimbus Sans', Helvetica, Arial, 'Liberation Sans', sans-serif"
W = 960                       # drawing units across the 165 mm text width: 1 unit = 0.49 pt
TEXT_MM = 165
FS, FS_SMALL, FS_PANEL = 14.5, 12.5, 17   # about 7 pt, 6 pt, 8.3 pt printed
INK, INK2, MUTED, SPINE = "#111111", "#444444", "#7a7a7a", "#333333"
LIGHT = "#f2f2f0"
PROVIDER = {"OpenAI": "#2a78d6", "Anthropic": "#eb6834", "DeepSeek": "#1baf7a"}
GOOD, CRITICAL, WARNING, CUT = "#0ca30c", "#d03b3b", "#fab219", "#8c8c8c"
BLUE = ("#86b6ef", "#2a78d6", "#104281")


def name(c):
    return f"{c['label']} ({c['setting']})" if c["setting"] != "default" else c["label"]


ORDER = sorted(DATA, key=lambda c: -c["episodes"]["bug_recall"])   # rows ranked by recall


class Fig:
    def __init__(self, h):
        self.h, self.parts = h, []

    def add(self, s):
        self.parts.append(s)

    def text(self, x, y, s, size=FS, fill=INK, anchor="start", weight=400, extra=""):
        self.add(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" text-anchor="{anchor}" '
                 f'font-weight="{weight}" {extra}>{escape(s)}</text>')

    def lines(self, x, y, rows, size=FS, fill=INK, anchor="middle", lead=1.25, weight=400):
        for i, r in enumerate(rows):
            w = weight if i == 0 and weight != 400 else 400
            self.text(x, y + i * size * lead, r, size=size, fill=fill if i == 0 else INK2, anchor=anchor, weight=w)

    def line(self, x1, y1, x2, y2, stroke=SPINE, width=1.2, dash=""):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{stroke}" '
                 f'stroke-width="{width}"{d}/>')

    def panel(self, x, y, label):
        self.text(x, y, label, size=FS_PANEL, weight=700)

    def save(self, stem):
        mm_h = TEXT_MM * self.h / W
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {self.h}" width="{TEXT_MM}mm" '
               f'height="{mm_h:.1f}mm" font-family="{FONT}">\n'
               '<defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
               f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{INK2}"/></marker></defs>\n'
               '<rect width="100%" height="100%" fill="#ffffff"/>\n' + "\n".join(self.parts) + "\n</svg>\n")
        p = HERE / f"{stem}.svg"
        p.write_text(svg)
        if shutil.which("rsvg-convert"):
            subprocess.run(["rsvg-convert", "-f", "pdf", "-o", str(HERE / f"{stem}.pdf"), str(p)], check=True)
            subprocess.run(["rsvg-convert", "-d", "300", "-p", "300", "-o", str(HERE / f"{stem}.png"), str(p)],
                           check=True)
        print("wrote", p.name)


class Axes:
    """A plot area with left/bottom spines, outward ticks and no gridlines."""

    def __init__(self, f, x, y, w, h, xr, yr, logx=False):
        self.f, self.x, self.y, self.w, self.h = f, x, y, w, h
        self.xr, self.yr, self.logx = xr, yr, logx

    def X(self, v):
        t = (lambda u: math.log10(u)) if self.logx else (lambda u: u)
        return self.x + self.w * (t(v) - t(self.xr[0])) / (t(self.xr[1]) - t(self.xr[0]))

    def Y(self, v):
        return self.y + self.h - self.h * (v - self.yr[0]) / (self.yr[1] - self.yr[0])

    def spines(self, xticks, yticks, xfmt=str, yfmt=str, xlabel="", ylabel=""):
        f, b = self.f, self.y + self.h
        f.line(self.x, b, self.x + self.w, b)
        f.line(self.x, self.y, self.x, b)
        for t in xticks:
            f.line(self.X(t), b, self.X(t), b + 5)
            f.text(self.X(t), b + 19, xfmt(t), size=FS_SMALL, fill=INK2, anchor="middle")
        for t in yticks:
            f.line(self.x - 5, self.Y(t), self.x, self.Y(t))
            f.text(self.x - 9, self.Y(t) + 4.5, yfmt(t), size=FS_SMALL, fill=INK2, anchor="end")
        if xlabel:
            f.text(self.x + self.w / 2, b + 40, xlabel, size=FS, anchor="middle")
        if ylabel:
            f.text(0, 0, ylabel, size=FS, anchor="middle",
                   extra=f'transform="translate({self.x - 46},{self.y + self.h / 2}) rotate(-90)"')

    def dot(self, c, xv, yv, label_dx=10, label_dy=5, anchor="start", r=6.5):
        f = self.f
        f.add(f'<circle cx="{self.X(xv):.1f}" cy="{self.Y(yv):.1f}" r="{r}" fill="{PROVIDER[c["provider"]]}" '
              f'stroke="#ffffff" stroke-width="1.5"/>')
        f.text(self.X(xv) + label_dx, self.Y(yv) + label_dy, name(c), size=FS_SMALL, anchor=anchor)


# ---------------------------------------------------------------- 2. headline metrics
def fig_forest():
    f = Fig(300)
    metrics = [("bug_recall", "bug_recall_ci95", "Recall", 100, (0, 80), [0, 20, 40, 60, 80], "%"),
               ("solve_rate", "solve_rate_ci95", "Strict pass", 100, (0, 50), [0, 10, 20, 30, 40, 50], "%"),
               ("episode_score", "episode_score_ci95", "Episode Score", 1, (0, 0.6), [0, 0.2, 0.4, 0.6], "")]
    left, top, rowh = 200, 34, 34
    pw, gap = 210, 46
    n = len(ORDER)
    for r, c in enumerate(ORDER):
        f.text(left - 12, top + r * rowh + rowh / 2 + 5, name(c), size=FS_SMALL, anchor="end")
    for k, (m, ci, title, scale, xr, ticks, unit) in enumerate(metrics):
        x = left + k * (pw + gap)
        f.panel(x - 2 if k else 4, 18, "abc"[k])
        f.text(x + pw / 2, 18, title, size=FS, anchor="middle", weight=700)
        ax = Axes(f, x, top, pw, n * rowh, xr, (0, n))
        ax.spines(ticks, [], xfmt=lambda t, s=scale, u=unit: (f"{t:g}" if s == 100 else f"{t:.1f}") + u)
        for r, c in enumerate(ORDER):
            e = c["episodes"]
            v, (lo, hi) = e[m] * scale, [q * scale for q in e[ci]]
            yy = top + r * rowh + rowh / 2
            f.line(ax.X(lo), yy, ax.X(hi), yy, stroke=INK2, width=1.4)
            f.add(f'<circle cx="{ax.X(v):.1f}" cy="{yy:.1f}" r="5.5" fill="{PROVIDER[c["provider"]]}" '
                  f'stroke="#ffffff" stroke-width="1.2"/>')
            f.text(ax.X(hi) + 7, yy + 4.5, f"{v:.0f}" if scale == 100 else f"{v:.2f}", size=FS_SMALL, fill=INK2)
    f.save("p2_headline")


# ---------------------------------------------------------------- 3. recall vs precision | endings
def fig_recall_endings():
    f = Fig(330)
    f.panel(4, 18, "a")
    ax = Axes(f, 66, 30, 330, 240, (0, 0.7), (0, 0.7))
    for F1 in (0.2, 0.3, 0.4, 0.5):
        pts = []
        for i in range(160):
            p = 0.06 + i * (0.7 - 0.06) / 159
            if 2 * p - F1 <= 0:
                continue
            r = F1 * p / (2 * p - F1)
            if 0 <= r <= 0.7:
                pts.append(f"{ax.X(p):.1f},{ax.Y(r):.1f}")
        f.add(f'<polyline points="{" ".join(pts)}" fill="none" stroke="#c9c9c4" stroke-width="1" stroke-dasharray="3 3"/>')
        f.text(ax.X(0.7) + 3, ax.Y(F1 * 0.7 / (1.4 - F1)) + 4, f"F1 {F1}", size=FS_SMALL - 1, fill=MUTED)
    ax.spines([0, 0.2, 0.4, 0.6], [0, 0.2, 0.4, 0.6], xfmt=lambda t: f"{t:.0%}", yfmt=lambda t: f"{t:.0%}",
              xlabel="Report precision", ylabel="Recall")
    off = {"sol": (10, -4, "start"), "deepseek": (10, -8, "start"), "sonnet": (10, 16, "start"),
           "haiku": (-10, 5, "end"), "luna-max": (-10, 5, "end"), "luna-med": (-10, 18, "end")}
    for c in DATA:
        dx, dy, a = off[c["key"]]
        ax.dot(c, c["episodes"]["report_precision"], c["episodes"]["bug_recall"], dx, dy, a)
    # (b) endings
    f.panel(470, 18, "b")
    segs = [("correct_signoff", "Correct sign-off", GOOD, "#ffffff"),
            ("false_signoff", "Signed off, bugs missed", CRITICAL, "#ffffff"),
            ("gave_up", "No sign-off", WARNING, INK),
            ("cut_off", "Cut off", CUT, "#ffffff")]
    x0, x1, top, bh, g = 640, 950, 30, 25, 11
    for r, c in enumerate(ORDER):
        st = c["episodes"]["stopping"]
        y = top + r * (bh + g)
        f.text(x0 - 9, y + bh / 2 + 5, name(c), size=FS_SMALL, anchor="end")
        x = x0
        for k, lab, col, ink in segs:
            v = st.get(k, 0)
            w = (x1 - x0) * v
            if w <= 0:
                continue
            f.add(f'<rect x="{x:.1f}" y="{y}" width="{max(w - 1.5, 0.5):.1f}" height="{bh}" fill="{col}"/>')
            if w > 34:
                f.text(x + 5, y + bh / 2 + 4.5, f"{v:.0%}", size=FS_SMALL, fill=ink, weight=700)
            x += w
    ly = top + len(ORDER) * (bh + g) + 10
    lx = 470
    for k, lab, col, _ in segs:
        f.add(f'<rect x="{lx}" y="{ly - 9}" width="10" height="10" fill="{col}"/>')
        f.text(lx + 14, ly, lab, size=FS_SMALL, fill=INK2)
        lx += 14 + 6.3 * len(lab) + 16
    f.save("p3_recall_endings")


# ---------------------------------------------------------------- 4. effort and cost
def fig_effort_cost():
    f = Fig(390)
    f.panel(4, 18, "a")
    ax = Axes(f, 66, 30, 360, 300, (0, 320), (0, 0.5))
    ax.f.line(ax.X(300), ax.y, ax.X(300), ax.y + ax.h, stroke=CRITICAL, width=1, dash="4 3")
    f.text(ax.X(300) - 5, ax.y + 12, "cap", size=FS_SMALL, fill=INK2, anchor="end")
    ax.spines([0, 100, 200, 300], [0, 0.1, 0.2, 0.3, 0.4, 0.5], yfmt=lambda t: f"{t:.1f}",
              xlabel="Device actions per episode (mean)", ylabel="Episode Score")
    off = {"sonnet": (10, 5, "start"), "sol": (-10, -7, "end"), "haiku": (-10, -7, "end"),
           "luna-max": (-10, -8, "end"), "deepseek": (-10, 17, "end"), "luna-med": (10, 9, "start")}
    for c in DATA:
        dx, dy, a = off[c["key"]]
        ax.dot(c, c["episodes"]["steps_mean"], c["episodes"]["episode_score"], dx, dy, a)
    f.panel(490, 18, "b")
    bx = Axes(f, 556, 30, 380, 300, (0.01, 1), (0, 0.5), logx=True)
    bx.spines([0.01, 0.03, 0.1, 0.3, 1], [0, 0.1, 0.2, 0.3, 0.4, 0.5], xfmt=lambda t: f"${t:g}",
              yfmt=lambda t: f"{t:.1f}", xlabel="Cost per episode (USD, API list prices, log)", ylabel="Episode Score")
    off = {"sonnet": (-10, 5, "end"), "sol": (-10, -6, "end"), "haiku": (-10, -8, "end"),
           "luna-max": (10, 5, "start"), "deepseek": (10, 5, "start"), "luna-med": (10, 5, "start")}
    for c in DATA:
        dx, dy, a = off[c["key"]]
        bx.dot(c, c["episodes"]["cost_usd_per_episode"], c["episodes"]["episode_score"], dx, dy, a)
    f.save("p4_effort_cost")


# ---------------------------------------------------------------- 5. changelog coverage
def fig_coverage():
    f = Fig(345)
    keys = [("reached", "Reached"), ("worked", "Exercised (6+ actions)"), ("caught", "Caught")]
    left, top, rowh = 200, 26, 38
    ax = Axes(f, left, top, 700, len(ORDER) * rowh, (0, 92), (0, len(ORDER)))
    ax.spines([0, 23, 46, 69, 92], [], xfmt=lambda t: f"{t}", xlabel="Release-note lines that hide a regression (of 92)")
    for r, c in enumerate(ORDER):
        cov = c["coverage"]["real"]
        y = top + r * rowh
        f.text(left - 12, y + rowh / 2 + 5, name(c), size=FS_SMALL, anchor="end")
        for j, (k, _) in enumerate(keys):
            f.add(f'<rect x="{left}" y="{y + 5 + j * 9.5:.1f}" width="{ax.X(cov[k]) - left:.1f}" height="8.5" fill="{BLUE[j]}"/>')
        f.text(ax.X(cov["reached"]) + 6, y + 14, f"{cov['reached']}", size=FS_SMALL - 1, fill=INK2)
        f.text(ax.X(cov["caught"]) + 6, y + 33, f"{cov['caught']}", size=FS_SMALL - 1, fill=INK, weight=700)
    lx = left
    ly = top + len(ORDER) * rowh + 70
    for j, (_, lab) in enumerate(keys):
        f.add(f'<rect x="{lx}" y="{ly - 9}" width="10" height="10" fill="{BLUE[j]}"/>')
        f.text(lx + 14, ly, lab, size=FS_SMALL, fill=INK2)
        lx += 14 + 6.3 * len(lab) + 20
    f.save("p5_coverage")


# ---------------------------------------------------------------- 6. AQB vs AA index
def fig_aa():
    f = Fig(280)
    ax = Axes(f, 270, 20, 420, 200, (15, 40), (0, 0.5))
    ax.spines([15, 20, 25, 30, 35, 40], [0, 0.1, 0.2, 0.3, 0.4, 0.5], yfmt=lambda t: f"{t:.1f}",
              xlabel="Artificial Analysis Intelligence Index (same model and effort)", ylabel="AQB Episode Score")
    off = {"sonnet": (-10, 5, "end"), "sol": (-10, 5, "end"), "luna-max": (10, 5, "start"), "luna-med": (10, 5, "start")}
    for c in DATA:
        if c.get("aa_index") is not None:
            dx, dy, a = off[c["key"]]
            ax.dot(c, c["aa_index"], c["episodes"]["episode_score"], dx, dy, a)
    f.save("p6_aa")


if __name__ == "__main__":
    fig_forest()
    fig_recall_endings()
    fig_effort_cost()
    fig_coverage()
    fig_aa()
