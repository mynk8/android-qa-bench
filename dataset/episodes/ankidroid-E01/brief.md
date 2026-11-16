# QA sweep: AnkiDroid
The app is installed and open. A colleague asked you to sweep these areas before release:
- the deck list and card browser
- tags

## Preconditions
Deck Spanish has 4 Basic notes: comer (tagged verb), mesa, hola and agua. Deck French has 3 Basic notes: bonjour, pain and chat. No other tags exist.

## Changed in this build
- Deck list expand/collapse arrows: the collapsed state of each parent deck is now stored in the collection.
- Card browser deck dropdown: its starting deck is now loaded from browser state ahead of the launching screen's request.
- Deck list toolbar: deck search results are now computed as each character is typed.
- Card browser tag dialog: each tag's checkbox state is now computed from the union of the chosen rows' tags.

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
