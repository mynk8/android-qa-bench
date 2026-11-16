# QA sweep: Featherline
The app is installed and open. A colleague asked you to sweep these areas before release:
- medication groups and medicines
- lab test results under Settings > Calibration

## Preconditions
Fresh install with no medications, plans or lab results.

## Changed in this build
- Medicine editor category picker: category labels are now resolved from shared string resources.
- Lab test results under Calibration: the units for each test are now fetched together with the test list.
- Group editor history generation: generated past doses are now recorded the same way as doses logged live.

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
