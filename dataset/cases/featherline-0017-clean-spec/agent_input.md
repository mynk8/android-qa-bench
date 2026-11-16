# Test case Featherline-TC-0017
App: Featherline (already open on the device)

## Context
Leaving a group editor with unsaved edits asks whether to discard them.

## Preconditions
Fresh install with no medications, plans or lab results.

## Steps
1. Open the Plan tab, scroll down and tap Add to create a group.
2. In the Schedule section choose Weekly instead of Daily.
3. Press the system Back button.
4. Read the dialog that appears.

## Expected results
- The dialog is titled Discard changes, asks Discard your unsaved changes? and offers the buttons Cancel and Discard.

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
