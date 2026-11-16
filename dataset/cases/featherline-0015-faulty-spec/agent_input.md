# Test case Featherline-TC-0015
App: Featherline (already open on the device)

## Context
A medication card in a group shows a dose summary for each medication.

## Preconditions
Fresh install with no medications, plans or lab results.

## Steps
1. Open the Plan tab, scroll down and tap Add to create a group. Under Medications tap Add, then tap Add medicine.
2. In the Add medicine sheet keep the category Estradiol and the form Tablet, enter Estradiol A as the Display name, 2 as the Tablet strength and 1 as Tablets per dose, then tap Save.
3. Look at the dose summary on the Estradiol A card under Medications.

## Expected results
- The summary shows the strength (2 mg) without a separate "1 tablet" part.

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
