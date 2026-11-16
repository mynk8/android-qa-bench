# Test case Amaze File Manager-TC-0011
App: Amaze File Manager (already open on the device)

## Context
Bookmarks must have a name and a path, and two bookmarks cannot point at the same path.

## Preconditions
Internal storage has a folder AndroidQA/Amaze containing: folder Alpha (with readme.txt), folder Beta (with its own readme.txt), files report+final.txt and notes.txt, and two photos, photo.jpg and keep.jpg. No bookmarks have been added.

## Steps
1. Open the navigation drawer, then Settings > Interface > Bookmarks.
2. Tap Add Item and create bookmark Docs with directory /storage/emulated/0/AndroidQA/Amaze/Alpha.
3. Tap Add Item again and create bookmark Docs2 with the same directory.

## Expected results
- Docs2 is not added (an error message is shown); the bookmark list shows only Docs.

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
