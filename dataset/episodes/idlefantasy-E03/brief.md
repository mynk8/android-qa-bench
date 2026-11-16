# QA sweep: Idle Fantasy
The app is installed and open. A colleague asked you to sweep these areas before release:
- the shop
- gear and equipment
- the bestiary

## Preconditions
Character Aldric (human) has 2,567,890 coins, Mercantile level 99, Attack/Strength/Defense/Hitpoints level 70, Ranged and Magic 40, Prayer 45, Smithing level 19 with 4,400 XP, Mining 50. Equipped: Iron Sword (Weapon (Atk)), Bronze Pickaxe, Bronze Axe, Bronze Fishing Rod, Bronze Boots; the Shop's Keep one of each item toggle is off and no item is locked. Inventory: Bronze Pickaxe x1, Bronze Axe x2, Bronze Fishing Rod x1, Bronze Boots x1, Iron Sword x3, Bronze Dagger x1, Agility Cape x1, Mithril Platebody, Adamantite Platebody, Slayer Platebody, Runite Chainbody, Runite Platebody and Gilded Platebody x1 each, Steel Full Helmet x1, Mithril Med Helmet x1, Copper Ore x40, Tin Ore x25, Stone x12, Logs x30, Pumpkin x12, Tomato x9, Cowhide x14, Feather x60, Wool x7. Prestige: Attack and Hitpoints are each prestiged once, Attack owns Precision tiers I and II and Hitpoints owns Vitality tier I (combat stat prestige bonuses +9 Attack and +4 Hitpoints). Infinite Tower bonuses earned: +7% XP, +12% coin drops and +150 HP. Quests completed: Mining I, Fishing I, Woodcutting I and Smithing I, plus the guild quests Copper Run, Iron Quota and Shrimp Haul (3 guild quests). No session is running and the queue is empty.

## Changed in this build
- Shop bulk clearance actions: the preview total is now computed by a separate pass before the confirmation step.
- Gear tab slot chooser: candidate items are now ranked by their unlock threshold, with title as the tiebreak.
- Quest board: available quests are now refreshed from the character state each time the board opens.
- Per-item trade-in panel: the reserved keeper quantity is now computed from the inventory alone, as a separate step.

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
