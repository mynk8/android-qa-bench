# Test case Markor-TC-0010
App: Markor (already open on the device)

## Context
With regex enabled, a replacement such as $1 inserts the captured group.

## Preconditions
The notebook folder contains Shopping.md, todo.txt, Notes.md, Single.md (one line, 'gamma', with no newline at the end), Regex.md (the line 'cat@home'), Regex2.md (the line 'cat@home dog@home') Money.md (the line 'Costs $5 and $10'), Indent.md ('- item' then '  - child'), Indent2.md ('- a' then '  - deep') and a folder Zeta.

## Steps
1. Open Regex.md.
2. Tap Search in the toolbar, tap Toggle Find/Replace to show the replace field, and turn on Use Regular Expression.
3. Search (\w+)@home, replace with $1, tap Replace (1) once.
4. Leave the editor.

## Expected results
- Regex.md now reads cat.

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
