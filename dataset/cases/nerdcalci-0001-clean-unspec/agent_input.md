# Test case NerdCalci-TC-0001
App: NerdCalci (already open on the device)

## Context
NerdCalci shows a result next to every line of a file. The keywords total, avg and grand_total are calculation keywords.

## Preconditions
Nine calculation files exist, newest first on the home screen: Expenses (rent = 1200, food = 340.5, fuel = 85.25, then the lines total and avg); Monthly budget (salary = 2500, bonus = 300.5, total, a blank line, gift = 49.5, total, grand_total); Temperatures (-5 celsius; -10 celsius in fahrenheit; -40 fahrenheit in celsius; -65 fahrenheit in celsius); Temperature sums (25 celsius + 5 celsius; 20 celsius - 5 celsius; 10 celsius + 18 fahrenheit); Number bases (15 dec in hex; 10 dec in bin; 64 dec in oct; 255 dec in hex); Date gaps (datetime(1981, 2, 14, 18, 32, 0) to datetime(2026, 5, 3, 14, 49, 9); datetime(2020, 3, 10, 22, 15, 0) to datetime(2024, 8, 25, 9, 40, 30); date(2024, 1, 1) to date(2024, 1, 8)); Time differences (datetimeZ(2024, 1, 1, 10, 0, 0, "UTC") to datetimeZ(2024, 1, 1, 6, 30, 0, "UTC"); datetimeZ(2024, 3, 5, 9, 15, 0, "UTC") to datetimeZ(2024, 3, 3, 16, 45, 0, "UTC"); datetimeZ(2024, 1, 1, 6, 30, 0, "UTC") to datetimeZ(2024, 1, 1, 10, 0, 0, "UTC")); Remainders (100 % 13; 47 % 20; 19.5 % 4; a = 50; a % 14; 250 + 20%); Percentages (price = 240; disc = 15; disc% of price; disc% off price; tax = 8.5; tax% of 1200; 10% of 80). Result precision is the default of 2 decimals and no file is pinned or locked.

## Steps
1. On the home screen tap the file "Expenses" (scroll the list if needed) to open it.
2. Read the results next to the lines total and avg.
3. Go back to the home screen, open the file "Monthly budget" and read the result next to its last line, grand_total.

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
