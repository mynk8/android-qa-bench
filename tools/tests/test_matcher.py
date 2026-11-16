"""Unit tests for the v2 report matcher (concept groups, symptom sets, anti-gaming)."""
from __future__ import annotations

import unittest

from dataset_tools.matcher import episode_outcome, match_key

# A v2 key for a "subtask lost / duplicated" bug, written the way migrated keys are.
KEY = {
    "screens": ["task edit", "task list"],
    "elements": ["subtask"],
    "fields": ["subtasks"],
    "symptom_types": ["duplicated", "missing", "wrong_value"],
    "expected_concepts": [["subtask*", "sub-task*", "child*"], ["one", "1", "single", "once", "under", "nested", "belong*", "attached"]],
    "observed_concepts": [["twice", "two", "2", "duplicat*", "double*", "again", "not under", "top level", "top-level", "separate*", "missing", "orphan*", "not attached", "own task"]],
}

NATURAL = {
    "screen": "Task editor",
    "element": "Subtasks section",
    "field": "subtasks",
    "symptom_type": "duplicated",
    "expected": "Plan party should have one subtask, Buy cake",
    "observed": "Buy cake shows up two times under Plan party",
    "steps": ["Create task", "add subtask before saving", "save and reopen"],
}


class ValueGate(unittest.TestCase):
    def test_natural_paraphrase_matches(self):
        self.assertEqual(match_key(NATURAL, KEY)["reason"], "ok")

    def test_own_data_names_still_match(self):
        r = dict(NATURAL, expected="Groceries task should keep its single child item Eggs",
                 observed="Eggs ended up as a separate top-level task")
        self.assertTrue(match_key(r, KEY)["match"])

    def test_observed_without_symptom_concept_rejected(self):
        r = dict(NATURAL, observed="The subtask Buy cake is shown in bold")
        self.assertEqual(match_key(r, KEY)["reason"], "observed_value")

    def test_number_alt_is_whole_token(self):
        key = dict(KEY, observed_concepts=[["2"]])
        r = dict(NATURAL, observed="Buy cake count shows 20")
        self.assertFalse(match_key(r, key)["match"])

    def test_symbol_edged_alt_matches_inside_word(self):
        key = dict(KEY, observed_concepts=[["(1)"]])
        r = dict(NATURAL, observed="the second copy is again readme(1).txt")
        self.assertTrue(match_key(r, key)["match"])

    def test_curly_apostrophe_normalized(self):
        key = dict(KEY, observed_concepts=[["doesn't"]])
        r = dict(NATURAL, observed="Buy cake doesn’t stay under Plan party")
        self.assertTrue(match_key(r, key)["match"])

    def test_prefix_alt_needs_star(self):
        key = dict(KEY, observed_concepts=[["double"]])
        r = dict(NATURAL, observed="the row is doubled")
        self.assertFalse(match_key(r, key)["match"])
        key = dict(KEY, observed_concepts=[["double*"]])
        self.assertTrue(match_key(r, key)["match"])


class SymptomSet(unittest.TestCase):
    def test_any_listed_symptom_accepted(self):
        self.assertTrue(match_key(dict(NATURAL, symptom_type="missing"), KEY)["match"])

    def test_unlisted_symptom_is_advisory(self):
        # v3: a different but valid label does not reject an otherwise correct report
        self.assertTrue(match_key(dict(NATURAL, symptom_type="cut_off"), KEY)["match"])

    def test_invalid_symptom_rejected(self):
        self.assertEqual(match_key(dict(NATURAL, symptom_type="weird"), KEY)["reason"], "bad_symptom")

    def test_legacy_single_symptom_still_read(self):
        key = {k: v for k, v in KEY.items() if k != "symptom_types"}
        key["symptom_type"] = "duplicated"
        self.assertTrue(match_key(NATURAL, key)["match"])
        # the legacy label still counts in tie-breaks (match_score), not as a gate
        from dataset_tools.matcher import match_score
        self.assertGreater(match_score(NATURAL, key), match_score(dict(NATURAL, symptom_type="missing"), key))


