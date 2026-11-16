# Test case Minus-TC-0019
App: Minus (already open on the device)

## Context
The budget sheet on the main screen shows the amount you can spend per day, worked out from the budget, what was spent so far and the days left.

## Preconditions
The current budget period started 3 days ago and ends in 20 days, with a budget of 100.00 USD. Yesterday there was a one-off Groceries expense of 40.00 (Food) and a recurring monthly Rent expense of 20.00 (Food). Categories Food and Transport exist.

## Steps
1. On the main screen, tap the budget pill at the top to open the budget sheet.
2. Read the Calculated amount.

## Expected results
- The Calculated amount is 1.90 (the 100.00 budget minus 60.00 spent, spread over the 21 days left).

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
