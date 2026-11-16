#!/usr/bin/env python3
"""Doom-loop guard for benchmark agents.

    loop_guard.py [--format claude|codex|auto] -- <agent command ...>

Starts the agent command, passes its stdout through unchanged, and watches only the model's
own words (assistant text and reasoning; never tool results, whose UI dumps repeat by nature).
When the tail of those words turns degenerate, the same word or sentence over and over, the
guard kills the agent's process group, prints one {"type":"result","subtype":"error_doom_loop"}
line and exits 4. The harness records exit code 4 as the episode outcome "doom_loop" (an agent
failure, scored like a run cut off at the action cap).

Detection, checked on the last WINDOW characters of model text every CHECK_EVERY new characters:
  periodic   the tail is an exact repetition of one unit (1 to MAX_PERIOD characters long) for at
             least MIN_REPEAT_CHARS characters and MIN_REPEATS copies ("no no no no ...",
             "Let me check the list. Let me check the list. ...")
  compress   the last WINDOW characters compress to under MAX_RATIO of their size (near-repeats
             with small changes, such as counters); normal model prose stays well above it
Thresholds were checked against every Sonnet 5.5 and Haiku 5.5 transcript of the v4 episode runs
(tools/loop_guard_check.py): no false alarm.
"""
from __future__ import annotations

import json
import os
import re
import signal
import subprocess
import sys
import zlib

WINDOW = 4000
CHECK_EVERY = 200
MAX_PERIOD = 400
MIN_REPEAT_CHARS = 600
MIN_REPEATS = 8
MAX_RATIO = 0.10


