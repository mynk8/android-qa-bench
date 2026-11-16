#!/usr/bin/env python3
"""Shared helpers for the episode/case eval harness.

The QA agent talks to the harness over a stdin/stdout JSONL protocol
(one JSON object per line). See tools/dummy_agent.py for an example.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dataset_tools.device_api import Device
from dataset_tools.matcher import episode_outcome, load_key

DATASET = ROOT / "dataset"
PRIVATE = ROOT / "private"

REPLY = {
    "hit": "Developer: thanks, confirmed. A new build is installed with a fix. (build {n})",
    "hit_claim": (
        "Developer: thanks, confirmed. It's fixed now. "
        "A new build is installed with a fix. (build {n})"
    ),
    "already_fixed": (
        "Developer: that one was fixed in build {k}. Please re-test on the current build."
    ),
    "hit_fast": "Developer: thanks, confirmed and logged. Keep testing the current build.",
    "duplicate": "Developer: that one is already logged.",
    "no_match": "Developer: could not reproduce with the steps given.",
    "malformed": "Developer: please use the report format.",
    "leftover_known": (
        "Developer: known issue. This is already tracked and is not part of the current sweep."
    ),
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_manifest(dataset: Path = DATASET) -> dict:
    return load_json(dataset / "manifest.json")


def load_episode(episode_id: str, dataset: Path = DATASET) -> dict:
    d = dataset / "episodes" / episode_id
    ep = load_json(d / "episode.json")
    ep["_brief"] = (d / "brief.md").read_text(encoding="utf-8")
    ep["_dir"] = str(d)
    return ep


def load_case(case_id: str, dataset: Path = DATASET) -> dict:
    d = dataset / "cases" / case_id
    case = load_json(d / "case.json")
    case["_agent_input"] = (d / "agent_input.md").read_text(encoding="utf-8")
    case["_dir"] = str(d)
    return case


def load_app(app_id: str, dataset: Path = DATASET) -> dict:
    return load_json(dataset / "apps" / app_id / "app.json")


def load_bug(bug_id: str, dataset: Path = DATASET) -> dict:
    return load_json(dataset / "bugs" / bug_id / "bug.json")


def load_bug_keys(bug_ids: list[str], dataset: Path = DATASET) -> dict:
    return {b: load_key(dataset / "bugs" / b) for b in bug_ids}


def load_case_texts(bug_ids: list[str], dataset: Path = DATASET) -> dict:
    texts = {}
    for b in bug_ids:
        cases = sorted((dataset / "cases").glob(f"{b}-*/agent_input.md"))
        if cases:
            texts[b] = cases[0].read_text(encoding="utf-8")
    return texts


def load_reference_report(bug_id: str, which: str = "correct", dataset: Path = DATASET) -> dict:
    refs = load_json(dataset / "bugs" / bug_id / "reference_reports.json")
    report = dict(refs[which])
    report.setdefault("type", "bug_report")
    return report


def mask_for(bugs: list[str], unfixed: set[str]) -> str:
    return "".join("1" if b in unfixed else "0" for b in bugs)


def present_on(episode: dict, unfixed: set[str]) -> set[str]:
    """Bugs whose symptom is observable on this subset (not merely unfixed)."""
    bugs = list(episode["bugs"])
    mask = mask_for(bugs, unfixed)
    obs = episode.get("observable") or {}
    if mask in obs:
        return {b for b, v in obs[mask].items() if v}
    return set(unfixed) & set(bugs)


def format_reply(kind: str, *, build_n: int | None = None, fixed_in: int | None = None,
                 claim: str = "none") -> str:
    if kind == "hit":
        tmpl = REPLY["hit_claim"] if claim == "developer" else REPLY["hit"]
        return tmpl.format(n=build_n)
    if kind == "already_fixed":
        k = fixed_in if fixed_in is not None else "an earlier"
        return REPLY["already_fixed"].format(k=k)
    if kind == "leftover_known":
        return REPLY["leftover_known"]
    if kind == "malformed":
        return REPLY["malformed"]
    if kind in ("hit_fast", "duplicate"):
        return REPLY[kind]
    return REPLY["no_match"]


def classify_report(report: dict, episode: dict, unfixed: set[str], bug_keys: dict,
                    case_texts: dict | None, credited=()) -> dict:
    """Wrap matcher.episode_outcome; masked-but-unfixed hits are no_match. `credited`: bugs this
    episode already credited, so a report that matches several prefers a new one."""
    present = present_on(episode, unfixed)
    state = dict(episode)
    state["present"] = present
    state["credited"] = sorted(credited)
    result = episode_outcome(report, state, bug_keys, case_texts)
    if result.get("kind") == "already_fixed":
        still = [b for b in (result.get("bugs") or []) if b in unfixed]
        if still:
            return {"kind": "no_match", "reply": REPLY["no_match"], "bugs": still,
                    "reason": "masked_or_not_observable"}
    return result


def apk_path(app_id: str, build_id: str, dataset: Path = DATASET) -> Path:
    return dataset / "apps" / app_id / "builds" / f"{build_id}.apk"


# ---------------------------------------------------------------------------
# Fake device (dry-run, no APKs)
# ---------------------------------------------------------------------------

class FakeDevice(Device):
    """Records Device calls; never talks to an emulator or an APK."""

    def __init__(self) -> None:
        self.log: list[tuple] = []
        self.installed: str | None = None
        self.package: str | None = None
        self.landscape = False

    def install(self, build_id: str) -> None:
        self.installed = build_id
        self.log.append(("install", build_id))

    def launch(self, package: str) -> None:
        self.package = package
        self.log.append(("launch", package))

    def force_stop(self, package: str) -> None:
        self.log.append(("force_stop", package))

    def rotate(self, landscape: bool) -> None:
        self.landscape = landscape
        self.log.append(("rotate", landscape))

    def tap(self, selector: dict) -> None:
        self.log.append(("tap", selector))

    def input_text(self, selector: dict, text: str) -> None:
        self.log.append(("input_text", selector, text))

    def back(self) -> None:
        self.log.append(("back",))

    def home(self) -> None:
        self.log.append(("home",))

    def scroll_to(self, selector: dict) -> bool:
        self.log.append(("scroll_to", selector))
        return True

    def wait_idle(self, timeout_s: float = 5) -> None:
        self.log.append(("wait_idle", timeout_s))

    def ui(self) -> list[dict]:
        self.log.append(("ui",))
        return []

    def screenshot(self) -> bytes:
        self.log.append(("screenshot",))
        return b""

    def sql(self, db_name: str, query: str, params: tuple = ()) -> list[dict[str, Any]]:
        self.log.append(("sql", db_name, query, params))
        return []

    def read_file(self, app_relative_path: str) -> bytes:
        self.log.append(("read_file", app_relative_path))
        return b""

    def write_seed_sql(self, db_name: str, statements: list[str]) -> None:
        self.log.append(("write_seed_sql", db_name, len(statements)))

    def settings(self, namespace: str, key: str) -> str:
        self.log.append(("settings", namespace, key))
        return ""


ACTIONS = ("tap", "tap_xy", "long_press", "long_press_xy", "swipe", "swipe_screen", "input_text", "type",
           "key", "back", "home", "enter", "rotate", "open_app", "scroll_to", "wait_idle", "screenshot", "ui",
           "observe")
# keys an agent may press (no power, settings shortcuts or app-switching tricks)
AGENT_KEYS = {"BACK", "HOME", "ENTER", "TAB", "DEL", "FORWARD_DEL", "DPAD_UP", "DPAD_DOWN", "DPAD_LEFT",
              "DPAD_RIGHT", "MOVE_HOME", "MOVE_END", "PAGE_UP", "PAGE_DOWN", "ESCAPE", "APP_SWITCH"}


def _sh(device: Device):
    fn = getattr(device, "sh", None)
    if fn is None:
        raise NotImplementedError("this action needs a real device")
    return fn


def _screen(device: Device) -> tuple[int, int]:
    fn = getattr(device, "_screen_size", None)
    return fn() if fn else (1080, 2400)


def apply_action(device: Device, msg: dict) -> dict:
    """Run one agent 'action' message against a Device. Returns an observation.

    A failed or unknown action never ends the run: the observation carries
    `error` and the current UI, so the agent can recover (as in AndroidWorld).
    """
    import base64
    name = msg.get("name") or msg.get("action") or ""
    args = msg.get("args") or {}
    sel = args.get("selector") or {k: args[k] for k in ("id", "text", "desc") if k in args}
    obs: dict = {"type": "observation"}
    try:
        if name == "tap":
            device.tap(sel)
        elif name == "tap_xy":
            fn = getattr(device, "sh", None)
            if fn is None:
                raise NotImplementedError("tap_xy needs a real device")
            fn(f"input tap {int(args['x'])} {int(args['y'])}")
            getattr(device, "_dirty", lambda: None)()
        elif name == "long_press":
            getattr(device, "long_press")(sel)
        elif name == "long_press_xy":
            x, y = int(args["x"]), int(args["y"])
            _sh(device)(f"input swipe {x} {y} {x} {y} 900")
            getattr(device, "_dirty", lambda: None)()
        elif name == "swipe":
            getattr(device, "swipe")(sel, args.get("direction", "left"))
        elif name == "swipe_screen":
            # direction = where the finger moves; "up" scrolls content down the list
            w, h = _screen(device)
            d = args.get("direction", "up")
            span = float(args.get("distance", 0.5))
            cx, cy = int(args.get("x", w // 2)), int(args.get("y", h // 2))
            dx = {"left": -1, "right": 1}.get(d, 0) * int(w * span / 2)
            dy = {"up": -1, "down": 1}.get(d, 0) * int(h * span / 2)
            if not dx and not dy:
                raise ValueError("direction must be up, down, left or right")
            _sh(device)(f"input swipe {cx - dx} {cy - dy} {cx + dx} {cy + dy} 350")
            getattr(device, "_dirty", lambda: None)()
        elif name == "input_text":
            device.input_text(sel or {"text": args.get("field")}, args.get("text", ""))
        elif name == "type":
            # type into the focused field (tap it first); optional clear and submit
            sh = _sh(device)
            if args.get("clear"):
                sh("input keycombination KEYCODE_CTRL_LEFT KEYCODE_A", check=False)
                sh("input keyevent KEYCODE_DEL", check=False)
            text = str(args.get("text", ""))
            if text:
                import shlex as _shlex
                from aqb.device import input_text_pieces
                for piece in input_text_pieces(text):
                    sh("input text " + _shlex.quote(piece))
            if args.get("submit"):
                sh("input keyevent KEYCODE_ENTER")
            getattr(device, "_dirty", lambda: None)()
        elif name == "key":
            k = str(args.get("key", "")).upper().removeprefix("KEYCODE_")
            if k not in AGENT_KEYS:
                raise ValueError(f"key must be one of {', '.join(sorted(AGENT_KEYS))}")
            _sh(device)(f"input keyevent KEYCODE_{k}")
            getattr(device, "_dirty", lambda: None)()
        elif name == "open_app":
            pkg = getattr(device, "package", None)
            if not pkg:
                raise RuntimeError("no app under test is installed")
            device.launch(pkg)
        elif name == "back":
            device.back()
        elif name == "home":
            device.home()
        elif name == "enter":
            fn = getattr(device, "sh", None)
            if fn is not None:
                fn("input keyevent KEYCODE_ENTER")
                getattr(device, "_dirty", lambda: None)()
        elif name == "rotate":
            device.rotate(bool(args.get("landscape")))
        elif name == "scroll_to":
            obs["found"] = bool(device.scroll_to(sel))
        elif name == "wait_idle":
            device.wait_idle(float(args.get("timeout_s", 5)))
        elif name == "screenshot":
            obs["screenshot_png_b64"] = base64.b64encode(device.screenshot() or b"").decode("ascii")
        elif name not in ("ui", "observe", ""):
            obs["error"] = f"unknown action {name!r}; use one of {', '.join(ACTIONS)}"
        if name not in ("screenshot", "ui", "observe", "wait_idle", "") and "error" not in obs:
            device.wait_idle()
    except Exception as e:  # report to the agent, keep the episode alive
        obs["error"] = f"{name} failed: {type(e).__name__}: {e}"
    obs["ui"] = device.ui()
    remember_seen(device, obs["ui"])
    # never expose the build id to the agent: ids like "<bug>-fixed" give away the answer
    return obs


# ---------------------------------------------------------------------------
# Anchored reports: the harness remembers every text it showed the agent, so a
# report's observed_quote can be checked as really seen (not invented).
# ---------------------------------------------------------------------------

def _norm_text(t: str) -> str:
    import re as _re
    import unicodedata as _ud
    t = _ud.normalize("NFKC", str(t)).replace("\u202f", " ").replace("\u00a0", " ").lower()
    # invisible format characters (bidi isolates U+2066-2069, zero-width marks): apps such as
    # AnkiDroid wrap numbers in them, so an exact quote would never match otherwise
    t = "".join(ch for ch in t if _ud.category(ch) != "Cf")
    # agents often write line breaks inside quotes as the two characters backslash-n
    t = t.replace("\\n", " ").replace("\\t", " ").replace("\\r", " ")
    return _re.sub(r"\s+", " ", t).strip()


def _inside(inner: dict, outer: dict) -> bool:
    a, b = inner.get("bounds") or (0, 0, 0, 0), outer.get("bounds") or (0, 0, 0, 0)
    return inner is not outer and b[0] <= a[0] and b[1] <= a[1] and a[2] <= b[2] and a[3] <= b[3] and list(a) != list(b)


def row_texts(ui: list[dict]) -> list[list[str]]:
    """The texts the MCP observation shows as one row: an unlabelled clickable container is
    rendered `contains "A" | "B"` with the labelled, non-clickable nodes inside it (first 4),
    the same rule as aqb.mcp_device.Server._merge."""
    labelled = [n for n in ui or [] if n.get("text") or n.get("desc")]
    rows = []
    for n in ui or []:
        if n.get("clickable") and not (n.get("text") or n.get("desc")):
            kids = [k.get("text") or k.get("desc") for k in labelled if not k.get("clickable") and _inside(k, n)]
            if len(kids) > 1:
                rows.append(kids[:4])
    return rows


def remember_seen(device, ui: list[dict]) -> None:
    seen = getattr(device, "_aqb_seen", None)
    if seen is None:
        return
    for n in ui or []:
        for k in ("text", "desc"):
            v = n.get(k)
            if v:
                seen.add(_norm_text(v))
    # a row shown as `contains "A" | "B"` was on screen as one line: accept a quote copied
    # from that rendering, joined with " | " (as displayed) or with a space (as read)
    for kids in row_texts(ui):
        parts = [_norm_text(k) for k in kids]
        seen.add(" | ".join(parts))
        seen.add(" ".join(parts))


def start_seen(device) -> None:
    try:
        device._aqb_seen = set()
    except Exception:
        pass


def quote_seen(quote: str | None, device) -> bool:
    """True when the quote (>= 2 chars) is part of some text shown to the agent this session."""
    seen = getattr(device, "_aqb_seen", None)
    q = _norm_text(quote or "")
    if seen is None or not (len(q) >= 2 or q.isdigit()):
        return False
    if len(q) < 3:
        # a very short quote ("2", "ok") must be a whole token, not a fragment of "12" or "book"
        import re as _re
        pat = _re.compile(r"(?<![a-z0-9])" + _re.escape(q) + r"(?![a-z0-9])")
        return any(pat.search(t) for t in seen)
    # a quote copied from a row rendering keeps its JSON quotes: "A" | "B"
    q2 = _norm_text(q.removeprefix("contains ").replace('"', ""))
    return any(q in t or (q2 and q2 in t) for t in seen)


def quote_usable(quote: str | None) -> bool:
    """A quote too short to check (under 2 characters after normalising, e.g. "- ") counts as
    no quote: the report falls back to the prose matcher instead of being rejected."""
    q = _norm_text(quote or "")
    return len(q) >= 2 or q.isdigit()


def annotate_report(report: dict, device) -> dict:
    """Harness-side fields the matcher uses: _quote_seen (observed_quote really shown).
    Dry runs (FakeDevice shows no screen) skip the check; real devices always apply it."""
    out = dict(report)
    if type(device).__name__ == "FakeDevice":
        return out
    # only a quote that was given and never shown is rejected; a report without a quote
    # falls back to the prose matcher (the full run showed 7 correct finds lost otherwise)
    if report.get("observed_quote") and quote_usable(report.get("observed_quote")):
        out["_quote_seen"] = quote_seen(report.get("observed_quote"), device)
    # values_seen() is recorded for audits but not enforced: testers legitimately write numbers
    # they computed ("0x96 (=150)", "should be 18 d"); the pilot showed the rule rejects real finds.
    out["_values_seen_info"] = values_seen(report.get("observed"), device)
    return out


def values_seen(observed: str | None, device) -> bool:
    """Every number the report claims to have observed was shown on screen this session."""
    import re as _re
    seen = getattr(device, "_aqb_seen", None) or set()
    for n in _re.findall(r"-?\d+(?:[.,]\d+)*", _norm_text(observed or "")):
        flat = n.replace(",", "")
        if not any(n in t or flat in t.replace(",", "") for t in seen):
            return False
    return True


def opaque_id(item_id: str) -> str:
    """Stable id shown to agents. Real ids encode the answer (e.g. '-faulty-')."""
    import hashlib
    return "i-" + hashlib.sha256(("aqb:" + item_id).encode()).hexdigest()[:10]


_SEED_ROOTS: dict[str, list[str]] = {}


def seed_roots(dataset: Path = DATASET) -> list[str]:
    """Shared-storage folders any app's seed writes or deletes (relative to /sdcard)."""
    key = str(dataset)
    if key not in _SEED_ROOTS:
        roots: set[str] = set()
        for f in sorted(Path(dataset, "apps").glob("*/seed/*.json")):
            s = json.loads(f.read_text())
            for rel in s.get("delete_external") or []:
                roots.add(str(Path(rel).parent) if "." in Path(rel).name else rel)
            for it in (s.get("files") or []) + (s.get("fixtures") or []):
                roots.add(str(Path(it["path"]).parent))
        roots.discard(".")
        # keep only top-most folders (a parent wipe covers its children)
        _SEED_ROOTS[key] = sorted(r for r in roots if not any(r != o and r.startswith(o + "/") for o in roots))
    return _SEED_ROOTS[key]


