# Test case Minus-TC-0008
App: Minus (already open on the device)

## Context
An existing expense can be edited from the expense history, including its category.

## Preconditions
The current budget period started 3 days ago and ends in 20 days, with a budget of 100.00 USD. Yesterday there was a one-off Groceries expense of 40.00 (Food) and a recurring monthly Rent expense of 20.00 (Food). Categories Food and Transport exist.

## Steps
1. Drag the main screen down to open the expense history.
2. Swipe the Groceries expense to the left to edit it.
3. Change its category tag to Transport (type it or pick the saved tag), then tap the check on the numpad to save.
4. Open Analytics and read the category shown on the Maximum spent card.

## Expected results
- The Maximum spent card (40.00) shows the category Transport.

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
