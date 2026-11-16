# Test case AnkiDroid-TC-0023
App: AnkiDroid (already open on the device)

## Context
The timebox screen remembers the limit that was last set while the timebox is switched off.

## Preconditions
Deck Spanish has 4 Basic notes: comer (tagged verb), mesa, hola and agua. Deck French has 3 Basic notes: bonjour, pain and chat. No other tags exist.

## Steps
1. Open the navigation drawer, then Settings, Reviewing and Timebox time limit.
2. Switch Use timebox on, tap + once to raise the limit, then switch Use timebox off.
3. Go back to Reviewing, open Timebox time limit again and switch Use timebox on. Look at the time limit.

## Expected results
- The time limit shows 21 mins, the value it had before the timebox was switched off.

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