def prepare_app(device: Device, app_id: str, seed_id: str, dry_run: bool, dataset: Path = DATASET) -> None:
    """Clear app data and apply the seed so the brief's preconditions hold.
    Dry runs (FakeDevice) only launch: there is no app data to seed."""
    if dry_run:
        return
    reset = getattr(device, "reset_device_state", None)
    if reset is not None:
        reset()
    # Shared storage outlives `pm clear`: wipe every app's seed folders (and their MediaStore
    # rows) so one app's fixtures never show up in another app's item (e.g. Iris photos in
    # Amaze's Recent files). The app's own seed then writes what its brief promises.
    wipe = getattr(device, "delete_external", None)
    if wipe is not None:
        for rel in seed_roots(dataset):
            wipe(rel)
    from dataset_tools import check_helpers
    check_helpers.fresh(device, app_id, seed_id)


def load_device(spec: str | None, dry_run: bool) -> Device:
    if dry_run or not spec or spec in ("fake", "FakeDevice", "dry-run"):
        return FakeDevice()
    if ":" not in spec:
        raise ValueError(f"device spec must be module:Class, got {spec!r}")
    mod_name, cls_name = spec.split(":", 1)
    import importlib
    mod = importlib.import_module(mod_name)
    return getattr(mod, cls_name)()


