# Test case AnkiDroid-TC-0014
App: AnkiDroid (already open on the device)

## Context
The deck list shows an arrow next to a deck that has subdecks.

## Preconditions
Deck Spanish has 4 Basic notes: comer (tagged verb), mesa, hola and agua. Deck French has 3 Basic notes: bonjour, pain and chat. No other tags exist.

## Steps
1. In the deck list, long-press deck Spanish, choose Create subdeck and create a subdeck named Verbs.
2. Note the arrow shown next to Spanish, tap it, and look at the arrow again.

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
