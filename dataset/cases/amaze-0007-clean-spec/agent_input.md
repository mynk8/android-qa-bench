# Test case Amaze File Manager-TC-0007
App: Amaze File Manager (already open on the device)

## Context
Pasting a file into a folder that already has a file with that name, and choosing Rename, picks the next free number in the destination.

## Preconditions
Internal storage has a folder AndroidQA/Amaze containing: folder Alpha (with readme.txt), folder Beta (with its own readme.txt), files report+final.txt and notes.txt, and two photos, photo.jpg and keep.jpg. No bookmarks have been added.

## Steps
1. Open AndroidQA/Amaze/Alpha and copy readme.txt.
2. Open AndroidQA/Amaze/Beta and paste, choosing Rename.
3. Copy Alpha/readme.txt again and paste it into Beta again, choosing Rename.

## Expected results
- Beta contains readme.txt, readme (1).txt and readme (2).txt.

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
