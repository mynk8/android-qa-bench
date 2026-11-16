# Test case Featherline-TC-0003
App: Featherline (already open on the device)

## Context
The Home tab shows an Antiandrogen card for antiandrogen medicines that are in a medication group.

## Preconditions
Fresh install with no medications, plans or lab results.

## Steps
1. Open the Plan tab, scroll down and tap Add to create a group. Under Medications tap Add, then tap Add medicine.
2. In the Add medicine sheet choose the category Antiandrogen and the preparation form Tablet, enter 25 as the Tablet strength, keep 1 Tablets per dose, and tap Save.
3. Keep the Daily schedule, the start Now and the default time. Tap Save at the top.
4. Open the Home tab and read the Due line on the Antiandrogen card.
5. Log that dose with the Quick log button on its row on Home, then read the Antiandrogen card again.

## Expected results
- After the dose is logged, the Antiandrogen card shows the last dose and its Due line refers to the next scheduled dose (tomorrow).

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
