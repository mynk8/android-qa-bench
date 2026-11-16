# Test case Amaze File Manager-TC-0014
App: Amaze File Manager (already open on the device)

## Context
Files can be renamed from the Images view in the navigation drawer.

## Preconditions
Internal storage has a folder AndroidQA/Amaze containing: folder Alpha (with readme.txt), folder Beta (with its own readme.txt), files report+final.txt and notes.txt, and two photos, photo.jpg and keep.jpg. No bookmarks have been added.

## Steps
1. Open the navigation drawer and choose Images.
2. Tap the three-dots button at the right end of the photo.jpg row.
3. Choose Rename.
4. Replace the name with photo-renamed.jpg and tap Save.
5. Look at the Images list.

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