# ---------------------------------------------------------------------------
# Agent adapters
# ---------------------------------------------------------------------------

class ScriptedAgent:
    """In-process agent: plays a fixed list of outgoing messages."""

    def __init__(self, responses: list[dict]) -> None:
        self.responses = list(responses)
        self.inbox: list[dict] = []
        self._i = 0

    def send(self, msg: dict) -> None:
        self.inbox.append(msg)

    def recv(self) -> dict | None:
        if self._i >= len(self.responses):
            return None
        m = self.responses[self._i]
        self._i += 1
        return m

    def close(self) -> None:
        return None


class OracleAgent:
    """Test/dry-run agent that files each episode bug's reference report, then signs off.

    It cheats by reading the dataset; it is not a model under test.
    """

    def __init__(self, dataset: Path = DATASET) -> None:
        self.dataset = Path(dataset)
        self.inbox: list[dict] = []
        self.queue: list[dict] = []

    def send(self, msg: dict) -> None:
        self.inbox.append(msg)
        if msg.get("type") == "start":
            if msg.get("kind") == "episode":
                ep = load_episode(msg.get("_oracle_item_id") or msg["item_id"], self.dataset)
                for bug_id in ep["bugs"]:
                    self.queue.append(load_reference_report(bug_id, "correct", self.dataset))
                self.queue.append({"type": "sign_off", "verdict": "PASS", "confidence": 1.0,
                                   "notes": "oracle sign-off"})
            elif msg.get("kind") == "case":
                case = load_case(msg.get("_oracle_item_id") or msg["item_id"], self.dataset)
                verdict = case.get("_true_verdict", "PASS")
                out: dict[str, Any] = {"verdict": verdict, "confidence": 1.0,
                                       "evidence": [{"screen": "oracle", "element": "",
                                                     "observed": "oracle"}]}
                if verdict == "FAIL":
                    # the oracle reads the answer: the bug's correct reference report
                    out["failure"] = load_reference_report(case["bug_id"], "correct", self.dataset)
                self.queue.append(out)

    def recv(self) -> dict | None:
        if not self.queue:
            return None
        return self.queue.pop(0)

    def close(self) -> None:
        return None




