# QA sweep: AnkiDroid
The app is installed and open. A colleague asked you to sweep these areas before release:
- adding notes and previewing cards
- note types and their card templates
- the deck list

## Preconditions
Deck Spanish has 4 Basic notes: comer (tagged verb), mesa, hola and agua. Deck French has 3 Basic notes: bonjour, pain and chat. No other tags exist.

## Changed in this build
- Card preview from Add note: preview pages are now indexed directly by each card's template position.
- Card template editor toolbar: the menu's entries are now built the same way for every kind of note model.
- Deck list expand/collapse arrows: a tap is now handled by redrawing only the affected deck's rows.
- Manage note types: each type's note count is now computed in the background after the list appears.

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
