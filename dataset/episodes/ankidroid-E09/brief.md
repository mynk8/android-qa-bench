# QA sweep: AnkiDroid
The app is installed and open. A colleague asked you to sweep these areas before release:
- deck management
- browsing and editing cards
- managing note types

## Preconditions
Deck Spanish has 4 Basic notes: comer (tagged verb), mesa, hola and agua. Deck French has 3 Basic notes: bonjour, pain and chat. No other tags exist.

## Changed in this build
- Card browser new-card ordering popup: the range hint above the inputs is now generated from translated strings.
- Deck retitling dialog: the clash check with other decks is now computed by comparing text instead of identifiers.
- Deck list expand/collapse arrows: each arrow's touch target is now separated from the rest of the deck row.
- Note type field editor: field positions are now stored right after each reorder.

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
