# Test case Tasks.org-TC-0005
App: Tasks.org (already open on the device)

## Context
A repeating task whose last occurrence is completed should end instead of repeating again.

## Preconditions
The list contains one task, Final dose, due in 30 days. It repeats daily but only for 1 occurrence in total, so this is its last occurrence.

## Steps
1. Tick the checkbox to complete Final dose.
2. Look at the task list.

## Expected results
- Final dose is completed and no longer shown among active tasks.

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
