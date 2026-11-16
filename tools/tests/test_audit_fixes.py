"""Regression tests for the defects found in the 2026-11 grader and scoring audit.

Each test fails on commit 9976c14 and passes after the fix it names.
"""
from __future__ import annotations

import unittest
from pathlib import Path

from dataset_tools.matcher import _alt_re, _term_match, episode_outcome, normalize
from tools import eval_lib, leaderboard

ROOT = Path(__file__).resolve().parents[2]

KEY = {
    "screens": ["task edit", "task list"],
    "elements": ["subtask"],
    "fields": ["subtasks"],
    "symptom_types": ["duplicated"],
    "expected_concepts": [["subtask*"], ["one", "single", "once"]],
    "observed_concepts": [["twice", "two", "duplicat*"]],
}
REPORT = {
    "type": "bug_report",
    "screen": "Task editor",
    "element": "Subtasks section",
    "field": "subtasks",
    "symptom_type": "duplicated",
    "expected": "Plan party should have one subtask, Buy cake",
    "observed": "Buy cake shows up two times under Plan party",
    "steps": ["Create task", "add subtask", "save and reopen"],
}


class TieBreakPrefersUncredited(unittest.TestCase):
    """F1: a report that matches two present regressions must credit one not yet credited."""

    def test_uncredited_bug_wins(self):
        keys = {"x-0001": KEY, "x-0002": KEY}
        state = {"present": ["x-0001", "x-0002"], "credited": ["x-0001"]}
        self.assertEqual(episode_outcome(REPORT, state, keys, None)["bugs"], ["x-0002"])

    def test_without_credits_the_old_order_holds(self):
        keys = {"x-0001": KEY, "x-0002": KEY}
        out = episode_outcome(REPORT, {"present": ["x-0001", "x-0002"]}, keys, None)
        self.assertEqual(out["bugs"], ["x-0001"])

    def test_classify_report_passes_credited(self):
        keys = {"x-0001": KEY, "x-0002": KEY}
        ep = {"bugs": ["x-0001", "x-0002"], "observable": {}}
        out = eval_lib.classify_report(REPORT, ep, {"x-0001", "x-0002"}, keys, None, {"x-0001"})
        self.assertEqual(out["bugs"], ["x-0002"])


class NumericAlternativesAreWholeNumbers(unittest.TestCase):
    """A bare number in a key must not match a fragment of a decimal, a grouped number or a range."""

    def test_fragments_do_not_match(self):
        for text in ("1.2", "2.5", "2,000", "10-2", "-2"):
            self.assertIsNone(_alt_re("2").search(normalize(text)), text)

    def test_whole_numbers_still_match(self):
        for text in ("2 items", "shows 2.", "(2)", "it is 2, not 3", "x 2"):
            self.assertIsNotNone(_alt_re("2").search(normalize(text)), text)

    def test_decimal_alternative_matches_itself(self):
        self.assertIsNotNone(_alt_re("2.5").search("value 2.5 shown"))

    def test_zero_decimal_part_is_the_same_value(self):
        self.assertIsNotNone(_alt_re("2,850").search("= 2,850.00"))
        self.assertIsNotNone(_alt_re("2").search("shows 2.00 now"))


class LocationTermsMatchAtWordStart(unittest.TestCase):
    """A location term must start a word: 'edit' is not inside 'credit'."""

    def test_inside_a_word_is_rejected(self):
        self.assertFalse(_term_match("credit card", ["edit"]))
        self.assertFalse(_term_match("checklist", ["list"]))

    def test_word_start_and_phrase_still_match(self):
        self.assertTrue(_term_match("Task editor", ["task edit"]))
        self.assertTrue(_term_match("editor", ["edit"]))


class NormalizeStripsInvisibleCharacters(unittest.TestCase):
    def test_bidi_isolates_removed(self):
        self.assertEqual(normalize("12⁨ cards⁩"), "12 cards")


