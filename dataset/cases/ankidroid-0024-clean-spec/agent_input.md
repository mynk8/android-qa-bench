# Test case AnkiDroid-TC-0024
App: AnkiDroid (already open on the device)

## Context
The card browser's subtitle shows how many cards are listed.

## Preconditions
Deck Spanish has 4 Basic notes: comer (tagged verb), mesa, hola and agua. Deck French has 3 Basic notes: bonjour, pain and chat. No other tags exist.

## Steps
1. Open the card browser from the navigation drawer and read the subtitle under the title.
2. Rotate the device to landscape.
3. Look at the subtitle again.

## Expected results
- The subtitle still shows the count (for example 0 cards shown), as before the rotation.

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
