# Test case Tasks.org-TC-0017
App: Tasks.org (already open on the device)

## Context
The task list can be grouped by start date, in ascending or descending order.

## Preconditions
The list contains: Buy milk (due in 5 days, notes '2 litres'); Pack for trip (due in 10 days) with subtasks Charge phone and Print tickets; Pay rent (due in 20 days) repeating monthly; and Read docs (no due date), whose notes contain the link https://example.com/guide.

## Steps
1. Open Buy milk, set its start date to today (date only, no time), and save.
2. Tap Sort. Under Grouping choose By start date, then set the grouping order to Descending.
3. Look at the section headers and the tasks under them, including Buy milk.

## Expected results
- Buy milk has a header of its own that starts with 'Start'.
- Buy milk is not listed under the 'No start date' header.

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
