# Test case AnkiDroid-TC-0029
App: AnkiDroid (already open on the device)

## Context
The reposition dialog for new cards shows the first and the last position of the new-card queue.

## Preconditions
Deck Spanish has 4 Basic notes: comer (tagged verb), mesa, hola and agua. Deck French has 3 Basic notes: bonjour, pain and chat. No other tags exist.

## Steps
1. Open the card browser from the navigation drawer.
2. Long-press a card to select it.
3. Open the overflow menu and choose Reposition.
4. Read the two lines above the Start position input.

## Expected results
- The two lines are labelled Queue top and Queue bottom.

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
