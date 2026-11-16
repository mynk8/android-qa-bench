# Test case Amaze File Manager-TC-0018
App: Amaze File Manager (already open on the device)

## Context
The Encrypt dialog asks for a password and a confirmation of it.

## Preconditions
Internal storage has a folder AndroidQA/Amaze containing: folder Alpha (with readme.txt), folder Beta (with its own readme.txt), files report+final.txt and notes.txt, and two photos, photo.jpg and keep.jpg. No bookmarks have been added.

## Steps
1. Open the AndroidQA/Amaze folder.
2. On the notes.txt row tap the three-dots button and choose Encrypt.
3. Type secret1 in the first password field only, leaving the confirmation field empty.
4. Look at the dialog.

## Expected results
- No error message is shown while the confirmation field is still empty.

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
