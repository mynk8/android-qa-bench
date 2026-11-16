# Test case AnkiDroid-TC-0021
App: AnkiDroid (already open on the device)

## Context
Creating a subdeck from a deck's long-press menu needs a usable name.

## Preconditions
Deck Spanish has 4 Basic notes: comer (tagged verb), mesa, hola and agua. Deck French has 3 Basic notes: bonjour, pain and chat. No other tags exist.

## Steps
1. In the deck list, long-press deck Spanish and choose Create subdeck.
2. Type three spaces as the name and tap Create (if it can be tapped).
3. Look at the deck list.

## Expected results
- No subdeck is created: Spanish has no expand/collapse arrow and no new deck appears.

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
