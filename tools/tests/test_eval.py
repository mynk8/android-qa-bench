#!/usr/bin/env python3
"""Fast unit tests for eval harness, scorer, briefs and the dummy agent."""
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

from tools.eval_lib import (
    DATASET, FakeDevice, OracleAgent, ScriptedAgent, StdioAgent,
    format_reply, load_episode, load_reference_report, mask_for, present_on,
    secret_access,
)
from tools.run_eval import run_episode
from tools.case_eval import run_case
from tools import score as score_mod


class BriefContractTests(unittest.TestCase):
    def test_all_cases_exist_and_follow_part3(self):
        bugs = json.loads((DATASET / "manifest.json").read_text())["bugs"]
        required = ["# Test case", "App:", "## Context", "## Preconditions",
                    "## Steps", "## Rules", "## Answer format"]
        by = {}
        for d in sorted((DATASET / "cases").iterdir()):
            if not d.is_dir():
                continue
            case = json.loads((d / "case.json").read_text())
            text = (d / "agent_input.md").read_text()
            self.assertTrue(text.startswith("# Test case "))
            self.assertFalse(text.splitlines()[0].endswith("-spec"))
            self.assertFalse(text.splitlines()[0].endswith("-unspec"))
            for s in required:
                self.assertIn(s, text, f"{d.name} missing {s}")
            self.assertIn("\n\n## Rules\n", text)
            inst = case["_conditions"]["instruction"]
            if inst == "specified":
                self.assertIn("## Expected results", text)
            else:
                self.assertNotIn("## Expected results", text)
            # no source leaks
            self.assertNotRegex(text, r"\b[0-9a-f]{40}\b")
            self.assertNotIn("github.com", text.lower())
            self.assertNotRegex(text.lower(), r"\b(amaze|ankidroid|tasks|markor|minus|iris|featherline)-\d{4}\b")
            key = (case["bug_id"], inst)
            by.setdefault(key, []).append(text)
        for (bug, inst), texts in by.items():
            self.assertTrue(len(set(texts)) == 1, f"clean/faulty text differs for {bug} {inst}")
        # every manifest bug has at least a specified pair
        for bug in bugs:
            self.assertTrue((DATASET / "cases" / f"{bug}-faulty-spec").is_dir(), bug)
            self.assertTrue((DATASET / "cases" / f"{bug}-clean-spec").is_dir(), bug)

    def test_all_episode_briefs_follow_part3(self):
        man = json.loads((DATASET / "manifest.json").read_text())
        required = ["## Preconditions", "## How this works", "## Report format", "## Sign-off format"]
        boilerplate = [
            "The app is installed and open. A colleague asked you to sweep these areas before release:",
            "- Test the app through its screen.",
            "- When you find a bug, file a report (format below). A developer will reply.",
            "- If the developer accepts the report, they ship a new build and tell you. Re-test as you see fit.",
            "- When you believe the areas above have no remaining bugs, sign off.",
            "- Do not change data outside what testing requires.",
        ]
        for eid in man["episodes"]:
            d = DATASET / "episodes" / eid
            self.assertTrue((d / "episode.json").is_file())
            text = (d / "brief.md").read_text()
            self.assertTrue(text.startswith("# QA sweep: "))
            for s in required:
                self.assertIn(s, text, f"{eid} missing {s}")
            for b in boilerplate:
                self.assertIn(b, text, f"{eid} missing boilerplate")
            self.assertNotRegex(text, r"\b[0-9a-f]{40}\b")
            self.assertNotRegex(text.lower(), r"\b(amaze|ankidroid|tasks|markor|minus|iris|featherline)-\d{4}\b")
            self.assertNotRegex(text.lower(), r"\b(there are \d+ bugs|known bug)\b")


class FakeDeviceTests(unittest.TestCase):
    def test_records_install_and_launch(self):
        d = FakeDevice()
        d.install("tasks-E01-111")
        d.launch("org.tasks")
        d.tap({"text": "Buy milk"})
        self.assertEqual(d.installed, "tasks-E01-111")
        self.assertEqual(d.ui(), [])
        self.assertEqual(d.log[0], ("install", "tasks-E01-111"))


class EpisodeHarnessTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="evaltest-"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _run(self, episode_id, responses, **kw):
        agent = ScriptedAgent(responses)
        device = FakeDevice()
        rec = run_episode(episode_id, agent, device, dataset=DATASET, dry_run=True,
                          out_dir=self.tmp, **kw)
        return rec, device, agent

    def test_oracle_clears_tasks_e01(self):
        agent = OracleAgent(DATASET)
        device = FakeDevice()
        rec = run_episode("tasks-E01", agent, device, dataset=DATASET, dry_run=True,
                          out_dir=self.tmp)
        self.assertEqual(rec["outcome"], "success")
        self.assertEqual(rec["status"], "ok")
        self.assertEqual(rec["recall"], 1.0)
        self.assertEqual(rec["false_positives"], 0)
        self.assertEqual(device.installed, "tasks-E01-000")
        masks = [b["mask"] for b in rec["builds_installed"]]
        self.assertEqual(masks[0], "111")
        self.assertEqual(masks[-1], "000")
        self.assertEqual(len(rec["builds_installed"]), 4)  # start + 3 hits
        self.assertTrue(rec["harness_replies"][0].endswith("(build 2)"))
        self.assertIn("trace.jsonl", rec["trace"])
        self.assertTrue((self.tmp / "tasks-E01" / rec["run_id"] / "result.json").is_file())

    def test_wrong_pass_if_signoff_while_bugs_remain(self):
        rec, _, _ = self._run("tasks-E01", [
            {"type": "sign_off", "verdict": "PASS", "confidence": 0.5, "notes": "too soon"},
        ])
        self.assertEqual(rec["outcome"], "wrong_pass")
        self.assertEqual(rec["found"], [])
        self.assertEqual(rec["recall"], 0.0)

    def test_no_match_and_already_fixed_and_second_hit(self):
        ep = load_episode("tasks-E01")
        r0 = load_reference_report(ep["bugs"][0])
        rec, device, agent = self._run("tasks-E01", [
            {"type": "bug_report", "screen": "nowhere", "element": "x", "field": "y",
             "symptom_type": "missing", "expected": "a visible title Buy milk",
             "observed": "the title is gone completely", "steps": ["looked"]},
            r0,
            r0,  # already fixed
            load_reference_report(ep["bugs"][1]),
            load_reference_report(ep["bugs"][2]),
            {"type": "sign_off", "verdict": "PASS", "confidence": 1.0, "notes": "ok"},
        ])
        self.assertEqual(rec["outcome"], "success")
        self.assertEqual(rec["false_positives"], 1)
        self.assertEqual(rec["already_fixed_reports"], 1)
        self.assertTrue(any("could not reproduce" in t for t in rec["harness_replies"]))
        self.assertTrue(any("fixed in build" in t for t in rec["harness_replies"]))
        # already_fixed names the build that shipped the first fix (build 2)
        already = [t for t in rec["harness_replies"] if "fixed in build" in t]
        self.assertTrue(any("build 2" in t for t in already))

    def test_leftover_known_issue_does_not_ship_build(self):
        # Head-port builds carry no leftovers, so build a dataset copy that has one:
        # amaze-0007 marked as a known leftover of amaze-E01.
        ds = self.tmp / "ds"
        shutil.copytree(DATASET, ds, ignore=shutil.ignore_patterns("*.apk"))
        ep_path = ds / "episodes" / "amaze-E01" / "episode.json"
        ep = json.loads(ep_path.read_text())
        ep["known_leftover"] = ["amaze-0007"]
        ep_path.write_text(json.dumps(ep))
        leftover = load_reference_report("amaze-0007")
        first = load_reference_report("amaze-0004")
        second = load_reference_report("amaze-0005")
        agent = ScriptedAgent([
            leftover,
            first,
            leftover,  # still leftover after a real hit
            second,
            {"type": "sign_off", "verdict": "PASS", "confidence": 1.0, "notes": "ok"},
        ])
        rec = run_episode("amaze-E01", agent, FakeDevice(), dataset=ds, dry_run=True, out_dir=self.tmp / "out")
        self.assertEqual(rec["outcome"], "success")
        self.assertEqual(rec["leftover_reports"], 2)
        self.assertEqual(rec["false_positives"], 0)
        self.assertEqual(sum(1 for t in rec["harness_replies"] if "known issue" in t), 2)
        # leftover must not add a subset build
        self.assertEqual(len(rec["builds_installed"]), 3)  # 11, 01, 00 (0004 then 0005)
        self.assertEqual(rec["builds_installed"][0]["build_id"], "amaze-E01-11")

    def test_masked_bug_is_not_already_fixed(self):
        # On amaze-E01 start mask 11, amaze-0005 is masked. Reporting it is no_match.
        rec, _, _ = self._run("amaze-E01", [
            load_reference_report("amaze-0005"),
            load_reference_report("amaze-0004"),
            load_reference_report("amaze-0005"),
            {"type": "sign_off", "verdict": "PASS", "confidence": 1.0, "notes": "ok"},
        ])
        self.assertEqual(rec["outcome"], "success")
        self.assertEqual(rec["false_positives"], 1)
        self.assertEqual(rec["already_fixed_reports"], 0)
        self.assertEqual(rec["found"], ["amaze-0004", "amaze-0005"])

    def test_malformed_reply_wording(self):
        rec, _, agent = self._run("amaze-E03", [
            {"type": "not_a_report", "hello": True},
            {"type": "sign_off", "verdict": "PASS", "confidence": 0.1, "notes": "nope"},
        ])
        self.assertEqual(rec["harness_replies"][0], format_reply("malformed"))
        self.assertEqual(rec["outcome"], "wrong_pass")
        self.assertEqual(agent.inbox[0]["type"], "start")
        self.assertIn("brief", agent.inbox[0])
        self.assertTrue(agent.inbox[0]["brief"].startswith("# QA sweep:"))

    def test_timeout_on_max_reports(self):
        rec, _, _ = self._run("amaze-E03", [
            {"type": "bug_report", "screen": "nowhere", "element": "x", "field": "y",
             "symptom_type": "missing", "expected": "a visible title notes.txt",
             "observed": "the title is gone completely", "steps": ["looked"]},
            {"type": "sign_off", "verdict": "PASS", "confidence": 1.0, "notes": "late"},
        ], max_reports=0)
        self.assertEqual(rec["status"], "timeout")
        # the report limit has its own outcome (audit 2026-11): it is not the 300-action cap
        self.assertEqual(rec["outcome"], "report_cap")

    def test_mask_and_present_helpers(self):
        ep = load_episode("amaze-E01")
        unfixed = set(ep["bugs"])
        self.assertEqual(mask_for(ep["bugs"], unfixed), "11")
        self.assertEqual(present_on(ep, unfixed), {"amaze-0004"})
        self.assertEqual(present_on(ep, {"amaze-0005"}), {"amaze-0005"})


class CaseHarnessTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="caseeval-"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_oracle_matches_truth_on_clean_and_faulty(self):
        for cid, truth in (("tasks-0002-clean-spec", "PASS"), ("tasks-0002-faulty-spec", "FAIL")):
            rec = run_case(cid, OracleAgent(DATASET), FakeDevice(), dataset=DATASET,
                           dry_run=True, out_dir=self.tmp)
            self.assertEqual(rec["true_verdict"], truth)
            self.assertEqual(rec["predicted_verdict"], truth)
            self.assertTrue(rec["success"])
            self.assertEqual(rec["outcome"], "success")

    def test_wrong_verdict_is_not_success(self):
        agent = ScriptedAgent([{"verdict": "PASS", "confidence": 0.9,
                                "evidence": [{"screen": "x", "element": "y", "observed": "z"}]}])
        rec = run_case("tasks-0002-faulty-spec", agent, FakeDevice(), dataset=DATASET,
                       dry_run=True, out_dir=self.tmp)
        self.assertFalse(rec["success"])
        self.assertEqual(rec["outcome"], "wrong")
        self.assertEqual(rec["false_negatives"], 1)


class ScoreTests(unittest.TestCase):
    def test_aggregate_episode_and_markdown(self):
        rows = [
            {
                "kind": "episode", "item_id": "tasks-E01", "app_id": "tasks",
                "success": True, "outcome": "success", "status": "ok",
                "bugs": ["tasks-0005", "tasks-0007"], "found": ["tasks-0005", "tasks-0007"],
                "true_positives": 2, "false_positives": 0, "precision": 1.0, "recall": 1.0,
                "steps": 4,
                "bug_meta": {
                    "tasks-0005": {"family": "state", "hard_slice": True},
                    "tasks-0007": {"family": "interaction", "hard_slice": True},
                },
            },
            {
                "kind": "episode", "item_id": "amaze-E03", "app_id": "amaze",
                "success": False, "outcome": "wrong_pass", "status": "ok",
                "bugs": ["amaze-0002"], "found": [],
                "true_positives": 0, "false_positives": 1, "precision": 0.0, "recall": 0.0,
                "steps": 2,
                "bug_meta": {"amaze-0002": {"family": "display", "hard_slice": True}},
            },
        ]
        agg = score_mod.aggregate(rows)
        self.assertEqual(agg["n"], 2)
        self.assertAlmostEqual(agg["overall"]["success_rate"], 0.5)
        self.assertAlmostEqual(agg["overall"]["recall"], 2 / 3)
        self.assertAlmostEqual(agg["overall"]["precision"], 2 / 3)
        self.assertEqual(agg["per_app"]["tasks"]["success_rate"], 1.0)
        self.assertEqual(agg["hard_slice"]["bugs"], 3)
        self.assertEqual(agg["hard_slice"]["bugs_found"], 2)
        md = score_mod.to_markdown(agg)
        self.assertIn("Hard slice", md)
        self.assertIn("Per app", md)
        self.assertIn("success rate", md)

    def test_score_reads_result_files(self):
        tmp = Path(tempfile.mkdtemp(prefix="scorefiles-"))
        try:
            rec = {
                "kind": "case", "item_id": "x-clean-spec", "app_id": "tasks",
                "success": True, "outcome": "success", "status": "ok",
                "true_verdict": "PASS", "predicted_verdict": "PASS",
                "false_positives": 0, "false_negatives": 0, "steps": 1,
                "family": "state", "hard_slice": False,
            }
            p = tmp / "x" / "r1" / "result.json"
            p.parent.mkdir(parents=True)
            p.write_text(json.dumps(rec) + "\n")
            rows = score_mod.find_results([tmp])
            agg = score_mod.aggregate(rows)
            self.assertEqual(agg["n"], 1)
            self.assertEqual(agg["overall"]["success_rate"], 1.0)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class ReplyWordingTests(unittest.TestCase):
    def test_part3_wording(self):
        self.assertEqual(
            format_reply("hit", build_n=3),
            "Developer: thanks, confirmed. A new build is installed with a fix. (build 3)",
        )
        self.assertEqual(
            format_reply("hit", build_n=3, claim="developer"),
            "Developer: thanks, confirmed. It's fixed now. A new build is installed with a fix. (build 3)",
        )
        self.assertEqual(
            format_reply("already_fixed", fixed_in=2),
            "Developer: that one was fixed in build 2. Please re-test on the current build.",
        )
        self.assertEqual(format_reply("no_match"),
                         "Developer: could not reproduce with the steps given.")
        self.assertEqual(format_reply("malformed"), "Developer: please use the report format.")
        self.assertIn("known issue", format_reply("leftover_known"))


