"""MCP server (stdio) that lets a QA agent operate the benchmark's Android device.

    AQB_BRIDGE=/path/to/bridge.sock python -m aqb.mcp_device

It speaks MCP's stdio transport (newline-delimited JSON-RPC 2.0, no SDK needed) to the agent,
and relays every tool call to the harness over the bridge socket
(tools/eval_lib.py McpBridgeAgent). The harness executes the action on the device, scores
reports, and its answer becomes the tool result. This process has no device access, no
dataset access and no secrets: it only formats observations.

Elements are numbered in each observation; tap/long_press/type_text take `element` (that
number), or `x`/`y` screen coordinates.
"""
from __future__ import annotations

import base64
import json
import os
import socket
import sys

PROTOCOL = "2025-06-18"
MAX_ELEMENTS = 120

SELECT = {"type": "object", "properties": {
    "element": {"type": "integer", "description": "element number from the latest observation"},
    "x": {"type": "integer", "description": "screen x in pixels (instead of element)"},
    "y": {"type": "integer", "description": "screen y in pixels (instead of element)"},
}}

REPORT_FIELDS = {
    "screen": {"type": "string"}, "element": {"type": "string"}, "field": {"type": "string"},
    "symptom_type": {"type": "string", "enum": ["wrong_value", "missing", "not_persisted", "cut_off",
                                                "wrong_navigation", "no_effect", "duplicated", "overlap"]},
    "expected": {"type": "string"}, "observed": {"type": "string"},
    "steps": {"type": "array", "items": {"type": "string"}},
    "element_ref": {"type": "integer", "description": "number of the element showing the defect, from your "
                    "latest observe (the element itself, or the closest one when something is missing)"},
    "observed_quote": {"type": "string", "description": "exact text you saw on screen that shows the defect "
                       "(copy it verbatim from an observation, e.g. the wrong value or the label shown)"},
}


def _tool(name, desc, props=None, required=None):
    schema = {"type": "object", "properties": props or {}}
    if required:
        schema["required"] = required
    return {"name": name, "description": desc, "inputSchema": schema}


DEVICE_TOOLS = [
    _tool("observe", "List the visible UI elements of the current screen (numbered), and the "
          "foreground app. Use the numbers with tap/long_press/type_text.",
          {"screenshot": {"type": "boolean", "description": "also return a screenshot image"}}),
    _tool("screenshot", "Return a screenshot of the current screen as an image."),
    _tool("tap", "Tap an element (by number) or a screen point (x, y).", SELECT["properties"]),
    _tool("long_press", "Long-press an element (by number) or a screen point (x, y).", SELECT["properties"]),
    _tool("type_text", "Type text into a field. Taps the element first when given; otherwise types into "
          "the focused field.", {**SELECT["properties"],
                                 "text": {"type": "string"},
                                 "clear": {"type": "boolean", "description": "clear the field first (default true)"},
                                 "submit": {"type": "boolean", "description": "press Enter afterwards"}},
          ["text"]),
    _tool("swipe", "Swipe the screen. direction is where the finger moves: 'up' scrolls a list down.",
          {"direction": {"type": "string", "enum": ["up", "down", "left", "right"]},
           "distance": {"type": "number", "description": "fraction of the screen, 0.1-0.9 (default 0.5)"},
           **SELECT["properties"]}, ["direction"]),
    _tool("press_key", "Press a key: BACK, HOME, ENTER, TAB, DEL, ESCAPE, APP_SWITCH, DPAD_* ...",
          {"key": {"type": "string"}}, ["key"]),
    _tool("rotate", "Rotate the device.", {"orientation": {"type": "string", "enum": ["portrait", "landscape"]}},
          ["orientation"]),
    _tool("open_app", "Bring the app under test to the foreground (does not reset its data)."),
    _tool("wait", "Wait for the screen to settle (up to 5 s).", {"seconds": {"type": "number"}}),
]
CASE_TOOLS = [
    _tool("submit_verdict", "Finish the test case with your verdict. Ends the session.", {
        "verdict": {"type": "string", "enum": ["PASS", "FAIL", "INCONCLUSIVE"]},
        "confidence": {"type": "number"},
        "evidence": {"type": "array", "items": {"type": "object", "properties": {
            "screen": {"type": "string"}, "element": {"type": "string"}, "observed": {"type": "string"}}}},
        "failure": {"type": "object", "properties": REPORT_FIELDS, "description": "required when FAIL"},
    }, ["verdict", "confidence"]),
]
EPISODE_TOOLS = [
    _tool("file_report", "File one bug report. The developer's reply is returned. Where you can, point at "
          "the element (element_ref) and quote what the screen shows (observed_quote); a report about something "
          "missing may leave the quote out, but a quote that was never on screen gets the report rejected.",
          REPORT_FIELDS, ["screen", "element", "symptom_type", "expected", "observed", "steps"]),
    _tool("sign_off", "Sign off: you have tested the listed areas and filed a report for every bug you "
          "found. Ends the session.",
          {"confidence": {"type": "number"}, "notes": {"type": "string"}}, ["confidence"]),
]


