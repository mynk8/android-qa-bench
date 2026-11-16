# QA sweep: Amaze File Manager
The app is installed and open. A colleague asked you to sweep these areas before release:
- file and folder operations
- creating new files and folders
- searching within a folder

## Preconditions
Internal storage has a folder AndroidQA/Amaze containing: folder Alpha (with readme.txt), folder Beta (with its own readme.txt), files report+final.txt and notes.txt, and two photos, photo.jpg and keep.jpg. No bookmarks have been added.

## Changed in this build
- Encryption dialog: the two passphrase inputs are now compared on every keystroke in either one.
- Copy and move between folders: the destination directory is now built before the operation's checks run.
- Search within a folder: matches are now delivered progressively while the folder scan is running.
- Retitling prompt: input validation for files and folders is now handled by a consolidated validator.

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
