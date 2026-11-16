# Test case Tasks.org-TC-0008
App: Tasks.org (already open on the device)

## Context
The task list can be grouped by due date and sorted descending.

## Preconditions
The list contains: Buy milk (due in 5 days, notes '2 litres'); Pack for trip (due in 10 days) with subtasks Charge phone and Print tickets; Pay rent (due in 20 days) repeating monthly; and Read docs (no due date), whose notes contain the link https://example.com/guide.

## Steps
1. Tap Sort. Under Grouping choose By due date, then set the grouping order to Descending.
2. Look at the section headers and the tasks under them, including Read docs (no due date) and Pay rent (due in 20 days).

## Expected results
- Tasks are grouped under due-date headers, newest first, so Pay rent appears above Buy milk.
- Pay rent has a header of its own and is not listed under the same header as Read docs.

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
