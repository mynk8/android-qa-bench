# QA sweep: NerdCalci
The app is installed and open. A colleague asked you to sweep these areas before release:
- operators and percentages
- variables used in calculations
- pinning and locking files

## Preconditions
Nine calculation files exist, newest first on the home screen: Expenses (rent = 1200, food = 340.5, fuel = 85.25, then the lines total and avg); Monthly budget (salary = 2500, bonus = 300.5, total, a blank line, gift = 49.5, total, grand_total); Temperatures (-5 celsius; -10 celsius in fahrenheit; -40 fahrenheit in celsius; -65 fahrenheit in celsius); Temperature sums (25 celsius + 5 celsius; 20 celsius - 5 celsius; 10 celsius + 18 fahrenheit); Number bases (15 dec in hex; 10 dec in bin; 64 dec in oct; 255 dec in hex); Date gaps (datetime(1981, 2, 14, 18, 32, 0) to datetime(2026, 5, 3, 14, 49, 9); datetime(2020, 3, 10, 22, 15, 0) to datetime(2024, 8, 25, 9, 40, 30); date(2024, 1, 1) to date(2024, 1, 8)); Time differences (datetimeZ(2024, 1, 1, 10, 0, 0, "UTC") to datetimeZ(2024, 1, 1, 6, 30, 0, "UTC"); datetimeZ(2024, 3, 5, 9, 15, 0, "UTC") to datetimeZ(2024, 3, 3, 16, 45, 0, "UTC"); datetimeZ(2024, 1, 1, 6, 30, 0, "UTC") to datetimeZ(2024, 1, 1, 10, 0, 0, "UTC")); Remainders (100 % 13; 47 % 20; 19.5 % 4; a = 50; a % 14; 250 + 20%); Percentages (price = 240; disc = 15; disc% of price; disc% off price; tax = 8.5; tax% of 1200; 10% of 80). Result precision is the default of 2 decimals and no file is pinned or locked.

## Changed in this build
- Variables in calculations: assignments are now resolved from top to bottom by a simpler evaluation pass on every edit.
- Home screen pin and lock controls: pinned files are now kept at the top of the list.
- Parsing of the % operator: a % after an operand is now interpreted by a new rule.

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
