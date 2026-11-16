# QA sweep: Featherline
The app is installed and open. A colleague asked you to sweep these areas before release:
- adding medicines and choosing their preparation form
- medication cards and lists
- the Medicines list

## Preconditions
Fresh install with no medications, plans or lab results.

## Changed in this build
- Medicines list header: the header is now built from the same data source as the list below.
- Dosing subtitle on medication cards: pill fractions are now formatted through a single general rule.
- Category picker in the medicine editor: categories are now taken from one shared catalogue.
- Preparation form picker: forms with several variants now resolve their sub-type only from an explicit pick.

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
