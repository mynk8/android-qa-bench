# QA sweep: Featherline
The app is installed and open. A colleague asked you to sweep these areas before release:
- the Home tab cards
- adding medicines: categories and preparation forms
- medication groups and their schedules

## Preconditions
Fresh install with no medications, plans or lab results.

## Changed in this build
- Antiandrogen card on Home: the dose it shows is now looked up across all of the day's schedule slots.
- Preparation form picker: every amount field is now carried over when the form is changed.
- Group editor schedule section: reminder times in the section are now ordered chronologically.

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
