# Test case AnkiDroid-TC-0008
App: AnkiDroid (already open on the device)

## Context
The card browser keeps separate sort orders for cards mode and notes mode.

## Preconditions
Deck Spanish has 4 Basic notes: comer (tagged verb), mesa, hola and agua. Deck French has 3 Basic notes: bonjour, pain and chat. No other tags exist.

## Steps
1. Open the card browser (navigation drawer), open the overflow menu, choose Options and select Notes.
2. Open the overflow menu, choose Change display order and pick a column other than Sort field (for example Created).
3. Choose Options, select Cards, then Options again and select Notes.
4. Open Change display order and look at which column is selected.

## Expected results
- In notes mode the column chosen in step 2 is still the selected display order.

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