class Bridge:
    def __init__(self, path: str):
        self.s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.s.connect(path)
        self.r = self.s.makefile("r", encoding="utf-8")
        self.start = self._read() or {}
        self.ended = False

    def _read(self):
        line = self.r.readline()
        return json.loads(line) if line.strip() else None

    def call(self, msg: dict, expect_reply: bool = True, timeout: float | None = None):
        if self.ended:
            return {"type": "end", "reason": "session already ended"}
        self.s.sendall((json.dumps(msg, ensure_ascii=False) + "\n").encode("utf-8"))
        if not expect_reply:
            return None
        self.s.settimeout(timeout)
        try:
            reply = self._read()
        except (socket.timeout, OSError):
            reply = None
        finally:
            self.s.settimeout(None)
        if reply is None or reply.get("type") == "end":
            self.ended = True
        return reply


def _label(n: dict) -> str:
    cls = (n.get("class") or "").rsplit(".", 1)[-1]
    parts = [cls or "View"]
    if n.get("text"):
        parts.append(json.dumps(n["text"], ensure_ascii=False))
    if n.get("desc") and n.get("desc") != n.get("text"):
        parts.append("desc=" + json.dumps(n["desc"], ensure_ascii=False))
    if n.get("contains"):
        parts.append("contains " + " | ".join(json.dumps(t, ensure_ascii=False) for t in n["contains"]))
    rid = (n.get("id") or "").split("/")[-1]
    if rid:
        parts.append("id=" + rid)
    flags = [f for f in ("clickable", "checked", "selected", "focused") if n.get(f)]
    if n.get("enabled") is False:
        flags.append("disabled")
    if flags:
        parts.append("[" + ",".join(flags) + "]")
    x1, y1, x2, y2 = n.get("bounds") or (0, 0, 0, 0)
    parts.append(f"@({(x1 + x2) // 2},{(y1 + y2) // 2})")
    return " ".join(parts)


