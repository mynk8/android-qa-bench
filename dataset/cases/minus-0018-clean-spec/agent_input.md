# Test case Minus-TC-0018
App: Minus (already open on the device)

## Context
The expense history groups expenses by day, and each day heading can be expanded or collapsed.

## Preconditions
The current budget period started 3 days ago and ends in 20 days, with a budget of 100.00 USD. Yesterday there was a one-off Groceries expense of 40.00 (Food) and a recurring monthly Rent expense of 20.00 (Food). Categories Food and Transport exist.

## Steps
1. Drag the main screen down to open the expense history.
2. Tap the arrow on the heading of the day that contains Groceries to collapse that day.
3. Look at the list under the heading.

## Expected results
- The Groceries row is hidden and the heading shows an Expand arrow.

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