# --- isolation, usage, secret-path guards (v2) ---

_SECRET_MARKERS = (  # the answer directories under private/ (a bare "private/" would flag app paths)
    'private/diffs', 'private/build', 'private/bugs', 'private/dropped', 'private/mining',
    'private/release_notes', 'private/review', 'private/forwardport', 'private/apps',
    'private/matcher_v2', 'private/licences',
    'build_plan.json',
)

def _token_seps():
    return set(" \t\n\r,();") | {chr(34), chr(39), chr(96)}

def _secret_hits(blob: str) -> list[str]:
    low = blob.lower()
    hits = [m for m in _SECRET_MARKERS if m in low]
    key = "dataset/bugs/"
    i = 0
    seps = _token_seps()
    while True:
        j = low.find(key, i)
        if j < 0:
            break
        k = j
        while k < len(low) and low[k] not in seps:
            k += 1
        token = low[j:k]
        if token.endswith("/checks.py") or token.endswith("/match.json") or "/private" in token:
            hits.append(token)
        i = j + len(key)
    return hits

def isolated_agent_cwd() -> Path:
    """Empty working directory that does not contain private/ or dataset/."""
    return Path(tempfile.mkdtemp(prefix="qa-agent-cwd-"))

def isolated_agent_env() -> dict[str, str]:
    env = os.environ.copy()
    env["ANDROID_QA_ISOLATED"] = "1"
    env.pop("ANDROID_QA_PRIVATE", None)
    return env

