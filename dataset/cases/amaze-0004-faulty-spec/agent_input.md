# Test case Amaze File Manager-TC-0004
App: Amaze File Manager (already open on the device)

## Context
Pasting a folder into the folder it came from, and choosing Rename, creates a numbered copy.

## Preconditions
Internal storage has a folder AndroidQA/Amaze containing: folder Alpha (with readme.txt), folder Beta (with its own readme.txt), files report+final.txt and notes.txt, and two photos, photo.jpg and keep.jpg. No bookmarks have been added.

## Steps
1. Open the AndroidQA/Amaze folder.
2. Copy the folder Alpha.
3. Paste it into the same folder.
4. When asked about the name conflict, choose Rename.

## Expected results
- A folder Alpha (1) appears next to Alpha and contains readme.txt.

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
