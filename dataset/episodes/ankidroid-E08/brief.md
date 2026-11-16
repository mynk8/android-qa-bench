# QA sweep: AnkiDroid
The app is installed and open. A colleague asked you to sweep these areas before release:
- filtered decks
- adding and editing notes
- the deck options screen

## Preconditions
Deck Spanish has 4 Basic notes: comer (tagged verb), mesa, hola and agua. Deck French has 3 Basic notes: bonjour, pain and chat. No other tags exist.

## Changed in this build
- Add note dismissal: the screen's edit-tracking snapshot is now rebuilt on each note model swap.
- Filtered deck builder: the criteria dropdown now lists every selection criterion the scheduler offers.
- Deck options New cards section: the daily limits are now stored on the deck's options preset.

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