def resolve_agent_cmd(cmd: list[str], root: Path = ROOT) -> list[str]:
    """Make in-repo relative paths absolute so the agent can start from an isolated cwd."""
    out = []
    for part in cmd:
        cand = root / part
        if part and not part.startswith("/") and cand.exists():
            out.append(str(cand))
        else:
            out.append(part)
    return out

def secret_access(obj: Any) -> list[str]:
    """Return secret-path mentions in an agent message (reward-hack channel)."""
    try:
        blob = obj if isinstance(obj, str) else json.dumps(obj, ensure_ascii=False)
    except TypeError:
        blob = str(obj)
    return _secret_hits(blob)


def merge_usage(acc: dict, msg: dict, *, price_in: float = 0.0, price_out: float = 0.0) -> dict:
    """Accumulate a {type: usage, ...} agent message into acc. Prices are USD / million tokens."""
    out = dict(acc or {})
    for k in ("input_tokens", "output_tokens", "total_tokens"):
        if msg.get(k) is not None:
            out[k] = int(out.get(k) or 0) + int(msg.get(k) or 0)
    if msg.get("cost_usd") is not None:
        out["cost_usd"] = float(out.get("cost_usd") or 0.0) + float(msg["cost_usd"])
    elif price_in or price_out:
        add = (int(msg.get("input_tokens") or 0) / 1e6) * price_in
        add += (int(msg.get("output_tokens") or 0) / 1e6) * price_out
        if add:
            out["cost_usd"] = float(out.get("cost_usd") or 0.0) + add
    for k in ("input_tokens", "output_tokens", "total_tokens"):
        out.setdefault(k, 0)
    out.setdefault("cost_usd", 0.0)
    return out


