# Test case Featherline-TC-0019
App: Featherline (already open on the device)

## Context
A new group starts Now. The Start date row in the Schedule section opens a date picker.

## Preconditions
Fresh install with no medications, plans or lab results.

## Steps
1. Open the Plan tab, scroll down and tap Add to create a group.
2. In the Schedule section note the value of the Start time row.
3. Tap the Start date row and tap Confirm in the date picker without changing the date.
4. Look at the Start time row again.

## Expected results
- The Start time row no longer reads Now; it shows the time at which the day begins.

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
