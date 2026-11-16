# QA sweep: Amaze File Manager
The app is installed and open. A colleague asked you to sweep these areas before release:
- copying, pasting and renaming files and folders
- sorting and directory view options
- bookmarks

## Preconditions
Internal storage has a folder AndroidQA/Amaze containing: folder Alpha (with readme.txt), folder Beta (with its own readme.txt), files report+final.txt and notes.txt, and two photos, photo.jpg and keep.jpg. No bookmarks have been added.

## Changed in this build
- Directory view options: the list or grid choice is now stored per folder path.
- Paste conflicts: the Rename choice now creates the renamed copy of a pasted folder in a new way.
- Bookmarks in the drawer: entries are now ordered by when they were added.
- Folder copying: the contents of a renamed folder copy are now written to their destination in a new way.

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