def usage_from_prices(usage: dict, *, price_in: float = 0.0, price_out: float = 0.0) -> dict:
    out = dict(usage or {})
    out.setdefault("input_tokens", 0)
    out.setdefault("output_tokens", 0)
    out.setdefault("total_tokens", int(out["input_tokens"]) + int(out["output_tokens"]))
    if not out.get("cost_usd") and (price_in or price_out):
        out["cost_usd"] = (int(out["input_tokens"]) / 1e6) * price_in + (int(out["output_tokens"]) / 1e6) * price_out
    out.setdefault("cost_usd", 0.0)
    return out

class StdioAgent:
    """Subprocess agent speaking the JSONL protocol on stdin/stdout.

    cwd defaults to an empty temp dir so relative paths cannot see private/.
    Pass cwd explicitly only for the in-tree oracle dummy.
    """

    def __init__(self, cmd: list[str], cwd: Path | None = None, env: dict | None = None) -> None:
        import subprocess
        self.cwd = Path(cwd) if cwd is not None else isolated_agent_cwd()
        self.proc = subprocess.Popen(
            cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, cwd=str(self.cwd), env=env if env is not None else isolated_agent_env(),
            bufsize=1,
        )

    def send(self, msg: dict) -> None:
        assert self.proc.stdin is not None
        self.proc.stdin.write(json.dumps(msg, ensure_ascii=False) + "\n")
        self.proc.stdin.flush()

    def recv(self) -> dict | None:
        assert self.proc.stdout is not None
        line = self.proc.stdout.readline()
        if not line:
            return None
        line = line.strip()
        if not line:
            return self.recv()
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            return {"type": "_unparseable", "raw": line}

    def close(self) -> None:
        try:
            if self.proc.stdin:
                self.proc.stdin.close()
        except Exception:
            pass
        try:
            self.proc.terminate()
            self.proc.wait(timeout=2)
        except Exception:
            try:
                self.proc.kill()
                self.proc.wait(timeout=1)
            except Exception:
                pass
        for stream in (self.proc.stdout, self.proc.stderr):
            try:
                if stream:
                    stream.close()
            except Exception:
                pass


def new_run_id() -> str:
    return uuid.uuid4().hex[:12]


def dump_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# MCP bridge: any MCP-capable agent (Claude Code, a reference loop, Harbor)
# ---------------------------------------------------------------------------

AGENT_PROMPT = """You are a QA tester for an Android app. You operate a real Android device only
through the `device` tools (observe, screenshot, tap, type_text, swipe, press_key, rotate,
open_app, wait). You cannot read the app's code, files or database.

Your task:

{brief}
{guidance}
How to finish:
{finish}
"""

FINISH_CASE = """- When you have decided, call `submit_verdict` once with PASS (the app behaves as the case
  expects), FAIL (it does not) or INCONCLUSIVE, your confidence, the evidence you saw, and for FAIL
  the failure details (screen, element, field, symptom_type, expected, observed; where you can,
  also element_ref and observed_quote: the element's number from observe and the exact on-screen
  text; a quote that was never on screen gets the failure rejected).
- After submit_verdict the session ends."""

