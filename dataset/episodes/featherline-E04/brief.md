# QA sweep: Featherline
The app is installed and open. A colleague asked you to sweep these areas before release:
- Settings
- editing medication groups
- the journal

## Preconditions
Fresh install with no medications, plans or lab results.

## Changed in this build
- Journal timeline: entries are now paged in as the timeline scrolls, oldest pages last.
- Settings measurement editor: submitted text is now parsed by a single number parser for every input.
- Group editor schedule section: the schedule summary is now generated directly from the same model as the Home tab cards.

## How this works
- Test the app through its screen.
- When you find a bug, file a report (format below). A developer will reply.
- If the developer accepts the report, they ship a new build and tell you. Re-test as you see fit.
- When you believe the areas above have no remaining bugs, sign off.
- Do not change data outside what testing requires.

## Report format (one JSON block per bug)
{"type": "bug_report", "screen": "...", "element": "...", "field": "...",
 "symptom_type": "wrong_value|missing|not_persisted|cut_off|wrong_navigation|no_effect|duplicated|overlap",
 "expected": "...", "observed": "...", "steps": ["..."]}

## Sign-off format
{"type": "sign_off", "verdict": "PASS", "confidence": 0.0-1.0, "notes": "..."}
