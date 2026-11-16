# Test case AnkiDroid-TC-0007
App: AnkiDroid (already open on the device)

## Context
The note editor's deck spinner remembers the last deck used for a new note.

## Preconditions
Deck Spanish has 4 Basic notes: comer (tagged verb), mesa, hola and agua. Deck French has 3 Basic notes: bonjour, pain and chat. No other tags exist.

## Steps
1. Open Settings > General and set Deck for new cards to Decide by note type, then return to the deck list.
2. Add a new Basic note, set the deck to French, fill Front with merci and save.
3. Open Add note again and look at the selected deck.

## Expected results
- The selected deck is French.

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
