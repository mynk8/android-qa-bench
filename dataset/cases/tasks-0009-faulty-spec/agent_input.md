# Test case Tasks.org-TC-0009
App: Tasks.org (already open on the device)

## Context
Pressing back while a search is active leaves the search.

## Preconditions
The list contains: Buy milk (due in 5 days, notes '2 litres'); Pack for trip (due in 10 days) with subtasks Charge phone and Print tickets; Pay rent (due in 20 days) repeating monthly; and Read docs (no due date), whose notes contain the link https://example.com/guide.

## Steps
1. Tap Search, type milk and submit the search with the keyboard's search key.
2. Press back once. If the on-screen keyboard is still showing, press back once more; stop as soon as the search is cleared or the app has closed.

## Expected results
- The search is cleared and the full task list, including Pay rent, is shown.

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
