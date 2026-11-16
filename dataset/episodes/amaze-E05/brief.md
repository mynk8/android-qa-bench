# QA sweep: Amaze File Manager
The app is installed and open. A colleague asked you to sweep these areas before release:
- the navigation drawer
- managing files in a folder
- opening and previewing text files

## Preconditions
Internal storage has a folder AndroidQA/Amaze containing: folder Alpha (with readme.txt), folder Beta (with its own readme.txt), files report+final.txt and notes.txt, and two photos, photo.jpg and keep.jpg. No bookmarks have been added.

## Changed in this build
- Built-in text viewer: the contents of large text files are now read in chunks rather than all at once.
- New folder prompt: the name is now validated while typing, before the create button is enabled.
- Navigation drawer media categories: per-item actions now load the storage location from the open category page.
- Batch overflow menu: the invert-marking entry is now handled entirely inside the list adapter.

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
