# Test case Tasks.org-TC-0019
App: Tasks.org (already open on the device)

## Context
On the Sort sheet, the Subtasks row is set to My order.

## Preconditions
The list contains: Buy milk (due in 5 days, notes '2 litres'); Pack for trip (due in 10 days) with subtasks Charge phone and Print tickets; Pay rent (due in 20 days) repeating monthly; and Read docs (no due date), whose notes contain the link https://example.com/guide.

## Steps
1. Tap Sort.
2. Look at the Subtasks row and at the Grouping, Sorting and Completed rows.

## Expected results
- The Subtasks row, set to My order, has no Ascending or Descending button.
- The Grouping and Sorting rows each have one.

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