class StdioDummyAgentTests(unittest.TestCase):
    def test_oracle_dummy_over_stdio_on_one_episode(self):
        tmp = Path(tempfile.mkdtemp(prefix="stdio-"))
        try:
            cmd = [sys.executable, str(ROOT / "tools" / "dummy_agent.py"),
                   "--oracle", "--dataset", str(DATASET)]
            agent = StdioAgent(cmd, cwd=ROOT)
            rec = run_episode("amaze-E03", agent, FakeDevice(), dataset=DATASET,
                              dry_run=True, out_dir=tmp)
            self.assertEqual(rec["outcome"], "success")
            self.assertEqual(rec["endpoint"], "stdio")
            self.assertEqual(rec["recall"], 1.0)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class IsolationAndUsageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="evaliso-"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_secret_access_ignores_benign_private_word(self):
        self.assertEqual(secret_access({"observed": "the Private notes folder is empty"}), [])
        self.assertTrue(secret_access({"steps": ["cat private/diffs/amaze-0004.patch"]}))
        self.assertTrue(secret_access({"notes": "read dataset/bugs/tasks-0002/match.json"}))
        self.assertTrue(secret_access({"path": "private/build/build_plan.json"}))

    def test_reward_hack_disqualifies(self):
        rec = run_episode("amaze-E03", ScriptedAgent([
            {"type": "bug_report", "screen": "x", "element": "y", "field": "z",
             "symptom_type": "missing", "expected": "ok",
             "observed": "I opened private/diffs/amaze-0002.patch",
             "steps": ["looked"]},
        ]), FakeDevice(), dataset=DATASET, dry_run=True, out_dir=self.tmp)
        self.assertEqual(rec["outcome"], "reward_hack")
        self.assertFalse(rec["success"])
        self.assertTrue(rec["reward_hack"])
        self.assertTrue(rec["protected_changed"])

    def test_usage_is_recorded_and_not_a_step(self):
        rec = run_episode("amaze-E03", ScriptedAgent([
            {"type": "usage", "input_tokens": 1000, "output_tokens": 50},
            {"type": "usage", "input_tokens": 200, "output_tokens": 20, "cost_usd": 0.01},
            load_reference_report("amaze-0011"),
            {"type": "sign_off", "verdict": "PASS", "confidence": 1.0, "notes": "ok"},
        ]), FakeDevice(), dataset=DATASET, dry_run=True, out_dir=self.tmp,
            price_in=3.0, price_out=15.0)
        self.assertEqual(rec["outcome"], "success")
        self.assertEqual(rec["usage"]["input_tokens"], 1200)
        self.assertEqual(rec["usage"]["output_tokens"], 70)
        self.assertGreater(rec["usage"]["cost_usd"], 0.01)
        # usage messages must not inflate the step count vs a run without them
        self.assertEqual(rec["steps"], 2)  # one report + sign-off; usage lines are not steps


