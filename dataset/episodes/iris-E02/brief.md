# QA sweep: Iris Gallery
The app is installed and open. A colleague asked you to sweep these areas before release:
- the media tab
- album browsing
- favorites

## Preconditions
The gallery has an album IrisSeed with two photos: big.jpg (exactly 1,500,000 bytes) and huge.jpg (exactly 2,500,000 bytes).

## Changed in this build
- Album grid header: the item count is now computed once when the album finishes loading.
- Favorites grid: favorites are now queried through the same data source as the Media tab.
- Media tab content-type chips: the chosen chip is now tracked by the screen rather than in the app's settings.

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
