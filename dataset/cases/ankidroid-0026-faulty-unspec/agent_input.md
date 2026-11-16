# Test case AnkiDroid-TC-0026
App: AnkiDroid (already open on the device)

## Context
The Add note screen has a Front field and a note type spinner.

## Preconditions
Deck Spanish has 4 Basic notes: comer (tagged verb), mesa, hola and agua. Deck French has 3 Basic notes: bonjour, pain and chat. No other tags exist.

## Steps
1. In the deck list, tap the + button and choose Add note.
2. Type merci in the Front field.
3. Change the note type to Basic (and reversed card).
4. Press back (twice if the keyboard is open) and look at what happens.

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