class Server:
    def __init__(self, bridge: Bridge):
        self.b = bridge
        self.kind = bridge.start.get("kind", "case")
        self.elements: list[dict] = []

    # ------------------------------------------------------------ observations
    def _format(self, obs: dict | None, want_shot: bool = False) -> list[dict]:
        if obs is None or obs.get("type") == "end":
            self.elements = []
            return [{"type": "text", "text": "The session has ended."}]
        out = []
        if obs.get("error"):
            out.append(f"ERROR: {obs['error']}")
        ui = [n for n in (obs.get("ui") or []) if n.get("visible", True)]
        app_nodes = [n for n in ui if n.get("package") and n["package"] != "com.android.systemui"]
        if app_nodes:  # hide the status bar / system UI unless it is all there is (e.g. shade open)
            ui = app_nodes
        pkgs = [n.get("package") for n in ui if n.get("package")]
        keep = self._merge(ui)
        self.elements = keep[:MAX_ELEMENTS]
        if pkgs:
            out.append(f"Foreground: {max(set(pkgs), key=pkgs.count)}")
        out.append(f"Elements ({len(self.elements)}{' of ' + str(len(keep)) if len(keep) > MAX_ELEMENTS else ''}):")
        out += [f"[{i}] {_label(n)}" for i, n in enumerate(self.elements)]
        content = [{"type": "text", "text": "\n".join(out)}]
        if want_shot and obs.get("screenshot_png_b64"):
            content.append({"type": "image", "data": obs["screenshot_png_b64"], "mimeType": "image/png"})
        return content

    @staticmethod
    def _inside(inner, outer) -> bool:
        a, b = inner.get("bounds") or (0, 0, 0, 0), outer.get("bounds") or (0, 0, 0, 0)
        return a is not b and b[0] <= a[0] and b[1] <= a[1] and a[2] <= b[2] and a[3] <= b[3] and a != b

    def _merge(self, ui: list[dict]) -> list[dict]:
        """Label unlabeled clickable containers with the text inside them (Compose rows), and
        drop text nodes already shown that way. Keeps every interactive or labelled node."""
        labelled = [n for n in ui if n.get("text") or n.get("desc")]
        absorbed: set[int] = set()
        out = []
        for n in ui:
            if not (n.get("text") or n.get("desc") or n.get("clickable") or n.get("checked")):
                continue
            if n.get("clickable") and not (n.get("text") or n.get("desc")):
                kids = [k for k in labelled if not k.get("clickable") and self._inside(k, n)]
                if kids:
                    n = dict(n, contains=[k.get("text") or k.get("desc") for k in kids[:4]])
                    absorbed.update(id(k) for k in kids)
            out.append(n)
        return [n for n in out if id(n) not in absorbed or n.get("clickable")]

    def _anchor(self, a: dict) -> dict:
        """Resolve element_ref to the UI node the agent pointed at (harness-trusted fields only)."""
        ref = a.get("element_ref")
        if ref is None:
            return {}
        i = int(ref)
        if not 0 <= i < len(self.elements):
            return {"anchor_error": f"no element {i} in the latest observation"}
        n = self.elements[i]
        return {"anchor_node": {k: n.get(k) for k in ("id", "text", "desc", "class", "contains", "bounds") if n.get(k)}}

    def _point(self, a: dict) -> tuple[int, int]:
        if a.get("element") is not None:
            i = int(a["element"])
            if not 0 <= i < len(self.elements):
                raise ValueError(f"no element {i}; call observe first")
            x1, y1, x2, y2 = self.elements[i]["bounds"]
            return (x1 + x2) // 2, (y1 + y2) // 2
        if a.get("x") is not None and a.get("y") is not None:
            return int(a["x"]), int(a["y"])
        raise ValueError("give element or x and y")

    def _act(self, name: str, args: dict | None = None, shot: bool = False) -> list[dict]:
        obs = self.b.call({"type": "action", "name": name, "args": args or {}})
        if shot and obs and obs.get("type") == "observation":
            s = self.b.call({"type": "action", "name": "screenshot", "args": {}})
            if s and s.get("screenshot_png_b64"):
                obs["screenshot_png_b64"] = s["screenshot_png_b64"]
        return self._format(obs, want_shot=shot)

    # ------------------------------------------------------------ tool calls
    def call_tool(self, name: str, a: dict) -> tuple[list[dict], bool]:
        if name == "observe":
            return self._act("observe", shot=bool(a.get("screenshot"))), False
        if name == "screenshot":
            obs = self.b.call({"type": "action", "name": "screenshot", "args": {}})
            if obs and obs.get("screenshot_png_b64"):
                return [{"type": "image", "data": obs["screenshot_png_b64"], "mimeType": "image/png"}], False
            return self._format(obs), True
        if name == "tap":
            x, y = self._point(a)
            return self._act("tap_xy", {"x": x, "y": y}), False
        if name == "long_press":
            x, y = self._point(a)
            return self._act("long_press_xy", {"x": x, "y": y}), False
        if name == "type_text":
            if a.get("element") is not None or a.get("x") is not None:
                x, y = self._point(a)
                self.b.call({"type": "action", "name": "tap_xy", "args": {"x": x, "y": y}})
            return self._act("type", {"text": a.get("text", ""), "clear": a.get("clear", True),
                                      "submit": bool(a.get("submit"))}), False
        if name == "swipe":
            args = {"direction": a.get("direction"), "distance": max(0.1, min(0.9, float(a.get("distance", 0.5))))}
            if a.get("element") is not None or a.get("x") is not None:
                args["x"], args["y"] = self._point(a)
            return self._act("swipe_screen", args), False
        if name == "press_key":
            return self._act("key", {"key": a.get("key", "")}), False
        if name == "rotate":
            return self._act("rotate", {"landscape": a.get("orientation") == "landscape"}), False
        if name == "open_app":
            return self._act("open_app"), False
        if name == "wait":
            return self._act("wait_idle", {"timeout_s": max(0.5, min(5.0, float(a.get("seconds", 2))))}), False
        if name == "submit_verdict" and self.kind == "case":
            msg = {k: a[k] for k in ("verdict", "confidence", "evidence", "failure") if k in a}
            if isinstance(msg.get("failure"), dict):
                msg["failure"] = {**msg["failure"], **self._anchor(msg["failure"])}
            self.b.call(msg, timeout=30)
            return [{"type": "text", "text": "Verdict submitted. The session has ended."}], False
        if name == "file_report" and self.kind != "case":
            reply = self.b.call({"type": "bug_report", **a, **self._anchor(a)})
            text = (reply or {}).get("text") or (reply or {}).get("kind") or "No reply."
            return [{"type": "text", "text": text}], False
        if name == "sign_off" and self.kind != "case":
            self.b.call({"type": "sign_off", "verdict": "PASS", **{k: a[k] for k in ("confidence", "notes") if k in a}},
                        timeout=30)
            return [{"type": "text", "text": "Signed off. The session has ended."}], False
        return [{"type": "text", "text": f"unknown tool {name}"}], True


