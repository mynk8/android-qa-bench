# Test case Minus-TC-0017
App: Minus (already open on the device)

## Context
The amount editor on the main screen lets you type simple arithmetic on the numpad and shows the calculated result.

## Preconditions
The current budget period started 3 days ago and ends in 20 days, with a budget of 100.00 USD. Yesterday there was a one-off Groceries expense of 40.00 (Food) and a recurring monthly Rent expense of 20.00 (Food). Categories Food and Transport exist.

## Steps
1. On the main screen, swipe up on the numpad to reveal the operator row.
2. Tap 2, +, 3, ×, 4 in that order.
3. Read the result line shown under the typed expression.

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
