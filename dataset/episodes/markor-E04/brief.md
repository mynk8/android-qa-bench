# QA sweep: Markor
The app is installed and open. A colleague asked you to sweep these areas before release:
- the editor's formatting toolbar
- file preview and view mode

## Preconditions
The notebook folder contains Shopping.md, todo.txt, Notes.md, Single.md (one line, 'gamma', with no newline at the end), Regex.md (the line 'cat@home'), Regex2.md (the line 'cat@home dog@home') Money.md (the line 'Costs $5 and $10'), Indent.md ('- item' then '  - child'), Indent2.md ('- a' then '  - deep') and a folder Zeta.

## Changed in this build
- File preview styling: code blocks are now rendered with a monospace font and a shaded background.
- Strong-emphasis hold gesture: the affected lines are now computed from the start and end of the selection range.
- Formatting toolbar enumeration button: it now uses the same insertion logic as the neighbouring toolbar buttons.
- Editor tab width dialog: the chosen width is now applied directly to the editor that is open.

## How this works
- Test the app through its screen.
- When you find a bug, file a report (format below). A developer will reply.
- If the developer accepts the report, they ship a new build and tell you. Re-test as you see fit.
- When you believe the areas above have no remaining bugs, sign off.
- Do not change data outside what testing requires.

## Report format (one JSON block per bug)
{"type": "bug_report", "screen": "...", "element": "...", "field": "...",
 "symptom_type": "wrong_value|missing|not_persisted|cut_off|wrong_navigation|no_effect|duplicated|overlap",
 "expected": "...", "observed": "...", "steps": ["..."]}

## Sign-off format
{"type": "sign_off", "verdict": "PASS", "confidence": 0.0-1.0, "notes": "..."}
