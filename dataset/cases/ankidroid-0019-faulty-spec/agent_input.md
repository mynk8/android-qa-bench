# Test case AnkiDroid-TC-0019
App: AnkiDroid (already open on the device)

## Context
Opening the browser from a deck's long-press menu shows that deck.

## Preconditions
Deck Spanish has 4 Basic notes: comer (tagged verb), mesa, hola and agua. Deck French has 3 Basic notes: bonjour, pain and chat. No other tags exist.

## Steps
1. Tap deck French in the deck list, then go back. Open the card browser from the navigation drawer, then go back.
2. Long-press deck Spanish and choose Browse cards.

## Expected results
- The browser shows deck Spanish (comer, mesa, hola, agua).

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
