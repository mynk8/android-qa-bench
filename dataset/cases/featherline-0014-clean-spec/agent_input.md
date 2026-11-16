# Test case Featherline-TC-0014
App: Featherline (already open on the device)

## Context
A new medicine is created from the Medicines screen by choosing a category and a preparation form.

## Preconditions
Fresh install with no medications, plans or lab results.

## Steps
1. Open the Plan tab, tap the Medicines icon at the top, then tap Add medicine.
2. In the Add medicine sheet keep the category Estradiol and choose the preparation form Gel.
3. Look at the fields below the preparation form.

## Expected results
- A Preparation type choice (Container, Sachet) is shown with Container selected, together with the gel fields Gel concentration (%) and Total amount gel (g).

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
