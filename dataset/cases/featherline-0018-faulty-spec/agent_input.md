# Test case Featherline-TC-0018
App: Featherline (already open on the device)

## Context
Night owl mode is a switch in the Schedule section of the group editor, with a description that names the time at which the day ends.

## Preconditions
Fresh install with no medications, plans or lab results.

## Steps
1. Open the Plan tab, scroll down and tap Add to create a group.
2. In the Schedule section find the Night owl mode switch and read its description.
3. Compare the time written in the description with the way times are written on the Time row of the same section.

## Expected results
- The description names the day-end time in the same 12-hour or 24-hour style as the other times in the section (for example 4:00 AM when times show AM and PM).

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
