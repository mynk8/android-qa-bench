# Test case AnkiDroid-TC-0006
App: AnkiDroid (already open on the device)

## Context
A Cloze note can skip a number, for example cloze 1 and cloze 3 with no cloze 2.

## Preconditions
Deck Spanish has 4 Basic notes: comer (tagged verb), mesa, hola and agua. Deck French has 3 Basic notes: bonjour, pain and chat. No other tags exist.

## Steps
1. Open Add note and choose the note type Cloze.
2. In the Text field enter {{c1::alpha}} and {{c3::gamma}} (cloze 1 and cloze 3 only, no cloze 2).
3. Open Preview and look at the tabs, then open each tab.

## Expected results
- The preview has two tabs, one for cloze 1 and one for cloze 3.
- The cloze 1 tab hides alpha and the cloze 3 tab hides gamma.

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
