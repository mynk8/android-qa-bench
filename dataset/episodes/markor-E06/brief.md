# QA sweep: Markor
The app is installed and open. A colleague asked you to sweep these areas before release:
- todo.txt files
- editor settings
- search and replace

## Preconditions
The notebook folder contains Shopping.md, todo.txt, Notes.md, Single.md (one line, 'gamma', with no newline at the end), Regex.md (the line 'cat@home'), Regex2.md (the line 'cat@home dog@home') Money.md (the line 'Costs $5 and $10'), Indent.md ('- item' then '  - child'), Indent2.md ('- a' then '  - deep') and a folder Zeta.

## Changed in this build
- Editor settings font options: each font entry now shows a preview loaded in that font.
- Editor overflow menu typing helpers: their toggles are now applied directly to the open editor session.
- Todo.txt mark-done action: the done prefix is now built from one constant template.
- Search and replace dialog: the input fields are now built from a shared layout.

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
