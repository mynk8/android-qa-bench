# Test case Tasks.org-TC-0018
App: Tasks.org (already open on the device)

## Context
The task list can be sorted by title.

## Preconditions
The list contains: Buy milk (due in 5 days, notes '2 litres'); Pack for trip (due in 10 days) with subtasks Charge phone and Print tickets; Pay rent (due in 20 days) repeating monthly; and Read docs (no due date), whose notes contain the link https://example.com/guide.

## Steps
1. Open Buy milk, change its title to Zucchini, and save.
2. Tap Sort. Under Grouping choose None. Under Sorting choose By title.
3. Look at the order of the tasks in the list.

## Expected results
- The tasks are listed alphabetically by title: Pack for trip, Pay rent, Read docs, Zucchini.

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
