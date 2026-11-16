# Test case Minus-TC-0009
App: Minus (already open on the device)

## Context
Analytics has a savings recommendation card that lists recurring and one-time expenses for the current period.

## Preconditions
The current budget period started 3 days ago and ends in 20 days, with a budget of 100.00 USD. Yesterday there was a one-off Groceries expense of 40.00 (Food) and a recurring monthly Rent expense of 20.00 (Food). Categories Food and Transport exist.

## Steps
1. Drag the main screen down to open the expense history.
2. Scroll down and tap "Show subscriptions outside of the period", then swipe the Rent row to the left to edit it.
3. Tap the recurrent expense toggle, choose Weekly, tap Save, then tap the check on the numpad to save the expense.
4. Open Analytics and read the Recurring expenses amount on the Savings recommendation card.

## Expected results
- Recurring expenses shows 40.00: the Rent charge from yesterday plus the next weekly Rent charge due within the period.

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
