# Test case Featherline-TC-0016
App: Featherline (already open on the device)

## Context
Body weight is entered on a sheet that opens from the Settings tab.

## Preconditions
Fresh install with no medications, plans or lab results.

## Steps
1. Open the Settings tab, scroll to Body weight and tap it.
2. Type 60 in the Weight field and tap Save.
3. Tap Body weight again, delete the value so the Weight field is empty, then tap Save.
4. Look at the Body weight row in Settings.

## Expected results
- The sheet closes and the Body weight row reads Not set.

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
