# Test case Iris Gallery-TC-0011
App: Iris Gallery (already open on the device)

## Context
The Media tab has a Filter button that limits the grid to all media, photos only or videos only, and the bottom navigation label follows the filter.

## Preconditions
The gallery has an album IrisSeed with two photos: big.jpg (exactly 1,500,000 bytes) and huge.jpg (exactly 2,500,000 bytes).

## Steps
1. On the Media tab, tap the Filter button at the top and choose Photos.
2. Note the label of the first item in the bottom navigation bar.
3. Close the app completely and open it again.
4. Note the label of the first item in the bottom navigation bar again.

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
