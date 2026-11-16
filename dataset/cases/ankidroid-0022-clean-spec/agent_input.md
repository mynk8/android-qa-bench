# Test case AnkiDroid-TC-0022
App: AnkiDroid (already open on the device)

## Context
The note type chosen on the Add note screen is only remembered once a note has been saved with it.

## Preconditions
Deck Spanish has 4 Basic notes: comer (tagged verb), mesa, hola and agua. Deck French has 3 Basic notes: bonjour, pain and chat. No other tags exist.

## Steps
1. In the deck list, tap the + button and choose Add note.
2. Change the note type to Cloze, then go back (repeat until the deck list is shown) without saving a note.
3. Tap the + button and choose Add note again, and look at the selected note type.

## Expected results
- The note type is Basic, as before; the Cloze choice was not kept because no note was saved.

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
