# Test case Featherline-TC-0011
App: Featherline (already open on the device)

## Context
A medicine can have its on-hand stock tracked, and a group can start with a schedule that begins in the past.

## Preconditions
Fresh install with no medications, plans or lab results.

## Steps
1. Open the Plan tab, tap the Medicines icon at the top, then tap Add medicine. Keep the category Estradiol and the form Tablet, enter 2 as the Tablet strength, and tap Save.
2. On the Medicine details page, under Stock tracking tap Enable stock tracking, add 10 tablets and confirm. Check that Stock reads 10 tablets, then go back to the Plan tab.
3. On the Plan tab scroll down and tap Add to create a group. Under Medications tap Add, pick that medicine, keep the dose and save it.
4. Set the group's Start date to three days ago. In the Past schedule card choose Mark as completed, then tap Save at the top.
5. Open Plan, tap the Medicines icon, open the medicine and read the Stock row.

## Expected results
- Stock still reads 10 tablets.

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
