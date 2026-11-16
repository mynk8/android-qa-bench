# Test case AnkiDroid-TC-0001
App: AnkiDroid (already open on the device)

## Context
Editing tags for several notes at once keeps tags that only some of the notes have.

## Preconditions
Deck Spanish has 4 Basic notes: comer (tagged verb), mesa, hola and agua. Deck French has 3 Basic notes: bonjour, pain and chat. No other tags exist.

## Steps
1. Open the card browser (navigation drawer) on deck Spanish.
2. Select the notes comer and mesa (long-press one, then tap the other).
3. Open Edit tags and press Confirm without changing anything.
4. Check the tags of mesa.

## Expected results
- comer is still tagged verb and mesa is still untagged.

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
