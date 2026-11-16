"""MCP device bridge: a scripted MCP client drives a case and an episode on FakeDevice."""
import json
import shlex
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.eval_lib import DATASET, FakeDevice, McpBridgeAgent, load_manifest  # noqa: E402
from tools.case_eval import run_case  # noqa: E402
from tools.run_eval import run_episode  # noqa: E402

STUB = ROOT / "tools" / "tests" / "mcp_client_stub.py"


def bridge(script, cwd):
    cmd = f"{shlex.quote(sys.executable)} {shlex.quote(str(STUB))} {{mcp_config}} {shlex.quote(json.dumps(script))}"
    return McpBridgeAgent(cmd, cwd=cwd, idle_timeout_s=60)


class McpBridgeTest(unittest.TestCase):
    def test_case_verdict_via_mcp(self):
        case = sorted(p.name for p in (DATASET / "cases").iterdir() if p.name.endswith("faulty-spec"))[0]
        bug = case.rsplit("-faulty", 1)[0]
        ref = json.loads((DATASET / "bugs" / bug / "reference_reports.json").read_text())
        with tempfile.TemporaryDirectory() as d:
            script = [["observe", {}], ["press_key", {"key": "POWER"}],
                      ["submit_verdict", {"verdict": "FAIL", "confidence": 0.8, "failure": ref["correct"]}]]
            res = run_case(case, bridge(script, d), FakeDevice(), dataset=DATASET, dry_run=True,
                           out_dir=Path(d) / "out")
            t = json.loads((Path(d) / "transcript.json").read_text())
        with tempfile.TemporaryDirectory() as d:  # a FAIL that names the wrong defect is not a find
            script = [["submit_verdict", {"verdict": "FAIL", "confidence": 0.8, "failure": ref["wrong_bug"]}]]
            wrong = run_case(case, bridge(script, d), FakeDevice(), dataset=DATASET, dry_run=True,
                             out_dir=Path(d) / "out")
        self.assertFalse(wrong["success"])
        self.assertTrue(wrong["verdict_correct"])
        self.assertIn("submit_verdict", t["tools"])
        self.assertNotIn("file_report", t["tools"])
        self.assertIn("Elements", t["calls"][0]["result"]["content"][0]["text"])
        self.assertIn("ERROR", t["calls"][1]["result"]["content"][0]["text"])  # POWER is not allowed
        self.assertEqual(res["predicted_verdict"], "FAIL")
        self.assertTrue(res["success"])

    def test_episode_report_and_sign_off_via_mcp(self):
        ep = load_manifest()["episodes"][0]
        with tempfile.TemporaryDirectory() as d:
            script = [["file_report", {"screen": "x", "element": "y", "symptom_type": "wrong_value",
                                       "expected": "a", "observed": "b", "steps": ["s"]}],
                      ["sign_off", {"confidence": 0.5}]]
            res = run_episode(ep, bridge(script, d), FakeDevice(), dataset=DATASET, dry_run=True,
                              out_dir=Path(d) / "out")
            t = json.loads((Path(d) / "transcript.json").read_text())
        self.assertIn("sign_off", t["tools"])
        self.assertIn("Developer", t["calls"][0]["result"]["content"][0]["text"])
        self.assertEqual(res["reports"], 1)



class ObservationFormatTest(unittest.TestCase):
    def test_rows_labelled_and_status_bar_hidden(self):
        from aqb.mcp_device import Server

        class B:
            start = {"kind": "case"}
        s = Server(B())
        node = lambda b, **k: {"bounds": b, "visible": True, "package": k.pop("pkg", "app"), **k}
        ui = [node([0, 0, 100, 50], text="2:03", pkg="com.android.systemui"),
              node([0, 300, 720, 400], clickable=True, **{"class": "android.view.View"}),
              node([20, 310, 300, 350], text="Expenses"),
              node([20, 360, 600, 390], text="MODIFIED: JAN 10"),
              node([640, 320, 700, 380], clickable=True, desc="More options")]
        text = s._format({"type": "observation", "ui": ui})[0]["text"]
        self.assertNotIn("2:03", text)
        self.assertIn('[0] View contains "Expenses" | "MODIFIED: JAN 10" [clickable]', text)
        self.assertEqual(text.count("Expenses"), 1)
        self.assertIn('desc="More options"', text)
        self.assertEqual(len(s.elements), 2)



class AnchoredReportTest(unittest.TestCase):
    def test_quote_must_have_been_shown(self):
        from tools.eval_lib import annotate_report, apply_action, start_seen

        class Dev(FakeDevice):  # a device that shows text (FakeDevice itself skips the check)
            def ui(self):
                return [{"text": "15 dec in hex", "visible": True, "bounds": [0, 0, 10, 10]},
                        {"text": "0x96", "visible": True, "bounds": [0, 20, 10, 30]}]
        d = Dev()
        start_seen(d)
        apply_action(d, {"type": "action", "name": "observe"})
        from tools.eval_lib import remember_seen
        self.assertTrue(annotate_report({"observed_quote": "0X96"}, d)["_quote_seen"])
        self.assertFalse(annotate_report({"observed_quote": "0xF"}, d)["_quote_seen"])
        self.assertNotIn("_quote_seen", annotate_report({}, d))  # no quote: prose path decides
        remember_seen(d, [{"text": "queue top: \u20681\u2069\nqueue top: \u20687\u2069"}])
        self.assertTrue(annotate_report({"observed_quote": "Queue top: 7"}, d)["_quote_seen"])
        from tools.eval_lib import remember_seen
        remember_seen(d, [{"text": "- item\n  - - child\n"}])
        self.assertTrue(annotate_report({"observed_quote": "- item\\n  - - child\\n"}, d)["_quote_seen"])
        self.assertTrue(annotate_report({"observed": "15 in hex shows 0x96"}, d)["_values_seen_info"])
        self.assertFalse(annotate_report({"observed": "shows 270.00"}, d)["_values_seen_info"])

    def test_mcp_attaches_anchor_node(self):
        from aqb.mcp_device import Server

        class B:
            start = {"kind": "episode"}
            sent = []

            def call(self, msg, **k):
                self.sent.append(msg)
                return {"type": "developer_reply", "text": "ok"}
        b = B()
        s = Server(b)
        s.elements = [{"text": "0x96", "id": "app:id/result", "bounds": [0, 0, 1, 1]}]
        s.call_tool("file_report", {"screen": "s", "element": "e", "symptom_type": "wrong_value",
                                    "expected": "a", "observed": "b", "steps": [], "element_ref": 0,
                                    "observed_quote": "0x96"})
        self.assertEqual(b.sent[-1]["anchor_node"]["text"], "0x96")


if __name__ == "__main__":
    unittest.main()
