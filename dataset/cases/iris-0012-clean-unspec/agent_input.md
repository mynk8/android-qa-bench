# Test case Iris Gallery-TC-0012
App: Iris Gallery (already open on the device)

## Context
When the Media tab filter matches nothing, the screen shows a message saying what was not found.

## Preconditions
The gallery has an album IrisSeed with two photos: big.jpg (exactly 1,500,000 bytes) and huge.jpg (exactly 2,500,000 bytes).

## Steps
1. On the Media tab, tap the Filter button at the top and choose Videos.
2. Read the message shown in the middle of the screen.

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