def main() -> int:
    path = os.environ.get("AQB_BRIDGE")
    if not path:
        print("AQB_BRIDGE is not set", file=sys.stderr)
        return 2
    # Connect to the harness lazily, on the first real MCP request. Some clients (DeepSeek
    # Harness) first start a short-lived probe instance that only sends server/discover and
    # exits; connecting at startup would let that probe take the episode's start message.
    state: dict = {}

    def server() -> Server:
        if "srv" not in state:
            state["srv"] = Server(Bridge(path))
            state["tools"] = DEVICE_TOOLS + (CASE_TOOLS if state["srv"].kind == "case" else EPISODE_TOOLS)
        return state["srv"]

    def reply(id_, result=None, error=None):
        msg = {"jsonrpc": "2.0", "id": id_}
        msg["error" if error else "result"] = error or result
        sys.stdout.write(json.dumps(msg, ensure_ascii=False) + "\n")
        sys.stdout.flush()

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue
        method, id_ = req.get("method"), req.get("id")
        if id_ is None:
            continue  # notifications (initialized, cancelled)
        if method == "initialize":
            server()
            reply(id_, {"protocolVersion": (req.get("params") or {}).get("protocolVersion", PROTOCOL),
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "aqb-device", "version": "0.1"}})
        elif method == "ping":
            reply(id_, {})
        elif method == "tools/list":
            server()
            reply(id_, {"tools": state["tools"]})
        elif method == "tools/call":
            p = req.get("params") or {}
            try:
                content, is_err = server().call_tool(p.get("name", ""), p.get("arguments") or {})
            except Exception as e:  # bad arguments: tell the agent, keep going
                content, is_err = [{"type": "text", "text": f"ERROR: {type(e).__name__}: {e}"}], True
            reply(id_, {"content": content, "isError": is_err})
        else:
            reply(id_, error={"code": -32601, "message": f"method not found: {method}"})
    return 0


if __name__ == "__main__":
    sys.exit(main())
