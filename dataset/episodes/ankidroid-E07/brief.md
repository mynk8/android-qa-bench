# QA sweep: AnkiDroid
The app is installed and open. A colleague asked you to sweep these areas before release:
- study session settings
- browsing and searching cards
- app preferences

## Preconditions
Deck Spanish has 4 Basic notes: comer (tagged verb), mesa, hola and agua. Deck French has 3 Basic notes: bonjour, pain and chat. No other tags exist.

## Changed in this build
- Timebox settings: the minutes field is now resolved from the collection's on/off state when the screen opens.
- Appearance preferences: a theme change is now applied to open screens without restarting the app.
- Study screen answer buttons: the interval shown on each button is now computed directly by the backend scheduler.
- Card browser header: the subtitle is now updated only when a search finishes.

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