class ShortQuotesNeedAWholeToken(unittest.TestCase):
    """A one-character quote such as '2' must match a whole token, not any text containing 2."""

    class Dev:
        def __init__(self, seen: set[str]):
            self._aqb_seen = seen

    def test_digit_inside_number_rejected(self):
        self.assertFalse(eval_lib.quote_seen("2", self.Dev({"12 items"})))

    def test_digit_as_token_accepted(self):
        self.assertTrue(eval_lib.quote_seen("2", self.Dev({"2 items"})))


class SecretPathsCoverAnswerKeys(unittest.TestCase):
    def test_release_note_key_is_flagged(self):
        self.assertTrue(eval_lib._secret_hits("cat private/release_notes/notes.json"))
        self.assertTrue(eval_lib._secret_hits("ls private/review/scorer"))

    def test_app_folder_named_private_is_not_flagged(self):
        self.assertFalse(eval_lib._secret_hits("Notes saved in Documents/Private/Shared"))


class CostIsMissingNotZero(unittest.TestCase):
    """F3: a run whose log has no cost must not count as $0."""

    def test_missing_log_is_none(self):
        self.assertIsNone(leaderboard.agent_cost(ROOT / "results" / "nope", "x", 0))

    def test_deepseek_cost_recovered_from_step_usage(self):
        run = ROOT / "results" / "deepseek-v4.1-flash-high"
        eps, _ = leaderboard.load([run])
        block = leaderboard.episode_block(eps)
        self.assertEqual(block["cost_episodes_logged"], 51)
        self.assertGreater(block["cost_usd_per_episode"], 0.05)

    def test_session_without_cost_data_is_excluded(self):
        run = ROOT / "results" / "gpt-6-luna-max"
        eps, _ = leaderboard.load([run])
        self.assertEqual(leaderboard.episode_block(eps)["cost_episodes_logged"], 50)


class ReportCapIsNotTheActionCap(unittest.TestCase):
    """F4: an episode ended by the report limit is labelled report_cap, not cut off at 300 actions."""

    def test_stored_report_cap_runs_are_labelled(self):
        run = ROOT / "results" / "deepseek-v4.1-flash-high"
        eps, _ = leaderboard.load([run])
        block = leaderboard.episode_block(eps)
        self.assertAlmostEqual(block["stopping"]["report_cap"], round(2 / 51, 3))


class RescoreFixesTheTieBreakCase(unittest.TestCase):
    """F1 on stored data: Sol tasks-E05 report 2 matches tasks-0018 and tasks-0019 equally."""

    def test_sol_tasks_e05_credits_both(self):
        from tools.rescore_episodes import rescore
        run = ROOT / "results" / "gpt-6.1-sol-low"
        d = next((run / "episodes" / "tasks-E05").glob("*/result.json")).parent
        out = rescore(d, run, check=True)
        self.assertEqual(out["found"], ["tasks-0018", "tasks-0019"])

    def test_check_mode_keeps_unusable_quotes_as_no_quote(self):
        """--check must not turn an unusable quote ('- ') into an unverified one."""
        from tools.rescore_episodes import rescore
        run = ROOT / "results" / "claude-haiku-5.5"
        d = next((run / "episodes" / "markor-E05").glob("*/result.json")).parent
        out = rescore(d, run, check=True)
        stored = __import__("json").loads((d / "result.json").read_text())
        self.assertEqual(out["found"], sorted(stored["found"]))


class ScrubPaths(unittest.TestCase):
    def test_home_paths_replaced_but_nested_home_kept(self):
        from tools.scrub_paths import scrub
        text = ("at /home/alice/workspace/x and /tmp/aqb/home/sessions/s.jsonl and /Users/bob/a"
                " (file:///home/alice/lib.js)")
        new, n = scrub(text)
        self.assertEqual(n, 3)
        self.assertEqual(scrub(new)[1], 0)
        self.assertIn("/home/USER/workspace", new)
        self.assertIn("/tmp/aqb/home/sessions", new)
        self.assertIn("/Users/USER/a", new)


if __name__ == "__main__":
    unittest.main()
