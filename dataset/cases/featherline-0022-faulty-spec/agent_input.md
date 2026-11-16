# Test case Featherline-TC-0022
App: Featherline (already open on the device)

## Context
The Body weight sheet in Settings has a Clear button that asks for confirmation.

## Preconditions
Fresh install with no medications, plans or lab results.

## Steps
1. Open the Settings tab, scroll to Body weight and tap it.
2. Type 60 in the Weight field and tap Save.
3. Tap Body weight again and tap Clear.
4. Read the title and the text of the dialog.

## Expected results
- The dialog is titled Clear body weight and its text reads Clear your body weight? Estimates will stop using it.

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
