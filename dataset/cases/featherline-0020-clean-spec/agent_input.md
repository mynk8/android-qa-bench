# Test case Featherline-TC-0020
App: Featherline (already open on the device)

## Context
A medication card in a group shows the route, the strength and the dose for each medication.

## Preconditions
Fresh install with no medications, plans or lab results.

## Steps
1. Open the Plan tab, scroll down and tap Add to create a group. Under Medications tap Add, then tap Add medicine.
2. In the Add medicine sheet choose the category Custom, enter Custom A as the Medication name and 2 as the Tablet strength, then tap Save.
3. Look at the supporting line under Custom A on its card under Medications.

## Expected results
- The supporting line starts with Custom, followed by the dose details.

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
