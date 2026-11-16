# QA sweep: Minus
The app is installed and open. A colleague asked you to sweep these areas before release:
- entering expenses on the main screen
- the expense history
- the budget sheet
- managing categories

## Preconditions
The current budget period started 3 days ago and ends in 20 days, with a budget of 100.00 USD. Yesterday there was a one-off Groceries expense of 40.00 (Food) and a recurring monthly Rent expense of 20.00 (Food). Categories Food and Transport exist.

## Changed in this build
- Category management screen: categories are now loaded from the local database on open.
- Main screen number pad: key input is now handled by a different keypad component from the history editor's.
- Budget sheet summary rows: recurring templates are now included in the entries the summary is built from.
- Expense history per-date sections: an empty open-sections set is now handled the same as a first visit.

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
