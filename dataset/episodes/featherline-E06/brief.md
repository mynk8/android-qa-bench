# QA sweep: Featherline
The app is installed and open. A colleague asked you to sweep these areas before release:
- medication groups and cards
- Settings
- adding and editing medicines

## Preconditions
Fresh install with no medications, plans or lab results.

## Changed in this build
- Secondary caption on medication cards: its text is now resolved by a helper shared with reminders and the widget.
- Settings measurement editor: the editing sheet is now built as a bottom sheet over Settings.
- Preparation form picker: the available form options are now drawn from a single shared catalogue.

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
