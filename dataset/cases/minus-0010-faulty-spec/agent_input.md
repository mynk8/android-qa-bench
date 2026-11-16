# Test case Minus-TC-0010
App: Minus (already open on the device)

## Context
Analytics totals count the recurring charges that fall in the current period.

## Preconditions
The current budget period started 3 days ago and ends in 20 days, with a budget of 100.00 USD. Yesterday there was a one-off Groceries expense of 40.00 (Food) and a recurring monthly Rent expense of 20.00 (Food). Categories Food and Transport exist.

## Steps
1. Drag the main screen down to open the expense history.
2. Scroll down and tap "Show subscriptions outside of the period", then swipe the Rent row to the left to edit it.
3. Tap the change date button and set it to one month earlier than the date it shows now (same day number, previous month), tap Accept, then tap the check on the numpad to save the expense.
4. Open Analytics and read the Spent card and the Total expenses card.

## Expected results
- Spent shows 60.00 and Total expenses shows 2.

## Rules
- Do not change or delete data unless a step tells you to.
- Report what you observed, not what you assume.

## Answer format
End with a JSON block:
{"verdict": "PASS|FAIL|INCONCLUSIVE", "confidence": 0.0-1.0,
 "evidence": [{"screen": "...", "element": "...", "observed": "..."}],
 "failure": {"screen": "...", "element": "...", "field": "...", "symptom_type": "...",
             "expected": "...", "observed": "..."}   <- only when FAIL
}