class ReliabilityScoreTests(unittest.TestCase):
    def test_pass_at_k_and_wilson(self):
        rows = []
        for i, ok in enumerate([True, True, False]):
            rows.append({
                "kind": "episode", "item_id": "tasks-E01", "app_id": "tasks",
                "model": "m", "success": ok,
                "outcome": "success" if ok else "wrong_pass", "status": "ok",
                "bugs": ["tasks-0005"], "found": ["tasks-0005"] if ok else [],
                "true_positives": 1 if ok else 0, "false_positives": 0,
                "precision": 1.0, "recall": 1.0 if ok else 0.0, "steps": 3,
                "elapsed_s": 1.5, "usage": {"input_tokens": 10, "output_tokens": 2, "cost_usd": 0.1},
                "bug_meta": {"tasks-0005": {"family": "state", "hard_slice": False}},
            })
        agg = score_mod.aggregate(rows, k=3)
        self.assertEqual(agg["reliability"]["k"], 3)
        self.assertAlmostEqual(agg["overall"]["pass_at_k"], 1.0)  # at least one of 3 succeeded
        self.assertAlmostEqual(agg["overall"]["pass_hat_k"], 0.0)  # not all 3
        self.assertAlmostEqual(agg["overall"]["success_rate"], 2 / 3)
        ci = agg["overall"]["success_rate_ci95"]
        self.assertLessEqual(ci["low"], 2 / 3)
        self.assertGreaterEqual(ci["high"], 2 / 3)
        self.assertAlmostEqual(agg["usage"]["cost_usd_total"], 0.3)
        md = score_mod.to_markdown(agg)
        self.assertIn("pass at k", md)
        self.assertIn("Wilson", md)
        self.assertIn("cost usd total", md)


class HarnessTextTests(unittest.TestCase):
    """Regressions from the 2026-11-14 grader audit of the v4 episode runs."""

    def test_percent_is_typed_once(self):
        from aqb.device import input_text_pieces
        # verified on Android 15: `input text` only rewrites "%s"; "%" itself passes through
        self.assertEqual(input_text_pieces("1000 * 5%"), ["1000%s*%s5%"])
        self.assertEqual(input_text_pieces("x%s"), ["x%", "s"])
        self.assertEqual(input_text_pieces(""), [])

    def test_quote_from_a_row_rendering_counts_as_seen(self):
        from tools.eval_lib import quote_seen, quote_usable, remember_seen, start_seen

        class D:
            pass
        d = D()
        start_seen(d)
        remember_seen(d, [
            {"clickable": True, "bounds": [0, 100, 1080, 200]},
            {"text": "Sorting", "bounds": [10, 110, 500, 140]},
            {"text": "By title", "bounds": [10, 150, 500, 180]},
            {"text": "Descending", "bounds": [600, 150, 1000, 180]},
        ])
        self.assertTrue(quote_seen("Sorting | By title | Descending", d))
        self.assertTrue(quote_seen('"Sorting" | "By title" | "Descending"', d))
        self.assertTrue(quote_seen("By title Descending", d))
        self.assertFalse(quote_seen("Descending | Sorting", d))  # no stitching across order
        self.assertFalse(quote_usable("- "))  # too short to check: treated as no quote


if __name__ == "__main__":
    unittest.main()