class Location(unittest.TestCase):
    def test_element_alone_locates(self):
        r = dict(NATURAL, screen="Main screen")
        self.assertTrue(match_key(r, KEY)["match"])

    def test_wrong_screen_and_one_shared_field_rejected(self):
        # a sibling bug on another screen often shares a generic field name
        r = dict(NATURAL, screen="About", element="version label", field="subtasks")
        self.assertEqual(match_key(r, KEY)["reason"], "location")

    def test_location_concepts_locate_loose_names(self):
        key = dict(KEY, location_concepts=["deck list", "deck*"])
        r = dict(NATURAL, screen="Deck list", element="arrow", field="icon")
        self.assertTrue(match_key(r, key)["match"])
        self.assertFalse(match_key(r, KEY)["match"])

    def test_nothing_located_rejected(self):
        r = dict(NATURAL, screen="About", element="version label", field="version")
        self.assertEqual(match_key(r, KEY)["reason"], "location")


class AntiGaming(unittest.TestCase):
    def test_mirrored_fields_rejected(self):
        both = NATURAL["expected"] + ". " + NATURAL["observed"]
        r = dict(NATURAL, expected=both, observed=both)
        self.assertEqual(match_key(r, KEY)["reason"], "mirror")

    def test_short_opposite_statements_are_not_mirror(self):
        r = dict(NATURAL, expected="Buy cake under Plan party, once", observed="Plan party under Buy cake, twice")
        self.assertNotEqual(match_key(r, KEY)["reason"], "mirror")
        r = dict(NATURAL, expected="Subtask Buy cake once", observed="Subtask Buy cake not once")
        self.assertNotEqual(match_key(r, KEY)["reason"], "mirror")

    def test_terse_exact_values_not_vague(self):
        key = dict(KEY, expected_concepts=[["cat"]], observed_concepts=[["$1"]])
        r = dict(NATURAL, expected="cat", observed="$1")
        self.assertTrue(match_key(r, key)["match"])

    def test_overlong_field_rejected(self):
        r = dict(NATURAL, observed=NATURAL["observed"] + " " + "twice duplicated missing " * 40)
        self.assertEqual(match_key(r, KEY)["reason"], "spray")

    def test_vague_still_rejected(self):
        r = dict(NATURAL, expected="it should work", observed="it looks wrong")
        self.assertEqual(match_key(r, KEY)["reason"], "vague")


class EpisodeCredit(unittest.TestCase):
    def test_one_report_fixes_at_most_one_bug(self):
        keys = {"b-1": KEY, "b-2": dict(KEY)}
        ep = {"present": ["b-1", "b-2"], "known_leftover": []}
        out = episode_outcome(NATURAL, ep, keys)
        self.assertEqual(out["kind"], "hit")
        self.assertEqual(len(out["bugs"]), 1)


if __name__ == "__main__":
    unittest.main()


class AnchoredReports(unittest.TestCase):
    KEY = {**KEY, "anchors": {"elements": ["Alpha (1)"], "observed": ["alpha (1)"]}}

    def test_unverified_quote_rejected(self):
        r = dict(NATURAL, observed_quote="made up", _quote_seen=False)
        self.assertEqual(match_key(r, self.KEY)["reason"], "unverified_quote")

    def test_anchored_match_ignores_wording(self):
        r = {"screen": "x", "element": "y", "field": "z", "symptom_type": NATURAL["symptom_type"],
             "expected": NATURAL["expected"], "observed": NATURAL["observed"],
             "observed_quote": "Alpha (1)", "_quote_seen": True,
             "anchor_node": {"text": "Alpha (1)", "id": "firstline"}}
        self.assertEqual(match_key(r, self.KEY)["reason"], "anchored")

    def test_anchor_with_unrelated_claim_not_anchored(self):
        r = {"screen": "x", "element": "y", "field": "z", "symptom_type": "overlap",
             "expected": "fine", "observed": "odd", "observed_quote": "Alpha (1)", "_quote_seen": True,
             "anchor_node": {"text": "Alpha (1)"}}
        self.assertNotEqual(match_key(r, self.KEY)["reason"], "anchored")

    def test_anchor_on_other_element_falls_back_to_prose(self):
        r = dict(NATURAL, observed_quote="Beta", _quote_seen=True, anchor_node={"text": "Beta"})
        self.assertNotEqual(match_key(r, self.KEY)["reason"], "anchored")

    def test_offline_reports_without_quote_field_still_use_prose(self):
        self.assertTrue(match_key(NATURAL, self.KEY)["match"])
