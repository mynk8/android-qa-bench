# Test case Markor-TC-0019
App: Markor (already open on the device)

## Context
The indent size chosen by long-pressing Indent in the editor is remembered for that file.

## Preconditions
The notebook folder contains Shopping.md, todo.txt, Notes.md, Single.md (one line, 'gamma', with no newline at the end), Regex.md (the line 'cat@home'), Regex2.md (the line 'cat@home dog@home') Money.md (the line 'Costs $5 and $10'), Indent.md ('- item' then '  - child'), Indent2.md ('- a' then '  - deep') and a folder Zeta.

## Steps
1. Open Single.md in the editor, long-press Indent and choose 2.
2. Place the cursor on the line gamma and tap Indent once.
3. Leave the editor, open Single.md again, and tap Indent once more.
4. Leave the editor.

## Expected results
- Single.md reads '    gamma' with exactly four leading spaces.

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
