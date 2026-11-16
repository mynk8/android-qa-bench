#!/usr/bin/env python3
"""The paper's illustrated figures, built from real artifacts: device screenshots from calibration
(artifacts/calibration), the agent's own screenshots and transcript (extract_liveview.py), the
forward-port patch and the episode brief.

    python3 docs/paper/figures/extract_liveview.py runs/eps-v4-sonnet tasks-E05
    python3 docs/paper/figures/figs_rich.py
"""
from __future__ import annotations

import json
import sys
from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from paper_figures import FS, FS_SMALL, INK, INK2, MUTED, Fig  # noqa: E402

MONO = "'DejaVu Sans Mono', 'Liberation Mono', monospace"
RED, RED_FILL = "#d03b3b", "#fde8e8"
GREEN, GREEN_FILL = "#1f9a40", "#e5f5e9"
BLUE = "#2a78d6"
ORANGE = "#eb6834"
GREY = "#a8a8a3"
LOOK, TAP, NAV = "#9cc3f2", "#1d5fb4", "#b9b9b4"
LIVE = HERE / "live" / "tasks-E05"


# ---------------------------------------------------------------- primitives
def img(f, x, y, w, h, href, clip=None):
    f.add(f'<image x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" href="{href}" '
          f'preserveAspectRatio="none"{f" clip-path=\"url(#{clip})\"" if clip else ""}/>')


def ring(f, x, y, w, h, color=RED, width=2.2, r=4, dash=""):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    f.add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{r}" fill="none" stroke="{color}" '
          f'stroke-width="{width}"{d}/>')


def phone(f, x, y, w, href, src=(1080, 2400), marks=()):
    """Screenshot in a phone frame; marks are (x, y, w, h, colour[, dash]) in screenshot pixels."""
    h = w * src[1] / src[0]
    p = w * 0.05
    f.add(f'<rect x="{x - p:.1f}" y="{y - 1.8 * p:.1f}" width="{w + 2 * p:.1f}" height="{h + 3.6 * p:.1f}" '
          f'rx="{2.4 * p:.1f}" fill="#202024"/>')
    f.add(f'<rect x="{x + w / 2 - 6:.1f}" y="{y - 1.1 * p:.1f}" width="12" height="1.6" rx="0.8" fill="#55555b"/>')
    img(f, x, y, w, h, href)
    s = w / src[0]
    for m in marks:
        mx, my, mw, mh, col = m[:5]
        ring(f, x + mx * s, y + my * s, mw * s, mh * s, col, 2, dash=m[5] if len(m) > 5 else "")
    return h


def arrow(f, x1, y1, x2, y2, color=INK2, width=1.5, dash="", curve=0):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    if curve:
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2 - curve
        path = f"M{x1:.1f},{y1:.1f} Q{mx:.1f},{my:.1f} {x2:.1f},{y2:.1f}"
    else:
        path = f"M{x1:.1f},{y1:.1f} L{x2:.1f},{y2:.1f}"
    f.add(f'<path d="{path}" fill="none" stroke="{color}" stroke-width="{width}" marker-end="url(#ah)"{d}/>')


