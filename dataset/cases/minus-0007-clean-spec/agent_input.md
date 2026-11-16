# Test case Minus-TC-0007
App: Minus (already open on the device)

## Context
The budget sheet on the main screen offers Daily, Weekly and Biweekly views of how the budget is split.

## Preconditions
The current budget period started 3 days ago and ends in 20 days, with a budget of 100.00 USD. Yesterday there was a one-off Groceries expense of 40.00 (Food) and a recurring monthly Rent expense of 20.00 (Food). Categories Food and Transport exist.

## Steps
1. On the main screen, tap the budget pill at the top to open the budget sheet.
2. Under "How do you want to split the budget?", choose Weekly.
3. Close the app completely and open it again.
4. Tap the budget pill again and note which option is selected under "How do you want to split the budget?".

## Expected results
- Weekly is still the selected option after the app is opened again.

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