FINISH_EPISODE = """- For each bug you find, call `file_report` (screen, element, field, symptom_type, expected,
  observed, steps). Where you can, point at the element that shows it (`element_ref`, its number
  in your latest observe) and quote the exact on-screen text that shows it (`observed_quote`);
  a report about something missing may leave the quote out, but a quote that was never on screen
  gets the report rejected. The developer's reply comes back as the result.
- {build_line}
- When you have tested the areas and filed a report for every bug you found, call `sign_off`.
  Bugs you have already reported do not stop you from signing off. The session then ends."""

# Episode prompt v2 (2026-11-14): generic testing method for open sweeps. Ordinary mobile-QA
# heuristics that apply to any app; nothing here names an app, a screen or a planted bug.
# v1 (no method section) produced near-universal premature sign-offs.
EPISODE_PROMPT_VERSION = "v4.1"  # v4.1: sign-off means "tested the areas and reported every bug found" (v4 said "no remaining bugs", which the fast protocol, where reported bugs stay in the build, made impossible to state truthfully); v4: release notes say what changed in each feature (mechanism level, no symptom or trigger); v3: feature-level notes; v2.1: QA method
QA_METHOD = """
How to test well (general QA practice):
- Make a plan from the areas above and exercise every one of them before you sign off. Signing off
  while bugs remain unreported is the worst outcome, worse than spending more steps.
- Go past the happy path. For each feature, also check:
  - State: after a change, leave and come back, and check that it was kept.
  - Reversal: undo, cancel or reverse a change, and check the app returns to the right state.
  - Repetition: repeat an action, and check the result is still right.
  - Input: try empty, boundary and unusual values.
  - Consistency: check that what each screen shows agrees with the data, and with other screens.
  - Device: rotate the screen, and check that nothing is lost.
  - Navigation: reach screens by more than one route.
- Use the starting data described in the preconditions in your tests.
- Reproduce a problem once before you report it.
"""

BUILD_LINE = {
    "fast": "A confirmed report is logged; no new build is installed. Keep testing the same build.",
    "full": "When the developer confirms a report, a fixed build is installed and you are told; re-test as you see fit.",
}


def brief_for_tools(brief: str) -> str:
    """Episode briefs describe the text protocol (JSON report and sign-off blocks, a new build per
    accepted report). Agents on the MCP tools get the brief without those sections: the tools and the
    finishing instructions replace them."""
    import re as _re
    out = _re.sub(r"\n## (Report format|Sign-off format)[^\n]*\n.*?(?=\n## |\Z)", "\n", brief, flags=_re.S)
    out = out.replace("- When you find a bug, file a report (format below). A developer will reply.\n",
                      "- When you find a bug, file a report. A developer will reply.\n")
    out = _re.sub(r"- If the developer accepts the report, they ship a new build and tell you\. Re-test as you see fit\.\n", "", out)
    # v4.1: the briefs' old sign-off rule ("no remaining bugs") contradicts the fast protocol, where
    # reported bugs stay in the build; use the same rule as the finishing instructions.
    out = out.replace("- When you believe the areas above have no remaining bugs, sign off.\n",
                      "- When you have tested the areas above and reported every bug you found, sign off.\n")
    return out.rstrip() + "\n"


