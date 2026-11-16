# QA sweep: Amaze File Manager
The app is installed and open. A colleague asked you to sweep these areas before release:
- the navigation drawer
- working with multiple files
- file details and properties

## Preconditions
Internal storage has a folder AndroidQA/Amaze containing: folder Alpha (with readme.txt), folder Beta (with its own readme.txt), files report+final.txt and notes.txt, and two photos, photo.jpg and keep.jpg. No bookmarks have been added.

## Changed in this build
- Navigation drawer category views: the file list now switches its on-screen controls when entering and leaving these views.
- Multi-file overflow menu: the bulk-marking entry is now handled as an on/off toggle of the current state.
- Navigation drawer storage list: the storage volumes are now resolved each time the drawer opens.
- File properties dialog: folder sizes and dates are now computed in the background by a separate task after the dialog opens.

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
