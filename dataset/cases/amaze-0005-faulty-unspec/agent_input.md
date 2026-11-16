# Test case Amaze File Manager-TC-0005
App: Amaze File Manager (already open on the device)

## Context
A renamed folder copy should mirror the original folder exactly.

## Preconditions
Internal storage has a folder AndroidQA/Amaze containing: folder Alpha (with readme.txt), folder Beta (with its own readme.txt), files report+final.txt and notes.txt, and two photos, photo.jpg and keep.jpg. No bookmarks have been added.

## Steps
1. Open the AndroidQA/Amaze folder.
2. Copy the folder Alpha and paste it into the same folder, choosing Rename.
3. Open the new copy of Alpha.

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