def periodic(t: str) -> tuple[int, int] | None:
    """(period, repeated chars) when the end of t repeats one unit, else None."""
    n = len(t)
    for p in range(1, min(MAX_PERIOD, n // MIN_REPEATS) + 1):
        need = max(MIN_REPEAT_CHARS, MIN_REPEATS * p)
        if need > n:
            continue
        s = t[n - need:]
        if s[:-p] == s[p:]:
            return p, need
    return None


def ratio(t: str) -> float:
    b = t.encode("utf-8", "replace")
    return len(zlib.compress(b, 9)) / max(1, len(b))


# DeepSeek's own loop shapes, from the dsh-doom-loop-guard plugin's "standard" preset (calibrated
# on 16k real DeepSeek reasoning chains): dash fill, stacked full-width brackets, and very short
# sentences repeated with tiny gaps ("好。执行。").
DASH_RUN = re.compile(r"(?:——\*{0,2}\s*){3,}")
PAREN_RUN = re.compile(r"（{4,}")
SENT_SPLIT = re.compile(r"[。！？!?；;\n]+")
WORDLIKE = re.compile(r"[\u4e00-\u9fa5]|[A-Za-z]{2,}")
MAX_DASH_RUN, MAX_PAREN_RUN = 800, 200
SHORT_REPEAT, SHORT_MAX_GAP, SHORT_WINDOW = 15, 8, 800


def deepseek_shapes(t: str) -> str | None:
    for rx, limit, name in ((DASH_RUN, MAX_DASH_RUN, "dash fill"), (PAREN_RUN, MAX_PAREN_RUN, "stacked brackets")):
        longest = max((len(m.group(0)) for m in rx.finditer(t)), default=0)
        if longest >= limit:
            return f"{name}: a run of {longest} characters"
    w = t[-SHORT_WINDOW:]
    pos: dict[str, list[int]] = {}
    i = 0
    for part in SENT_SPLIT.split(w):
        s = part.strip()
        if 1 <= len(s) <= 10 and WORDLIKE.search(s):
            pos.setdefault(s, []).append(i)
        i += len(part) + 1
    for s, ps in pos.items():
        if len(ps) >= SHORT_REPEAT and min(b - a for a, b in zip(ps, ps[1:])) <= SHORT_MAX_GAP + len(s):
            return f"short sentence {s!r} repeated {len(ps)} times"
    return None


def verdict(tail: str) -> str | None:
    ds = deepseek_shapes(tail)
    if ds:
        return ds
    pr = periodic(tail)
    if pr:
        return f"periodic: a {pr[0]}-character unit repeated over the last {pr[1]} characters"
    if len(tail) >= WINDOW:
        r = ratio(tail[-WINDOW:])
        if r < MAX_RATIO:
            return f"compress: last {WINDOW} characters compress to {r:.3f} of their size"
    return None


class TextTap:
    """Pulls the model's own words out of one agent's JSON event stream."""

    def __init__(self, fmt: str = "auto") -> None:
        self.fmt = fmt
        self.saw_deltas = False

    def texts(self, line: str) -> list[str]:
        try:
            e = json.loads(line)
        except Exception:
            return []
        if not isinstance(e, dict):
            return []
        t = e.get("type")
        # Claude Code stream-json
        if t == "stream_event":
            self.saw_deltas = True
            d = (e.get("event") or {}).get("delta") or {}
            return [d[k] for k in ("text", "thinking") if isinstance(d.get(k), str)]
        if t == "assistant":
            if self.saw_deltas:  # the full message repeats what the deltas already showed
                return []
            out = []
            for b in (e.get("message") or {}).get("content") or []:
                if isinstance(b, dict) and b.get("type") in ("text", "thinking"):
                    out.append(b.get("text") or b.get("thinking") or "")
            return out
        # Codex --json
        if t in ("item.completed", "item.updated"):
            it = e.get("item") or {}
            if it.get("type") in ("agent_message", "reasoning") and isinstance(it.get("text"), str):
                return [it["text"]]
            return []
        # DeepSeek Harness --json: finished reasoning and text blocks ("final" repeats the last text)
        if t in ("thinking", "text") and isinstance(e.get("text"), str):
            return [e["text"]]
        if t == "final":
            return []
        # generic: assistant-side text deltas, never tool output
        if self.fmt == "auto" and isinstance(t, str) and not re.search(r"tool|user|result|observation", t):
            out = []
            for k in ("delta", "text", "reasoning", "thinking", "content"):
                v = e.get(k)
                if isinstance(v, str):
                    out.append(v)
                elif isinstance(v, dict):
                    out += [v[x] for x in ("text", "reasoning", "thinking") if isinstance(v.get(x), str)]
            return out
        return []


class Watch:
    def __init__(self) -> None:
        self.buf = ""
        self.since = 0

    def feed(self, s: str) -> str | None:
        if not s:
            return None
        self.buf = (self.buf + s)[-WINDOW * 2:]
        self.since += len(s)
        if self.since < CHECK_EVERY:
            return None
        self.since = 0
        return verdict(re.sub(r"\s+", " ", self.buf)[-WINDOW:])


def main() -> int:
    args = sys.argv[1:]
    fmt = "auto"
    if args[:1] == ["--format"]:
        fmt, args = args[1], args[2:]
    if args[:1] == ["--"]:
        args = args[1:]
    if not args:
        print("usage: loop_guard.py [--format claude|codex|auto] -- <command ...>", file=sys.stderr)
        return 2
    proc = subprocess.Popen(args, stdout=subprocess.PIPE, start_new_session=True)
    tap, watch = TextTap(fmt), Watch()
    reason = None
    for raw in proc.stdout:
        sys.stdout.buffer.write(raw)
        sys.stdout.buffer.flush()
        for s in tap.texts(raw.decode("utf-8", "replace")):
            reason = watch.feed(s)
            if reason:
                break
        if reason:
            break
    if reason:
        try:
            os.killpg(proc.pid, signal.SIGTERM)
            proc.wait(timeout=10)
        except Exception:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except Exception:
                pass
        print(json.dumps({"type": "result", "subtype": "error_doom_loop", "is_error": True,
                          "reason": reason, "tail": watch.buf[-300:]}), flush=True)
        return 4
    return proc.wait()


if __name__ == "__main__":
    raise SystemExit(main())
