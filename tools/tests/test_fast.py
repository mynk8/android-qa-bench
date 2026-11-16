"""Tests for the fast episode protocol and the core/full build tiers."""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.eval_lib import DATASET, FakeDevice, OracleAgent, ScriptedAgent, load_reference_report
from tools.run_eval import run_episode

SIGN_OFF = {"type": "sign_off", "verdict": "PASS", "confidence": 1.0, "notes": "ok"}


class FastProtocol(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _run(self, episode_id, responses):
        rec = run_episode(episode_id, ScriptedAgent(responses), FakeDevice(), dataset=DATASET,
                          dry_run=True, out_dir=self.tmp, protocol="fast")
        return rec

    def test_oracle_succeeds_with_one_install(self):
        rec = run_episode("tasks-E01", OracleAgent(DATASET), FakeDevice(), dataset=DATASET,
                          dry_run=True, out_dir=self.tmp, protocol="fast")
        self.assertEqual(rec["outcome"], "success")
        self.assertEqual(rec["recall"], 1.0)
        self.assertEqual(len(rec["builds_installed"]), 1)
        self.assertEqual(rec["builds_installed"][0]["mask"], "111")
        self.assertEqual(rec["settings"]["protocol"], "fast")

    def test_signoff_with_unreported_bug_is_wrong_pass(self):
        rec = self._run("tasks-E01", [load_reference_report("tasks-0005"), SIGN_OFF])
        self.assertEqual(rec["outcome"], "wrong_pass")
        self.assertAlmostEqual(rec["recall"], 1 / 3)

    def test_duplicate_report_is_neither_hit_nor_false_positive(self):
        r = load_reference_report("tasks-0005")
        rec = self._run("tasks-E01", [r, r, SIGN_OFF])
        self.assertEqual(rec["true_positives"], 1)
        self.assertEqual(rec["false_positives"], 0)
        self.assertEqual(rec["already_fixed_reports"], 1)

    def test_masked_bug_not_required(self):
        # amaze-0004 masks amaze-0005 on the start build, so only 0004 is required
        rec = self._run("amaze-E01", [load_reference_report("amaze-0004"), SIGN_OFF])
        self.assertEqual(rec["outcome"], "success")
        self.assertEqual(rec["required"], ["amaze-0004"])
        self.assertEqual(rec["recall"], 1.0)


class BuildTiers(unittest.TestCase):
    def test_every_build_has_a_tier_and_core_is_minimal(self):
        man = json.loads((DATASET / "manifest.json").read_text())
        core = set()
        for app in man["apps"]:
            idx = json.loads((DATASET / "apps" / app / "builds" / "index.json").read_text())
            for bid, meta in idx.items():
                self.assertIn(meta.get("tier"), ("core", "full"), bid)
                if meta["tier"] == "core":
                    core.add(bid)
        want = set()
        for b in man["bugs"]:
            want |= set(json.loads((DATASET / "bugs" / b / "bug.json").read_text())["builds"].values())
        for e in man["episodes"]:
            ep = json.loads((DATASET / "episodes" / e / "episode.json").read_text())
            want.add(ep["builds"]["1" * len(ep["bugs"])])
        self.assertEqual(core, want)


if __name__ == "__main__":
    unittest.main()


class AgentActions(unittest.TestCase):
    def test_screenshot_is_returned_to_agent(self):
        from tools.eval_lib import apply_action
        obs = apply_action(FakeDevice(), {"type": "action", "name": "screenshot"})
        self.assertIn("screenshot_png_b64", obs)

    def test_failed_action_is_an_error_observation_not_a_crash(self):
        from tools.eval_lib import apply_action

        class Boom(FakeDevice):
            def tap(self, selector):
                raise LookupError("no node")
        obs = apply_action(Boom(), {"type": "action", "name": "tap", "args": {"selector": {"text": "Nope"}}})
        self.assertEqual(obs["type"], "observation")
        self.assertIn("no node", obs["error"])

    def test_unknown_action_reports_error(self):
        from tools.eval_lib import apply_action
        obs = apply_action(FakeDevice(), {"type": "action", "name": "teleport"})
        self.assertIn("unknown action", obs["error"])

    def test_gestures_reach_device(self):
        from tools.eval_lib import apply_action
        calls = []

        class Rec(FakeDevice):
            def long_press(self, selector):
                calls.append(("long_press", selector))

            def swipe(self, selector, direction="left"):
                calls.append(("swipe", selector, direction))
        d = Rec()
        apply_action(d, {"type": "action", "name": "long_press", "args": {"selector": {"text": "A"}}})
        apply_action(d, {"type": "action", "name": "swipe", "args": {"selector": {"text": "A"}, "direction": "right"}})
        self.assertEqual(calls, [("long_press", {"text": "A"}), ("swipe", {"text": "A"}, "right")])


class NoAnswerLeak(unittest.TestCase):
    def test_case_agent_never_sees_verdict_words(self):
        from tools.case_eval import run_case
        tmp = Path(tempfile.mkdtemp())
        try:
            for cid in ("tasks-0002-faulty-spec", "tasks-0002-clean-spec"):
                agent = ScriptedAgent([{"type": "action", "name": "ui"},
                                       {"verdict": "PASS", "confidence": 0.5, "evidence": []}])
                run_case(cid, agent, FakeDevice(), dataset=DATASET, dry_run=True, out_dir=tmp)
                seen = json.dumps(agent.inbox).lower()
                for word in ("faulty", "clean", "fixed", "buggy", "tasks-0002"):
                    self.assertNotIn(word, seen, f"{cid}: agent saw {word!r}")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
