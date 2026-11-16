# Test case Minus-TC-0014
App: Minus (already open on the device)

## Context
An expense can be entered on the main screen with an amount and a category tag.

## Preconditions
The current budget period started 3 days ago and ends in 20 days, with a budget of 100.00 USD. Yesterday there was a one-off Groceries expense of 40.00 (Food) and a recurring monthly Rent expense of 20.00 (Food). Categories Food and Transport exist.

## Steps
1. On the main screen, type 12 on the keypad.
2. Tap the Category tag and type Snacks.
3. Tap the check mark in the tag editor.
4. Drag the main screen down to open the expense history and look for a Snacks expense.

## Expected results
- No 12.00 Snacks expense exists in the history yet; it is saved only when the check on the numpad is pressed.

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
