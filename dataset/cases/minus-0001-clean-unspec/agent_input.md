# Test case Minus-TC-0001
App: Minus (already open on the device)

## Context
Recurring payments appear in the expense history, including those due after the current period. Their rows can be swiped.

## Preconditions
The current budget period started 3 days ago and ends in 20 days, with a budget of 100.00 USD. Yesterday there was a one-off Groceries expense of 40.00 (Food) and a recurring monthly Rent expense of 20.00 (Food). Categories Food and Transport exist.

## Steps
1. Drag the main screen down to open the expense history.
2. Scroll down and tap "Show subscriptions outside of the period" to expand that section.
3. Swipe the Rent row in that section to the right.
4. Note what appears. If a dialog opens, choose Cancel.

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