class McpBridgeAgent:
    """Harness-side agent that serves an MCP device server over a local socket.

    The harness calls send()/recv() exactly as with StdioAgent. On the 'start' message the
    bridge writes the prompt and an MCP config into an isolated working dir and launches the
    agent command; the agent's MCP client spawns `python -m aqb.mcp_device`, which connects
    back here. Each MCP tool call becomes one agent message; the harness's answer becomes
    the tool result. The agent never gets adb, the APK, the dataset or app data.

    cmd_template placeholders: {prompt} (prompt text, shell-quoted), {prompt_file},
    {mcp_config} (path to an mcpServers JSON file), {cwd}.
    """

    def __init__(self, cmd_template: str, cwd: Path | None = None, env: dict | None = None,
                 log_path: Path | None = None, idle_timeout_s: float = 900.0) -> None:
        import socket
        self.cmd_template = cmd_template
        self.cwd = Path(cwd) if cwd is not None else isolated_agent_cwd()
        self.env = dict(env if env is not None else isolated_agent_env())
        self.log_path = log_path
        self.idle_timeout_s = idle_timeout_s
        self.sock_path = str(Path(tempfile.mkdtemp(prefix="aqb-bridge-")) / "bridge.sock")
        self.srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.srv.bind(self.sock_path)
        self.srv.listen(4)
        self.conn = None
        self.rfile = None
        self.proc = None
        self.start_msg: dict | None = None
        self.pending: list[dict] = []

    # -- launch -------------------------------------------------------------
    def _launch(self, start: dict) -> None:
        import shlex
        import subprocess
        finish = FINISH_CASE if start.get("kind") == "case" else FINISH_EPISODE
        brief = start.get("brief", "")
        if start.get("kind") != "case":
            brief = brief_for_tools(brief)
            finish = finish.replace("{build_line}", BUILD_LINE.get(start.get("protocol") or "full", BUILD_LINE["full"]))
        # QA guidance is for episodes (open sweeps); a case is one described check.
        guidance = "" if start.get("kind") == "case" else QA_METHOD
        prompt = AGENT_PROMPT.format(brief=brief, finish=finish, guidance=guidance)
        pf = self.cwd / "PROMPT.md"
        pf.write_text(prompt)
        cfg = {"mcpServers": {"device": {
            "command": sys.executable, "args": ["-m", "aqb.mcp_device"],
            "env": {"AQB_BRIDGE": self.sock_path, "PYTHONPATH": str(ROOT)},
        }}}
        cf = self.cwd / "mcp.json"
        cf.write_text(json.dumps(cfg, indent=2))
        cmd = self.cmd_template
        for k, v in (("{prompt_file}", str(pf)), ("{mcp_config}", str(cf)), ("{cwd}", str(self.cwd)),
                     ("{prompt}", prompt)):
            cmd = cmd.replace(k, shlex.quote(v))
        out = open(self.log_path, "a") if self.log_path else subprocess.DEVNULL
        self.proc = subprocess.Popen(cmd, shell=True, cwd=str(self.cwd), env=self.env,
                                     stdin=subprocess.DEVNULL, stdout=out, stderr=subprocess.STDOUT,
                                     start_new_session=True)

    def _accept(self, deadline: float) -> bool:
        import select
        while self.conn is None:
            if self.proc is not None and self.proc.poll() is not None:
                return False
            r, _, _ = select.select([self.srv], [], [], 1.0)
            if r:
                self.conn, _ = self.srv.accept()
                self.rfile = self.conn.makefile("r", encoding="utf-8")
                self._write(self.start_msg or {})
                for m in self.pending:
                    self._write(m)
                self.pending.clear()
            elif time.monotonic() > deadline:
                return False
        return True

    def _write(self, msg: dict) -> None:
        self.conn.sendall((json.dumps(msg, ensure_ascii=False) + "\n").encode("utf-8"))

    # -- harness API ----------------------------------------------------------
    def send(self, msg: dict) -> None:
        if msg.get("type") == "start":
            self.start_msg = msg
            self._launch(msg)
            return
        if self.conn is None:
            self.pending.append(msg)
            return
        try:
            self._write(msg)
        except OSError:
            pass

    def recv(self) -> dict | None:
        import select
        deadline = time.monotonic() + self.idle_timeout_s
        if not self._accept(deadline):
            return None
        while True:
            r, _, _ = select.select([self.conn], [], [], 1.0)
            if r:
                line = self.rfile.readline()
                if not line:
                    return None
                line = line.strip()
                if not line:
                    continue
                try:
                    return json.loads(line)
                except json.JSONDecodeError:
                    return {"type": "_unparseable", "raw": line}
            if self.proc is not None and self.proc.poll() is not None:
                return None
            if time.monotonic() > deadline:
                return None

    def exit_code(self) -> int | None:
        """The agent process's exit code once it has ended (waits briefly), else None."""
        if self.proc is None:
            return None
        try:
            self.proc.wait(timeout=15)
        except Exception:
            return None
        return self.proc.returncode

    def quit_cleanly(self) -> bool:
        """The agent process ended by itself with exit code 0 (it chose to stop)."""
        if self.proc is None:
            return False
        try:
            self.proc.wait(timeout=15)  # the MCP server closes the socket just before the agent exits
        except Exception:
            return False
        return self.proc.returncode == 0

    def close(self) -> None:
        import os as _os
        import signal
        for f in (self.rfile, self.conn, self.srv):
            try:
                f and f.close()
            except Exception:
                pass
        if self.proc is not None and self.proc.poll() is None:
            try:
                self.proc.wait(timeout=60)  # let the agent finish its turn (and print its usage) after the session ends
            except Exception:
                pass
        if self.proc is not None and self.proc.poll() is None:
            try:
                _os.killpg(self.proc.pid, signal.SIGTERM)
                self.proc.wait(timeout=5)
            except Exception:
                try:
                    _os.killpg(self.proc.pid, signal.SIGKILL)
                except Exception:
                    pass
        try:
            Path(self.sock_path).unlink(missing_ok=True)
            Path(self.sock_path).parent.rmdir()
        except Exception:
            pass
