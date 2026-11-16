# QA sweep: Tasks.org
The app is installed and open. A colleague asked you to sweep these areas before release:
- the task list, including sorting, grouping and how each row is shown
- the task editor and its date settings
- subtasks and repeating tasks

## Preconditions
The list contains: Buy milk (due in 5 days, notes '2 litres'); Pack for trip (due in 10 days) with subtasks Charge phone and Print tickets; Pay rent (due in 20 days) repeating monthly; and Read docs (no due date), whose notes contain the link https://example.com/guide.

## Changed in this build
- Task editor date picker: the time shortcuts are now taken from the app's date and time preferences.
- Due date grouping in the task list: the boundaries between groups are now computed with the previous comparison logic.
- Subtask nesting in the task list: nested tasks are now indented by a constant step per nesting level.
- Date badges on task rows: the badge for each date field is now built independently of the others.

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
