#!/usr/bin/env python3
"""Deterministic report matcher (no models).

A report matches a bug when it names a listed screen, a listed element or field,
the right symptom type, and (when the key lists values) both expected and
observed pass a two-sided value gate.

Rejects:
  * case-copy reports that paste case boilerplate or the whole prompt
  * list-every-defect reports that spray many symptoms, screens or elements
  * one-line reports with no specific expected/observed detail when the key
    lists values
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

SYMPTOMS = {
    "wrong_value", "missing", "not_persisted", "cut_off", "wrong_navigation",
    "no_effect", "duplicated", "overlap",
}

# Token / synonym groups. A key term matches if any token in its group appears.
SYNONYMS = {
    "file_list": {"file_list", "file list", "files", "file browser", "listing", "folder list"},
    "file_browser": {"file_browser", "file browser", "notebook", "files"},
    "notebook": {"notebook", "file browser", "main screen"},
    "editor": {"editor", "edit", "text area", "document"},
    "view_mode": {"view_mode", "view mode", "preview"},
    "share_into": {"share_into", "share into", "share", "shared"},
    "search_replace": {"search_replace", "search and replace", "replace", "search"},
    "file_info": {"file_info", "file information", "properties", "details"},
    "task_list": {"task_list", "task list", "list", "tasks"},
    "task_edit": {"task_edit", "task editor", "edit screen", "editor"},
    "tag_settings": {"tag_settings", "tag settings", "tags"},
    "widget": {"widget", "home screen widget"},
    "deck_picker": {"deck_picker", "deck picker", "decks"},
    "study": {"study", "reviewer", "review", "card"},
    "note_editor": {"note_editor", "note editor", "editor"},
    "card_browser": {"card_browser", "card browser", "browser"},
    "card_template_editor": {"card_template_editor", "template editor", "templates"},
    "tags_dialog": {"tags_dialog", "tags dialog", "tags"},
    "filtered_deck": {"filtered_deck", "filtered deck"},
    "shared_decks": {"shared_decks", "shared decks"},
    "export": {"export", "export dialog", "export options"},
    "home": {"home", "main screen", "budget"},
    "history": {"history", "transactions", "expense list"},
    "analytics": {"analytics", "graphs", "chart"},
    "settings": {"settings", "preferences"},
    "gallery": {"gallery", "grid", "timeline"},
    "viewer": {"viewer", "photo", "image"},
    "albums": {"albums", "album"},
    "details": {"details", "info", "metadata"},
    "vault": {"vault", "locked vault"},
    "dose_sheet": {"dose_sheet", "dose sheet", "dose form", "dose"},
    "plan": {"plan", "schedule"},
    "stock": {"stock", "inventory"},
    "records": {"records", "lab", "lab result", "results"},
    "reminders": {"reminders", "reminder", "notification"},
    "remote": {"remote", "connection", "url", "bookmark"},
    "drawer": {"drawer", "navigation drawer", "categories"},
    "bookmarks": {"bookmarks", "bookmark"},
}

BOILERPLATE = [
    "do not change or delete data unless a step tells you to",
    "report what you observed, not what you assume",
    "end with a json block",
    "already open on the device",
    "verdict\": \"pass|fail|inconclusive",
    "a colleague asked you to sweep",
    "when you believe the areas above have no remaining bugs",
    "when you have tested the areas above and reported every bug you found",
]

SYMPTOM_RE = re.compile(r"\b(" + "|".join(SYMPTOMS) + r")\b", re.I)


def normalize(text: str) -> str:
    if text is None:
        return ""
    s = unicodedata.normalize("NFKC", str(text)).lower()
    # invisible format characters (bidi isolates, zero-width marks), as in eval_lib._norm_text
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Cf")
    s = s.replace("\u2013", "-").replace("\u2014", "-")
    s = s.replace("\u2019", "'").replace("\u2018", "'")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def tokens(text: str) -> set[str]:
    s = normalize(text)
    return set(re.findall(r"[a-z0-9$+./-]+", s))


def group_for(term: str) -> set[str]:
    t = normalize(term)
    extra = set()
    if t in SYNONYMS:
        extra |= {normalize(x) for x in SYNONYMS[t]}
    # also index synonyms that contain this term
    for k, g in SYNONYMS.items():
        if t == k or t in {normalize(x) for x in g}:
            extra |= {normalize(x) for x in g}
            extra.add(k)
    extra.add(t)
    return extra


def _term_match(reported: str, listed: list[str]) -> bool:
    r = normalize(reported)
    if not r or not listed:
        return False
    # reject sprayed lists
    if len(re.split(r"[;|/]| and then |, and ", r)) > 4:
        return False
    rt = tokens(r)
    for item in listed:
        g = group_for(item)
        # a term must start a word ("edit" matches "editor", not "credit")
        if any(_word_start(normalize(gterm), r) or tokens(gterm) <= rt for gterm in g):
            return True
        # token overlap of the item itself
        it = tokens(item)
        if it and it <= rt:
            return True
    return False


def _word_start(term: str, text: str) -> bool:
    if not term:
        return False
    head = r"(?<![a-z0-9])" if term[:1].isalnum() else ""
    return re.search(head + re.escape(term), text) is not None


def value_hit(reported: str, needles: list[str]) -> bool:
    if not needles:
        return True
    r = normalize(reported)
    if not r:
        return False
    for n in needles:
        nn = normalize(n)
        if not nn:
            continue
        if nn in r:
            return True
        nt = tokens(n)
        if len(nt) >= 2 and nt <= tokens(r):
            return True
        # numeric token
        nums_n = re.findall(r"\d+(?:\.\d+)?", nn)
        nums_r = re.findall(r"\d+(?:\.\d+)?", r)
        if nums_n and all(x in nums_r for x in nums_n) and (nt & tokens(r)):
            return True
    return False


def is_list_every(report: dict) -> bool:
    blob = " ".join(str(report.get(k) or "") for k in ("screen", "element", "field", "expected", "observed", "steps"))
    b = normalize(blob)
    n_sym = len(set(SYMPTOM_RE.findall(b)))
    if n_sym >= 4:
        return True
    # many distinct screens or elements packed into one field
    for key in ("screen", "element"):
        # split on ; | and a spaced " / ", never inside a path like /storage/emulated/0/Alpha
        parts = [p.strip() for p in re.split(r"[;|]|\s/\s", str(report.get(key) or "")) if p.strip()]
        if len(parts) >= 4:
            return True
    if len(b) > 1200 and n_sym >= 3:
        return True
    return False


def is_case_copy(report: dict, case_text: str | None) -> bool:
    blob = normalize(" ".join(
        str(report.get(k) or "") if not isinstance(report.get(k), list)
        else " ".join(map(str, report.get(k)))
        for k in ("screen", "element", "field", "expected", "observed", "steps", "notes")
    ))
    if any(p in blob for p in BOILERPLATE):
        return True
    if not case_text:
        return False
    ct = normalize(case_text)
    # long verbatim slice of the case (excluding short needles)
    if len(blob) >= 80 and blob in ct:
        return True
    # high overlap of 5-grams with the case when the report is long
    def grams(s, n=5):
        w = re.findall(r"[a-z0-9$+]+", s)
        return set(tuple(w[i:i+n]) for i in range(max(0, len(w)-n+1)))
    g_r, g_c = grams(blob), grams(ct)
    if g_r and g_c and len(g_r) >= 12:
        overlap = len(g_r & g_c) / len(g_r)
        if overlap >= 0.85:
            return True
    return False


MAX_FIELD_CHARS = 500
MIRROR_JACCARD = 0.8
MIRROR_MIN_CHARS = 60


def _alt_re(alt: str) -> re.Pattern:
    """Compile one concept alternative.

    A trailing '*' makes it a word-start prefix ("duplicat*" matches "duplicated").
    Without '*' the alternative must match as a whole word or phrase, so "2"
    does not match "20" and "double" does not match "doubled".
    """
    a = normalize(alt)
    prefix = a.endswith("*")
    a = a.rstrip("*").strip()
    # word boundaries only on edges that are letters or digits, so "(1)"
    # matches inside "readme(1).txt" and "$5" matches "costs $5"
    head = r"(?<![a-z0-9])" if a[:1].isalnum() else ""
    tail = "" if prefix or not a[-1:].isalnum() else r"(?![a-z0-9])"
    # a number must be whole: "2" does not match inside "1.2", "2.5", "2,000", "10-2" or "-2";
    # a zero decimal part is the same value ("2,850" matches "2,850.00", "2" matches "2.0")
    if a[:1].isdigit():
        head += r"(?<![0-9][.,])(?<!-)"
    if a[-1:].isdigit() and not prefix:
        tail += r"(?!,[0-9])(?!-[0-9])(?!\.[0-9]*[1-9])"
    return re.compile(head + re.escape(a) + tail)


def concepts_hit(text: str, groups: list[list[str]]) -> int:
    """Return how many concept groups have at least one alternative in text."""
    t = normalize(text)
    n = 0
    for g in groups or []:
        if any(_alt_re(a).search(t) for a in g if normalize(a).rstrip("*").strip()):
            n += 1
    return n


# Words that say "something is wrong" without saying what. A concept hit on one of these alone
# never counts as concrete evidence (v3): a vague report must not match by these words.
GENERIC = {
    "wrong", "error", "errors", "off", "broken", "bug", "buggy", "incorrect", "issue", "issues",
    "problem", "problems", "weird", "strange", "bad", "fail", "fails", "failed", "failing",
    "not work", "not working", "doesn t work", "does not work", "look", "looks", "seem", "seems",
    "odd", "unexpected", "glitch", "different", "changed", "not right", "not correct",
}


def specific_hit(text: str, groups: list[list[str]], place: set[str] | None = None) -> bool:
    """True if text has a concrete anchor: a digit, a quoted value, or a concept alternative that is
    neither a generic complaint word nor a word that only names the place (screen/element/field)."""
    raw = text or ""
    if re.search(r"\d", raw) or re.search(r"[\"'“‘][^\"'”’]{2,}[\"'”’]", raw):
        return True
    t = normalize(raw)
    for g in groups or []:
        for a in g:
            core = normalize(a).rstrip("*").strip()
            if core and core not in GENERIC and core not in (place or set()) and _alt_re(a).search(t):
                return True
    return False


def _symptoms(key: dict) -> set[str]:
    s = key.get("symptom_types") or [key.get("symptom_type")]
    return {normalize(x) for x in s if x}


def _side_ok(text: str, key: dict, side: str) -> bool:
    """Concept groups (v2 keys) or, for keys without them, legacy needles."""
    groups = key.get(f"{side}_concepts") or []
    needles = key.get(f"{side}_contains_any") or []
    if not groups and not needles:
        return True
    if groups:
        # v2 keys: concept groups only (legacy needles' numeric rule is too loose)
        return concepts_hit(text, groups) == len(groups)
    return value_hit(text, needles)


def is_mirror(report: dict) -> bool:
    """Expected and observed say the same thing (e.g. both fields hold both texts)."""
    e = normalize(report.get("expected") or "")
    o = normalize(report.get("observed") or "")
    if len(e) >= 20 and len(o) >= 20 and (e in o or o in e):
        return True
    # token overlap only for long fields: short opposite statements
    # ("c1 and c3" / "not c1 and c3") legitimately share most words
    te, to = tokens(e), tokens(o)
    if len(e) >= MIRROR_MIN_CHARS and len(o) >= MIRROR_MIN_CHARS:
        return len(te & to) / len(te | to) >= MIRROR_JACCARD
    return False


def is_overlong(report: dict) -> bool:
    return any(len(str(report.get(k) or "")) > MAX_FIELD_CHARS for k in ("screen", "element", "field", "expected", "observed"))


def too_vague(report: dict, key: dict) -> bool:
    exp_need = (key.get("expected_contains_any") or []) + (key.get("expected_concepts") or [])
    obs_need = (key.get("observed_contains_any") or []) + (key.get("observed_concepts") or [])
    if not exp_need and not obs_need:
        return False
    exp = normalize(report.get("expected") or "")
    obs = normalize(report.get("observed") or "")
    if not exp or not obs:
        return True
    if len(exp) + len(obs) < 5:
        return True
    vague = {"it looks wrong", "it should work", "broken", "not working", "nothing happens", "wrong", "bug"}
    if exp in vague or obs in vague:
        return True
    return False


def match_key(report: dict, key: dict, case_text: str | None = None) -> dict:
    """Return {match: bool, reason: str}."""
    if not isinstance(report, dict):
        return {"match": False, "reason": "malformed"}
    if is_list_every(report):
        return {"match": False, "reason": "list_every_defect"}
    if is_case_copy(report, case_text):
        return {"match": False, "reason": "case_copy"}
    if is_overlong(report):
        return {"match": False, "reason": "spray"}
    if too_vague(report, key):
        return {"match": False, "reason": "vague"}
    if is_mirror(report):
        return {"match": False, "reason": "mirror"}
    # v4 anchored reports. The harness sets _quote_seen when it checked observed_quote against
    # every text it showed the agent; an invented or missing quote earns no credit.
    if "_quote_seen" in report and not report["_quote_seen"]:
        return {"match": False, "reason": "unverified_quote"}
    if report.get("_quote_seen") and anchor_match(report, key):
        return {"match": True, "reason": "anchored"}
    st = normalize(report.get("symptom_type") or "")
    if st not in SYMPTOMS:
        return {"match": False, "reason": "bad_symptom"}
    # symptom_type is advisory (v3): testers label the same defect differently (missing vs
    # no_effect). Location and the two-sided value gate decide; the label only breaks ties.
    # location: screen plus element or field, or else both element and field.
    # Element and field may be named the other way round (testers mix them up).
    ef = (key.get("elements") or []) + (key.get("fields") or [])
    screen_ok = _term_match(report.get("screen") or "", key.get("screens") or [])
    el_ok = _term_match(report.get("element") or "", ef)
    fl_ok = _term_match(report.get("field") or "", ef)
    loc = " ".join(str(report.get(k) or "") for k in ("screen", "element", "field"))
    loc_ok = concepts_hit(loc, [key["location_concepts"]]) == 1 if key.get("location_concepts") else False
    if not (loc_ok or (screen_ok and (el_ok or fl_ok)) or (el_ok and fl_ok)):
        return {"match": False, "reason": "location"}
    # two-sided value gate: expected states the intended behaviour, observed the defect
    if not _side_ok(report.get("expected") or "", key, "expected"):
        return {"match": False, "reason": "expected_value"}
    if not _side_ok(report.get("observed") or "", key, "observed"):
        return {"match": False, "reason": "observed_value"}
    # v3: the observed side must carry something concrete, not only generic complaint words
    place = {normalize(x).rstrip("*").strip() for x in (key.get("location_concepts") or [])
             + (key.get("screens") or []) + (key.get("elements") or []) + (key.get("fields") or [])}
    if key.get("observed_concepts") and not specific_hit(report.get("observed") or "", key["observed_concepts"], place):
        return {"match": False, "reason": "generic"}
    return {"match": True, "reason": "ok"}


def _anchor_hit(text: str, pats: list[str]) -> bool:
    t = normalize(text or "")
    for pat in pats or []:
        if len(pat) > 2 and pat.startswith("/") and pat.endswith("/"):
            if re.search(pat[1:-1], t):
                return True
        elif normalize(pat) and normalize(pat) in t:
            return True
    return False


def anchor_match(report: dict, key: dict) -> bool:
    """Deterministic, wording-free match: the element the agent pointed at is one of the key's
    anchor elements AND the verbatim on-screen quote shows the buggy value. Keys whose defect
    has no visible value (something missing) leave anchors.observed empty and use the prose path."""
    anc = key.get("anchors") or {}
    node = report.get("anchor_node") or {}
    if not anc.get("elements") or not anc.get("observed") or not node:
        return False
    node_text = " ".join(str(node.get(k) or "") for k in ("text", "desc", "id"))
    node_text += " " + " ".join(node.get("contains") or [])
    if not (_anchor_hit(node_text, anc["elements"]) and _anchor_hit(report.get("observed_quote") or "", anc["observed"])):
        return False
    # the prose must still name the defect (one concept group on either side) with a listed symptom:
    # pointing at the right value while claiming another problem is not enough
    concept = (concepts_hit(report.get("observed") or "", key.get("observed_concepts") or []) >= 1
               or concepts_hit(report.get("expected") or "", key.get("expected_concepts") or []) >= 1)
    return concept and normalize(report.get("symptom_type") or "") in _symptoms(key)


def match_score(report: dict, key: dict) -> int:
    """Tie-breaker when one report matches several keys: concept groups hit, plus one for a
    symptom_type the key lists."""
    return (concepts_hit(report.get("expected") or "", key.get("expected_concepts") or [])
            + concepts_hit(report.get("observed") or "", key.get("observed_concepts") or [])
            + (normalize(report.get("symptom_type") or "") in _symptoms(key)))


def load_key(bug_dir: Path) -> dict:
    return json.loads((bug_dir / "match.json").read_text(encoding="utf-8"))


def episode_outcome(report: dict, episode: dict, bug_keys: dict, case_texts: dict | None = None) -> dict:
    """Classify one report against an episode.

    Returns kind: hit | already_fixed | leftover_known | no_match | malformed
    leftover_known is scored as neither a hit nor a false positive ('known issue').
    """
    if not isinstance(report, dict) or report.get("type") not in (None, "bug_report"):
        if isinstance(report, dict) and report.get("type") == "sign_off":
            return {"kind": "sign_off", "reply": "sign_off"}
        return {"kind": "malformed", "reply": "Developer: please use the report format."}
    present = set(episode.get("present") or [])
    leftover = set(episode.get("known_leftover") or [])
    hits = []
    leftover_hits = []
    already = []
    for bug_id, key in bug_keys.items():
        ct = (case_texts or {}).get(bug_id)
        r = match_key(report, key, ct)
        if not r["match"]:
            continue
        if bug_id in present:
            hits.append(bug_id)
        elif bug_id in leftover:
            leftover_hits.append(bug_id)
        else:
            already.append(bug_id)
    if leftover_hits and not hits:
        return {
            "kind": "leftover_known",
            "bugs": leftover_hits,
            "reply": "Developer: known issue. This is already tracked and is not part of the current sweep.",
        }
    if hits:
        # one report describes one defect: credit only the best-matching bug, preferring a bug
        # not credited yet (under the fast protocol credited bugs stay in the build and keep
        # matching, so the best match among all hits could repeat a credit and hide a new one)
        credited = set(episode.get("credited") or [])
        pool = [b for b in hits if b not in credited] or hits
        best = max(sorted(pool), key=lambda b: match_score(report, bug_keys[b]))
        return {
            "kind": "hit",
            "bugs": [best],
            "reply": "Developer: thanks, confirmed. A new build is installed with a fix.",
        }
    if already:
        return {
            "kind": "already_fixed",
            "bugs": already,
            "reply": "Developer: that one was fixed in an earlier build. Please re-test on the current build.",
        }
    return {"kind": "no_match", "reply": "Developer: could not reproduce with the steps given."}


def check_reference_reports(dataset: Path) -> list[str]:
    """Return a list of problems: correct must match, vague and wrong_bug must not."""
    problems = []
    man = json.loads((dataset / "manifest.json").read_text())
    for bug_id in man.get("bugs", []):
        d = dataset / "bugs" / bug_id
        key = load_key(d)
        refs = json.loads((d / "reference_reports.json").read_text())
        # nearest specified case text, if any
        case_text = None
        cases = sorted((dataset / "cases").glob(f"{bug_id}-*/agent_input.md"))
        if cases:
            case_text = cases[0].read_text(encoding="utf-8")
        ok = match_key(refs["correct"], key, case_text)
        if not ok["match"]:
            problems.append(f"{bug_id}: correct report did not match ({ok['reason']})")
        v = match_key(refs["vague"], key, case_text)
        if v["match"]:
            problems.append(f"{bug_id}: vague report matched")
        w = match_key(refs["wrong_bug"], key, case_text)
        if w["match"]:
            problems.append(f"{bug_id}: wrong_bug report matched")
    return problems


if __name__ == "__main__":
    import argparse, sys
    ap = argparse.ArgumentParser()
    ap.add_argument("dataset", type=Path, default=Path("dataset"), nargs="?")
    args = ap.parse_args()
    probs = check_reference_reports(args.dataset)
    for p in probs:
        print("FAIL", p)
    print(f"{len(probs)} reference-report failures")
    sys.exit(1 if probs else 0)
