# Test case Amaze File Manager-TC-0015
App: Amaze File Manager (already open on the device)

## Context
The selection counter in the action bar has a Select All choice.

## Preconditions
Internal storage has a folder AndroidQA/Amaze containing: folder Alpha (with readme.txt), folder Beta (with its own readme.txt), files report+final.txt and notes.txt, and two photos, photo.jpg and keep.jpg. No bookmarks have been added.

## Steps
1. Open the AndroidQA/Amaze folder.
2. Long-press notes.txt.
3. Tap the selection counter (the number with a down arrow) at the top left and choose Select All.
4. Tap the selection counter again and choose Select All again.
5. Look at the top bar and the list.

## Expected results
- All six items remain selected and the counter still shows 6.

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
