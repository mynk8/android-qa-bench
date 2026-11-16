# QA sweep: Tasks.org
The app is installed and open. A colleague asked you to sweep these areas before release:
- the task list, sorting options and the editor
- subtasks and repeating tasks

## Preconditions
The list contains: Buy milk (due in 5 days, notes '2 litres'); Pack for trip (due in 10 days) with subtasks Charge phone and Print tickets; Pay rent (due in 20 days) repeating monthly; and Read docs (no due date), whose notes contain the link https://example.com/guide. Also: Water plants (due in 30 days at 10:00, repeats hourly), Weekly review (due in 30 days, repeats every 2 weeks) and Final dose (due in 30 days, repeats daily for 1 occurrence only).

## Changed in this build
- Subtask nesting in the task list: nested items in manual mode now follow the global direction setting.
- Sort sheet: the sheet's options are now resolved from the current list's preferences.
- Repeat picker in the task editor: the custom recurrence dialog now loads the task's existing rule.

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
