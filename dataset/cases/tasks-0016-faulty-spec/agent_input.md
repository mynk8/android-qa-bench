# Test case Tasks.org-TC-0016
App: Tasks.org (already open on the device)

## Context
The subtask chip on a list row shows how many subtasks are still to do.

## Preconditions
The list contains: Buy milk (due in 5 days, notes '2 litres'); Pack for trip (due in 10 days) with subtasks Charge phone and Print tickets; Pay rent (due in 20 days) repeating monthly; and Read docs (no due date), whose notes contain the link https://example.com/guide.

## Steps
1. In the task list, tap the checkbox next to Charge phone (a subtask of Pack for trip) to mark it complete.
2. Look at the subtask chip on the Pack for trip row.

## Expected results
- The Pack for trip chip shows 1, the number of subtasks still to do.

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
