# Test case Markor-TC-0011
App: Markor (already open on the device)

## Context
Pressing Enter inside a line's leading indentation does not duplicate that indentation.

## Preconditions
The notebook folder contains Shopping.md, todo.txt, Notes.md, Single.md (one line, 'gamma', with no newline at the end), Regex.md (the line 'cat@home'), Regex2.md (the line 'cat@home dog@home') Money.md (the line 'Costs $5 and $10'), Indent.md ('- item' then '  - child'), Indent2.md ('- a' then '  - deep') and a folder Zeta.

## Steps
1. Open Indent.md.
2. Put the cursor at the very start of the line '  - child', before its two leading spaces (tapping the line and pressing the Home key moves the cursor there), and press Enter.
3. Leave the editor and reopen Indent.md.

## Expected results
- The '  - child' line is still indented by exactly two spaces, the same as before step 2 (its '-' lines up two characters to the right of the '-' on the line '- item').

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
