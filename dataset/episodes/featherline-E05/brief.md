# QA sweep: Featherline
The app is installed and open. A colleague asked you to sweep these areas before release:
- group setup and scheduling
- the medicine list
- the journal

## Preconditions
Fresh install with no medications, plans or lab results.

## Changed in this build
- Group editor first-dose picker: a picked value is now compared with the stored one before it is applied.
- Journal entry list: loaded entries are now cached in memory between tab switches.
- Medicine list category headers: headings are now generated only for categories holding at least one medicine.
- Night owl mode in the group editor: the explanatory caption now builds its cut-off text separately from the remaining values.

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