def line(f, x1, y1, x2, y2, color=GREY, width=1, dash=""):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    f.add(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{color}" stroke-width="{width}"{d}/>')


def mono(f, x, y, rows, size=10, lead=1.35, fill=INK):
    for i, r in enumerate(rows):
        f.add(f'<text x="{x:.1f}" y="{y + i * size * lead:.1f}" font-family="{MONO}" font-size="{size}" '
              f'fill="{fill}" xml:space="preserve">{escape(r)}</text>')


def check(f, cx, cy, r=8, color=GREEN):
    f.add(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{color}"/>')
    f.add(f'<path d="M{cx - r * .45},{cy + r * .02} L{cx - r * .1},{cy + r * .38} L{cx + r * .48},{cy - r * .35}" '
          f'fill="none" stroke="#fff" stroke-width="{r * .28:.1f}" stroke-linecap="round" stroke-linejoin="round"/>')


def cross(f, cx, cy, r=8, color=RED):
    f.add(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{color}"/>')
    k = r * .38
    f.add(f'<path d="M{cx - k},{cy - k} L{cx + k},{cy + k} M{cx + k},{cy - k} L{cx - k},{cy + k}" '
          f'stroke="#fff" stroke-width="{r * .28:.1f}" stroke-linecap="round"/>')


def bug(f, cx, cy, s=1.0, color=RED):
    """A small beetle: the planted regression."""
    f.add(f'<g transform="translate({cx},{cy}) scale({s})" stroke="{color}" stroke-width="1.6" stroke-linecap="round">'
          '<path d="M-7,-3 L-11,-6 M-7,1 L-12,1 M-7,5 L-11,8 M7,-3 L11,-6 M7,1 L12,1 M7,5 L11,8 M-3,-9 L-5,-12 '
          'M3,-9 L5,-12" fill="none"/>'
          f'<ellipse cx="0" cy="1" rx="7" ry="9" fill="{color}" stroke="none"/>'
          f'<circle cx="0" cy="-8" r="3.6" fill="{color}" stroke="none"/>'
          '<line x1="0" y1="-7" x2="0" y2="10" stroke="#fff" stroke-width="1"/></g>')


def ticket(f, x, y, w=30, h=20, color=ORANGE):
    """A bug report: a card with a folded corner and text lines."""
    c = 6
    f.add(f'<path d="M{x},{y} h{w - c} l{c},{c} v{h - c} h-{w} z" fill="#fff" stroke="{color}" stroke-width="1.4"/>')
    f.add(f'<path d="M{x + w - c},{y} v{c} h{c}" fill="none" stroke="{color}" stroke-width="1.2"/>')
    for i, ww in enumerate((0.6, 0.75, 0.5)):
        line(f, x + 4, y + 6 + i * 4.5, x + 4 + (w - 8) * ww, y + 6 + i * 4.5, color, 1.2)


def flag(f, x, y, color=INK):
    f.add(f'<line x1="{x}" y1="{y}" x2="{x}" y2="{y - 22}" stroke="{color}" stroke-width="1.6"/>')
    f.add(f'<path d="M{x},{y - 22} h14 l-4,5 l4,5 h-14 z" fill="{color}"/>')


def eye(f, cx, cy, color=LOOK):
    f.add(f'<path d="M{cx - 8},{cy} Q{cx},{cy - 7} {cx + 8},{cy} Q{cx},{cy + 7} {cx - 8},{cy} z" fill="none" '
          f'stroke="{color}" stroke-width="1.5"/><circle cx="{cx}" cy="{cy}" r="2.4" fill="{color}"/>')


def tapicon(f, cx, cy, color=TAP):
    f.add(f'<circle cx="{cx}" cy="{cy}" r="3" fill="{color}"/><circle cx="{cx}" cy="{cy}" r="6.5" fill="none" '
          f'stroke="{color}" stroke-width="1.2"/>')


def navicon(f, cx, cy, color=NAV):
    f.add(f'<path d="M{cx + 7},{cy} H{cx - 6} M{cx - 2},{cy - 4} L{cx - 6},{cy} L{cx - 2},{cy + 4}" fill="none" '
          f'stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>')


def bubble(f, x, y, w, rows, tail=None, size=FS_SMALL - 1, italic=True):
    h = 10 + len(rows) * size * 1.3
    f.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h:.1f}" rx="9" fill="#f4f6fb" stroke="#b9c7de"/>')
    if tail:
        tx, ty = tail
        bx = min(max(tx, x + 14), x + w - 14)
        f.add(f'<path d="M{bx - 6},{y + h - 0.5:.1f} L{tx},{ty} L{bx + 6},{y + h - 0.5:.1f}" fill="#f4f6fb" '
              f'stroke="#b9c7de"/>')
        f.add(f'<line x1="{bx - 5.3}" y1="{y + h - 0.6:.1f}" x2="{bx + 5.3}" y2="{y + h - 0.6:.1f}" '
              f'stroke="#f4f6fb" stroke-width="1.6"/>')
    for i, r in enumerate(rows):
        f.text(x + 9, y + 4 + (i + 1) * size * 1.3 - 2, r, size=size, fill=INK,
               extra='font-style="italic"' if italic else "")
    return h


def label(f, x, y, s, size=FS_SMALL, fill=INK2, anchor="middle", weight=400):
    f.text(x, y, s, size=size, fill=fill, anchor=anchor, weight=weight)


# ---------------------------------------------------------------- Figure 1: overview
def fig_overview():
    f = Fig(694)
    f.add('<defs><filter id="sh" x="-10%" y="-10%" width="130%" height="140%"><feDropShadow dx="0" dy="1.5" '
          'stdDeviation="2" flood-color="#000" flood-opacity="0.18"/></filter></defs>')
    # ================= a: how a regression enters a build
    f.panel(4, 18, "a")
    f.text(24, 18, "A real upstream bug, put back into the app", size=FS, weight=700)
    # commit graph
    gx = 28
    line(f, gx, 44, gx, 204, "#c9c9c4", 2)
    for k, cy in enumerate((60, 104, 186)):
        f.add(f'<circle cx="{gx}" cy="{cy}" r="{6 if k == 1 else 4.5}" fill="{"#fff" if k != 1 else ORANGE}" '
              f'stroke="{ORANGE if k == 1 else "#a8a8a3"}" stroke-width="2"/>')
    label(f, gx, 222, "upstream", size=FS_SMALL - 2.5)
    label(f, gx, 233, "history", size=FS_SMALL - 2.5)
    line(f, gx + 7, 104, 48, 104, ORANGE, 1.4)
    # diff card
    dx, dy, dw = 48, 70, 190
    f.add(f'<rect x="{dx}" y="{dy}" width="{dw}" height="72" rx="6" fill="#fff" stroke="#e3c3aa" filter="url(#sh)"/>')
    f.text(dx + 8, dy + 15, "the fix commit (Tasks.org)", size=FS_SMALL - 2, fill=MUTED)
    f.add(f'<rect x="{dx + 1}" y="{dy + 30}" width="{dw - 2}" height="27" fill="{RED_FILL}"/>')
    mono(f, dx + 6, dy + 28, ["  setAscending = ...,", "- showAscending = subtaskMode", "    != SORT_MANUAL", "  )"],
         size=9.2, lead=1.4)
    label(f, dx + dw / 2, dy + 92, "the forward-port removes", size=FS_SMALL - 1.5)
    label(f, dx + dw / 2, dy + 105, "the fix from the app's head", size=FS_SMALL - 1.5)
    arrow(f, dx + dw + 4, 106, 270, 106)
    # buggy phone and lens
    px, pw = 278, 80
    ph = phone(f, px, 36, pw, "assets/t19-buggy-phone.png", src=(720, 1616),
               marks=[(505, 990, 210, 85, RED)])
    label(f, px + pw / 2, 36 + ph + 17, "buggy build", size=FS_SMALL - 1.5)
    s = pw / 720
    hx, hy = px + 505 * s, 36 + 990 * s
    zx, zw = 392, 196
    zh = zw * 100 / 720
    for k, (href, ok, cap) in enumerate((("assets/t19-buggy-row.png", False, "buggy: a sort direction shown for manual order"),
                                         ("assets/t19-fixed-row.png", True, "fixed: no direction for manual order"))):
        zy = 64 + k * 78
        if k == 0:
            line(f, hx + 210 * s, hy, zx, zy, RED, 1, "3 2")
            line(f, hx + 210 * s, hy + 85 * s, zx, zy + zh, RED, 1, "3 2")
        f.add(f'<rect x="{zx - 3}" y="{zy - 3}" width="{zw + 6}" height="{zh + 6:.1f}" rx="6" fill="#fff" '
              f'stroke="{GREEN if ok else RED}" stroke-width="2" filter="url(#sh)"/>')
        img(f, zx, zy, zw, zh, href)
        if not ok:
            ring(f, zx + zw * 0.69, zy + zh * 0.1, zw * 0.3, zh * 0.8, RED, 2, r=5)
        (check if ok else cross)(f, zx + zw + 16, zy + zh / 2, 9)
        label(f, zx, zy + zh + 16, cap, size=FS_SMALL - 2.2, anchor="start")
    label(f, zx + zw / 2, 236, "device checks: FAIL on buggy, PASS on fixed", size=FS_SMALL - 1.5, fill=INK)
    arrow(f, 622, 120, 642, 120)
    # brief document
    bx, by, bw, bh = 650, 34, 112, 170
    f.add(f'<path d="M{bx},{by} h{bw - 16} l16,16 v{bh - 16} h-{bw} z" fill="#fff" stroke="#b5b5b0" '
          f'stroke-width="1.3" filter="url(#sh)"/>')
    f.add(f'<path d="M{bx + bw - 16},{by} v16 h16" fill="none" stroke="#b5b5b0" stroke-width="1.2"/>')
    f.text(bx + 9, by + 17, "Brief", size=FS_SMALL - 1, weight=700)
    for i, ww in enumerate((0.78, 0.6, 0.7, 0.45)):
        line(f, bx + 9, by + 31 + i * 9, bx + 9 + (bw - 22) * ww, by + 31 + i * 9, "#cfcfca", 3)
    f.text(bx + 9, by + 82, "Changed in this build", size=FS_SMALL - 3.5, weight=700)
    for i, (ww, real) in enumerate(((0.8, False), (0.7, True), (0.76, False), (0.82, True))):
        yy = by + 96 + i * 17
        f.add(f'<circle cx="{bx + 12}" cy="{yy}" r="2.6" fill="{RED if real else GREY}"/>')
        line(f, bx + 19, yy, bx + 19 + (bw - 34) * ww, yy, RED if real else "#cfcfca", 3)
        line(f, bx + 19, yy + 6, bx + 19 + (bw - 34) * ww * 0.6, yy + 6, RED if real else "#cfcfca", 3)
    label(f, bx + bw / 2, by + bh + 17, "areas, seed data and", size=FS_SMALL - 1.5)
    label(f, bx + bw / 2, by + bh + 30, "4 release-note lines:", size=FS_SMALL - 1.5)
    f.add(f'<circle cx="{bx + 8}" cy="{by + bh + 41}" r="3" fill="{RED}"/>')
    label(f, bx + 14, by + bh + 45, "2 hide a bug,", size=FS_SMALL - 1.5, anchor="start")
    f.add(f'<circle cx="{bx + 8}" cy="{by + bh + 55}" r="3" fill="{GREY}"/>')
    label(f, bx + 14, by + bh + 59, "2 are decoys", size=FS_SMALL - 1.5, anchor="start")

    # ================= c: scoring this episode
    cx = 784
    f.panel(cx - 10, 18, "c")
    f.text(cx + 10, 18, "Scoring this episode", size=FS, weight=700)
    label(f, cx, 46, "planted bugs", size=FS_SMALL - 1.5, anchor="start")
    for k in range(2):
        bug(f, cx + 14 + k * 40, 70, 1.0)
        check(f, cx + 26 + k * 40, 80, 6)
    label(f, cx + 96, 76, "caught 2 of 2", size=FS_SMALL - 1, anchor="start", fill=INK)
    label(f, cx, 112, "reports filed", size=FS_SMALL - 1.5, anchor="start")
    for k, ok in enumerate((True, True, False, False)):
        ticket(f, cx + k * 32, 122, 26, 19, GREEN if ok else GREY)
    label(f, cx, 160, "2 of 4 were planted bugs", size=FS_SMALL - 1, anchor="start", fill=INK)
    label(f, cx, 184, "ending", size=FS_SMALL - 1.5, anchor="start")
    flag(f, cx + 6, 208, INK)
    label(f, cx + 26, 200, "signed off,", size=FS_SMALL - 1, anchor="start", fill=INK)
    label(f, cx + 26, 212, "not cut off", size=FS_SMALL - 1, anchor="start", fill=INK)
    f.add(f'<rect x="{cx - 4}" y="222" width="166" height="40" rx="7" fill="#f3f3f1"/>')
    label(f, cx + 79, 239, "recall 2/2 · strict pass ✓", size=FS_SMALL - 1, fill=INK)
    label(f, cx + 79, 255, "Episode Score 1.0 × 2/4 = 0.50", size=FS_SMALL - 1, fill=INK, weight=700)

    # ================= b: the episode as the agent lived it
    top = 286
    f.panel(4, top, "b")
    f.text(24, top, "One episode as the agent lived it: Claude Sonnet 5.5 on tasks-E05, 51 actions",
           size=FS, weight=700)
    steps = [s for s in json.loads((LIVE / "timeline.json").read_text()) if s["kind"] == "act"]
    x0, x1, ay = 46, 930, 548
    X = lambda n: x0 + (n - 1) * (x1 - x0) / 50
    # phones
    frames = [(1, "assets/live-001.png", [], "start: list by due date"),
              (5, "assets/live-005.png", [(790, 1408, 285, 106, RED)], "sort sheet: Subtasks"),
              (16, "assets/live-016.png", [(790, 1205, 285, 106, BLUE)], "sets title: Descending"),
              (18, "assets/live-018.png", [(10, 880, 1060, 1000, RED)], "list still A to Z"),
              (49, "assets/live-049.png", [(40, 1050, 1000, 130, GREY, "4 3")], "note link: not a link?")]
    centres = [72, 196, 320, 444, 772]
    pw = 74
    for (n, href, marks, cap), c in zip(frames, centres):
        h = phone(f, c - pw / 2, top + 22, pw, href, marks=marks)
        label(f, c, top + 22 + h + 17, cap, size=FS_SMALL - 2.4, fill=INK)
        line(f, c, top + 22 + h + 22, X(n), ay - 9, "#b5b5b0", 1, "2 2")
        f.add(f'<circle cx="{X(n):.1f}" cy="{ay - 9}" r="2.2" fill="#8d8d88"/>')
    # thought bubbles (the agent's own words)
    def say(x, y, w, rows, tx, ty, to_axis=None):
        h = bubble(f, x, y, w, rows)
        f.add(f'<path d="M{x + 16},{y + h - 0.5:.1f} L{tx},{ty} L{x + 30},{y + h - 0.5:.1f}" fill="#f4f6fb" stroke="#b9c7de"/>')
        f.add(f'<line x1="{x + 16.8}" y1="{y + h - 0.6:.1f}" x2="{x + 29.2}" y2="{y + h - 0.6:.1f}" stroke="#f4f6fb" stroke-width="1.6"/>')
        if to_axis:
            line(f, tx, ty, to_axis, ay - 9, "#9fb3d4", 1, "2 2")
            f.add(f'<circle cx="{to_axis:.1f}" cy="{ay - 9}" r="2.2" fill="#7f97c2"/>')
    say(496, top + 18, 214, ["\u201cSetting title sorting to", "Descending did not reorder the", "list, so I'm re-checking that.\u201d"],
        484, top + 100)
    say(496, top + 118, 214, ["\u201cBug confirmed. Next I'm", "checking the title descending", "sort again.\u201d"], X(27), top + 216, X(27))
    say(822, top + 18, 132, ["\u201cI signed off with", "low confidence", "(0.4).\u201d"], X(51) - 4, top + 96, X(51))
    # action strip
    kind = {"observe": LOOK, "screenshot": LOOK, "tap": TAP, "long_press": TAP, "type_text": TAP,
            "swipe": NAV, "press_key": NAV, "file_report": ORANGE, "sign_off": INK}
    line(f, x0 - 8, ay + 8, x1 + 8, ay + 8, "#8d8d88", 1)
    for s in steps:
        col = kind.get(s["tool"], NAV)
        hh = 18 if s["tool"] in ("file_report", "sign_off") else 12
        f.add(f'<rect x="{X(s["n"]) - 5.5:.1f}" y="{ay + 8 - hh}" width="11" height="{hh}" rx="2" fill="{col}"/>')
    for n in (1, 10, 20, 30, 40, 51):
        line(f, X(n), ay + 8, X(n), ay + 12, "#8d8d88", 1)
        label(f, X(n), ay + 23, str(n), size=FS_SMALL - 2.5, fill=MUTED)
    flag(f, X(51), ay - 12, INK)
    # reports and replies
    reps = [(21, "title Descending:", "no effect", "could not reproduce", "credited later (audit)", "audit"),
            (27, "“My order” shows", "a direction toggle", "confirmed and logged", "", "ok"),
            (43, "title Descending:", "list unchanged", "could not reproduce", "duplicate of 21", "no"),
            (50, "note link is", "plain text", "could not reproduce", "not a planted bug", "no")]
    for n, a, b, reply, note, res in reps:
        cxr = X(n)
        anchor = "end" if n == 50 else "middle"
        tx = cxr + 12 if n == 50 else cxr
        ticket(f, cxr - 14, ay + 32, 28, 20, ORANGE)
        line(f, cxr, ay + 9, cxr, ay + 32, ORANGE, 1.2)
        label(f, tx, ay + 68, a, size=FS_SMALL - 2.3, fill=INK, anchor=anchor)
        label(f, tx, ay + 80, b, size=FS_SMALL - 2.3, fill=INK, anchor=anchor)
        icon_x = (tx - 112) if n == 50 else (cxr - 50)
        (check if res == "ok" else cross)(f, icon_x, ay + 95, 6, GREEN if res == "ok" else (GREY if res != "audit" else RED))
        label(f, icon_x + 10, ay + 99, reply, size=FS_SMALL - 2.6, fill=INK2, anchor="start")
        if note:
            label(f, icon_x + 10, ay + 111, note, size=FS_SMALL - 2.6, fill=MUTED, anchor="start")
    # legend
    lx, ly = 46, ay + 136
    for draw, lab in ((lambda a, b: eye(f, a, b), "look"), (lambda a, b: tapicon(f, a, b), "tap"),
                      (lambda a, b: navicon(f, a, b), "swipe / back"), (lambda a, b: ticket(f, a - 9, b - 7, 18, 13), "report"),
                      (lambda a, b: flag(f, a - 3, b + 8, INK), "sign-off")):
        draw(lx, ly - 4)
        label(f, lx + 13, ly, lab, size=FS_SMALL - 2.2, anchor="start")
        lx += 20 + 6.2 * len(lab) + 14
    f.save("p0_overview")


# ---------------------------------------------------------------- hard regressions, buggy vs fixed
HARD = [  # bug, app, release-note line, crop asset aspect (w, h), ring on buggy (fractions), what is wrong
    ("idlefantasy-0001", "Idle Fantasy", "Shop header: large gold amounts now use a new short format for millions.",
     (330, 56), (0.52, 0.12, 0.47, 0.8), "2,567,890 coins shown as 2.6M; the format floors to 2.5M"),
    ("iris-0012", "Iris Gallery", "Media tab blank-state illustration: its caption is now built from one constant string resource.",
     (420, 90), (0.12, 0.2, 0.76, 0.6), "the Videos filter says “No photos found”"),
    ("tasks-0012", "Tasks.org", "Date badges on task rows: the badge for each date field is now built independently of the others.",
     (720, 190), (0.14, 0.56, 0.32, 0.26), "a start-date chip repeats the due date"),
    ("featherline-0018", "Featherline", "Night owl mode in the group editor: the explanatory caption now builds its cut-off text separately.",
     (720, 110), (0.37, 0.3, 0.13, 0.36), "“04:00” among times written as AM/PM"),
]


def fig_hard():
    rows = json.loads((HERE.parent / "data" / "hard28.json").read_text()) if (HERE.parent / "data" / "hard28.json").exists() else []
    info = {r["bug"]: r for r in rows}
    f = Fig(500)
    zw = 290
    y = 30
    for k, (b, app, note, (cw, ch), (rx, ry, rw, rh), what) in enumerate(HARD):
        zh = zw * ch / cw
        f.text(4, y + 14, app, size=FS, weight=700)
        import textwrap
        wl = textwrap.wrap("release note: “" + note + "”", 56)
        for i, r in enumerate(wl[:2]):
            f.text(4, y + 30 + i * 13, r + ("…" if i == 1 and len(wl) > 2 else ""), size=FS_SMALL - 2.5, fill=INK2)
        y += 13
        n_caught = len(info.get(b, {}).get("caught_by", []))
        depth = max((v or 0) for v in info.get(b, {}).get("depth", {"x": 0}).values())
        f.text(4, y + 48, what, size=FS_SMALL - 1, fill=INK)
        f.text(4, y + 65, f"caught by {n_caught} of 6 configurations; up to {depth} actions on this screen",
               size=FS_SMALL - 2, fill=RED if n_caught == 0 else INK2, weight=700 if n_caught == 0 else 400)
        for j, (v, col) in enumerate((("buggy", RED), ("fixed", GREEN))):
            x = 350 + j * (zw + 24)
            f.add(f'<rect x="{x - 3}" y="{y - 3}" width="{zw + 6}" height="{zh + 6:.1f}" rx="5" fill="#fff" stroke="{col}" '
                  f'stroke-width="1.8"/>')
            img(f, x, y, zw, zh, f"assets/{b}-{v}.png")
            if j == 0:
                ring(f, x + rx * zw, y + ry * zh, rw * zw, rh * zh, RED, 2.2, r=5)
            if k == 0:
                f.text(x + zw / 2, 14, v, size=FS_SMALL - 1, fill=col, anchor="middle", weight=700)
        y += max(zh - 13, 60) + 36
    f.save("p7_hard")


# ---------------------------------------------------------------- catch matrix
def fig_matrix():
    sys.path.insert(0, str(HERE.parents[2]))
    from tools import changelog_coverage as cc
    from paper_figures import ORDER, PROVIDER, name as cname
    root = HERE.parents[2]
    found, bugs = {}, set()
    for c in ORDER:
        fs = set()
        for r in c["runs"]:
            run = root / r
            keep = cc.scored_run_ids(run)
            for p in run.glob("episodes/*/*/result.json"):
                d = json.loads(p.read_text())
                if d["run_id"] in keep:
                    fs |= set(d["found"] or [])
                    bugs |= set(d["required"])
        found[c["key"]] = fs
    apps = sorted({b.split("-")[0] for b in bugs})
    cols = []
    for a in apps:
        bs = sorted((b for b in bugs if b.startswith(a + "-")), key=lambda b: (-sum(b in found[c["key"]] for c in ORDER), b))
        cols.append((a, bs))
    f = Fig(300)
    left, top, cw, rh, gap = 196, 64, 7.4, 22, 8
    x = left
    names = {"amaze": "Amaze", "ankidroid": "AnkiDroid", "featherline": "Featherline", "idlefantasy": "Idle Fantasy",
             "iris": "Iris", "markor": "Markor", "minus": "Minus", "nerdcalci": "NerdCalci", "tasks": "Tasks"}
    for r, c in enumerate(ORDER):
        f.text(left - 10, top + r * rh + rh / 2 + 4.5, cname(c), size=FS_SMALL - 1.5, anchor="end")
    f.text(left - 10, top - 24, "agents that caught it", size=FS_SMALL - 2, fill=MUTED, anchor="end")
    for a, bs in cols:
        for b in bs:
            n = sum(b in found[c["key"]] for c in ORDER)
            hb = n * 6
            f.add(f'<rect x="{x:.1f}" y="{top - 8 - hb}" width="{cw - 1.2:.1f}" height="{hb}" fill="{"#8d8d88" if n else RED}"/>')
            if n == 0:
                f.add(f'<rect x="{x:.1f}" y="{top - 10}" width="{cw - 1.2:.1f}" height="2" fill="{RED}"/>')
            for r, c in enumerate(ORDER):
                hit = b in found[c["key"]]
                f.add(f'<rect x="{x:.1f}" y="{top + r * rh + 2}" width="{cw - 1.2:.1f}" height="{rh - 4}" rx="1" '
                      f'fill="{PROVIDER[c["provider"]] if hit else "#eeeeec"}"/>')
            x += cw
        f.line(x - cw * len(bs) + 1, top + len(ORDER) * rh + 8, x - 2, top + len(ORDER) * rh + 8, stroke="#8d8d88", width=1.2)
        f.text(x - cw * len(bs) / 2 - 1, top + len(ORDER) * rh + 24, names.get(a, a), size=FS_SMALL - 2.2, anchor="middle")
        x += gap
    none = sum(1 for _, bs in cols for b in bs if not any(b in found[c["key"]] for c in ORDER))
    f.text(left, top + len(ORDER) * rh + 50, f"Each column is one planted regression (92), grouped by app and sorted by how many "
           f"agents caught it; red: caught by none ({none}).", size=FS_SMALL - 2, fill=INK2)
    f.save("p8_matrix")


if __name__ == "__main__":
    fig_overview()
    fig_hard()
    fig_matrix()
