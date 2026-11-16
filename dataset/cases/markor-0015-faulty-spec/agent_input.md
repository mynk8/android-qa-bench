# Test case Markor-TC-0015
App: Markor (already open on the device)

## Context
The Unordered list action toggles the list marker of the line the cursor is on, including an indented line.

## Preconditions
The notebook folder contains Shopping.md, todo.txt, Notes.md, Single.md (one line, 'gamma', with no newline at the end), Regex.md (the line 'cat@home'), Regex2.md (the line 'cat@home dog@home') Money.md (the line 'Costs $5 and $10'), Indent.md ('- item' then '  - child'), Indent2.md ('- a' then '  - deep') and a folder Zeta.

## Steps
1. Open Indent.md in the editor.
2. Place the cursor on the line '  - child' and tap Unordered list.
3. Leave the editor and reopen Indent.md.

## Expected results
- The second line reads '  child' (two leading spaces, no list marker) and the first line is still '- item'.

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
