# Test case Markor-TC-0016
App: Markor (already open on the device)

## Context
Settings > Edit Mode > Unordered list character sets the marker that the editor's Unordered list action uses.

## Preconditions
The notebook folder contains Shopping.md, todo.txt, Notes.md, Single.md (one line, 'gamma', with no newline at the end), Regex.md (the line 'cat@home'), Regex2.md (the line 'cat@home dog@home') Money.md (the line 'Costs $5 and $10'), Indent.md ('- item' then '  - child'), Indent2.md ('- a' then '  - deep') and a folder Zeta.

## Steps
1. Open the More tab, then Settings, then Edit Mode, and set Unordered list character to Asterisk (*).
2. Go back to the Files tab and open Single.md in the editor.
3. Place the cursor on the line gamma and tap Unordered list.
4. Leave the editor and reopen Single.md.

## Expected results
- Single.md reads '* gamma'.

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
