# Test case Featherline-TC-0005
App: Featherline (already open on the device)

## Context
The Add medicine sheet lets you pick a preparation form (Tablet, Injection, Gel, Patch) and enter dose values for it.

## Preconditions
Fresh install with no medications, plans or lab results.

## Steps
1. Open the Plan tab, tap the Medicines icon at the top, then tap Add medicine.
2. Keep the category Estradiol, choose the preparation form Tablet, and type 100 in Tablet strength.
3. Choose the preparation form Patch, then choose Tablet again.
4. Look at the Tablet strength field.

## Expected results
- The Tablet strength field is empty; 100 is not shown.

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
