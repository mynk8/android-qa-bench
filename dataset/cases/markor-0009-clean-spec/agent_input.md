# Test case Markor-TC-0009
App: Markor (already open on the device)

## Context
A file's favourite state can be changed from its details dialog and from the file browser toolbar, and the Favourites list in the file browser shows the favourites.

## Preconditions
The notebook folder contains Shopping.md, todo.txt, Notes.md, Single.md (one line, 'gamma', with no newline at the end), Regex.md (the line 'cat@home'), Regex2.md (the line 'cat@home dog@home') Money.md (the line 'Costs $5 and $10'), Indent.md ('- item' then '  - child'), Indent2.md ('- a' then '  - deep') and a folder Zeta.

## Steps
1. In the notebook file browser, select Notes.md, tap Details, and tick Favourite.
2. Close the dialog with OK. Notes.md is still selected: tap the star (Favourite) action in the toolbar.
3. Clear the selection, tap Go to in the toolbar, and open Favourites.

## Expected results
- Notes.md was already a favourite after step 1, so the star action in step 2 removes it: Notes.md is not listed under Favourites.

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
