# Test case AnkiDroid-TC-0027
App: AnkiDroid (already open on the device)

## Context
A deck's long-press menu in the deck list has Rename deck.

## Preconditions
Deck Spanish has 4 Basic notes: comer (tagged verb), mesa, hola and agua. Deck French has 3 Basic notes: bonjour, pain and chat. No other tags exist.

## Steps
1. In the deck list, long-press deck French and choose Rename deck.
2. Replace the name with FRENCH (capital letters) and tap Rename.
3. Look at the deck list.

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
