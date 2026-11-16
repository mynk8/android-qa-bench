# Test case Tasks.org-TC-0003
App: Tasks.org (already open on the device)

## Context
Completing a repeating task schedules its next occurrence according to the repeat rule.

## Preconditions
The list contains one task, Water plants, due in 30 days at 10:00 and set to repeat every hour.

## Steps
1. Note the due date and time of Water plants.
2. Tick the checkbox to complete Water plants.
3. Look at Water plants' new due date and time.

## Expected results
- Water plants is still in the list and is now due exactly one hour later than before.

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
