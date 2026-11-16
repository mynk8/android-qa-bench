# QA sweep: AnkiDroid
The app is installed and open. A colleague asked you to sweep these areas before release:
- deck management
- adding and editing notes
- card scheduling
- the study statistics screen

## Preconditions
Deck Spanish has 4 Basic notes: comer (tagged verb), mesa, hola and agua. Deck French has 3 Basic notes: bonjour, pain and chat. No other tags exist.

## Changed in this build
- Set due date dialog: the day and range inputs are now handled by a common text-input component.
- Add note pickers: a switch of note model is now stored to the collection straight away.
- Nested deck dialog: the text typed for the inner deck is now handled by a different validity test.
- Study statistics screen: the charts are now built by the backend statistics renderer instead of native views.

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
