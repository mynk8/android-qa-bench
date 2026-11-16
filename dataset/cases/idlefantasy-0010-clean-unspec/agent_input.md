# Test case Idle Fantasy-TC-0010
App: Idle Fantasy (already open on the device)

## Context
The Profile screen has a strip of tabs (Skills, Inventory, Gear, Pets, Achievements, Notes, Bestiary, Armory, Bonuses, Banners). The bottom bar switches between the main sections.

## Preconditions
Character Aldric (human) has 2,567,890 coins, Mercantile level 99, Attack/Strength/Defense/Hitpoints level 70, Ranged and Magic 40, Prayer 45, Smithing level 19 with 4,400 XP, Mining 50. Equipped: Iron Sword (Weapon (Atk)), Bronze Pickaxe, Bronze Axe, Bronze Fishing Rod, Bronze Boots; the Shop's Keep one of each item toggle is off and no item is locked. Inventory: Bronze Pickaxe x1, Bronze Axe x2, Bronze Fishing Rod x1, Bronze Boots x1, Iron Sword x3, Bronze Dagger x1, Agility Cape x1, Mithril Platebody, Adamantite Platebody, Slayer Platebody, Runite Chainbody, Runite Platebody and Gilded Platebody x1 each, Steel Full Helmet x1, Mithril Med Helmet x1, Copper Ore x40, Tin Ore x25, Stone x12, Logs x30, Pumpkin x12, Tomato x9, Cowhide x14, Feather x60, Wool x7. Prestige: Attack and Hitpoints are each prestiged once, Attack owns Precision tiers I and II and Hitpoints owns Vitality tier I (combat stat prestige bonuses +9 Attack and +4 Hitpoints). Infinite Tower bonuses earned: +7% XP, +12% coin drops and +150 HP. Quests completed: Mining I, Fishing I, Woodcutting I and Smithing I, plus the guild quests Copper Run, Iron Quota and Shrimp Haul (3 guild quests). No session is running and the queue is empty.

## Steps
1. Tap "Profile" in the bottom bar and open the "Bonuses" tab.
2. Tap "Home" in the bottom bar.
3. Tap "Profile" in the bottom bar again.
4. Look at which tab is selected and what it shows.

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
