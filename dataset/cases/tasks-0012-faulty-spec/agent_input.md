# Test case Tasks.org-TC-0012
App: Tasks.org (already open on the device)

## Context
When a task's start date equals its due date, only the due chip is shown.

## Preconditions
The list contains: Buy milk (due in 5 days, notes '2 litres'); Pack for trip (due in 10 days) with subtasks Charge phone and Print tickets; Pay rent (due in 20 days) repeating monthly; and Read docs (no due date), whose notes contain the link https://example.com/guide.

## Steps
1. Open Buy milk and set a due time of 3:00 PM on its due date.
2. Set its start date to Due time, so it matches the due date and time.
3. Save and look at Buy milk's row in the list.

## Expected results
- Buy milk's row shows its date once.

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
