# Test case AnkiDroid-TC-0025
App: AnkiDroid (already open on the device)

## Context
The filtered deck screen offers card orders; the orders that rely on FSRS are only offered when FSRS is enabled (it is off in this collection).

## Preconditions
Deck Spanish has 4 Basic notes: comer (tagged verb), mesa, hola and agua. Deck French has 3 Basic notes: bonjour, pain and chat. No other tags exist.

## Steps
1. In the deck list, tap the + button and choose Create filtered deck.
2. Open the Order dropdown of the first filter and read all the options.

## Expected results
- The options do not include Retrievability ascending or Retrievability descending.

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
