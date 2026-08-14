"""Static content: skills, items, enemy and floor tables, and every text pool.

Data only, plus the generators that draw from it. This module imports nothing
from the rest of the game, which is what keeps the import graph acyclic --
`models` needs SKILLS and ITEMS, so content must never need models back. The one
place that would have (`make_epitaph`'s Hero annotation) is handled by
`from __future__ import annotations`, which keeps annotations as strings.
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # annotation only -- importing models at runtime would cycle
    from models import Hero

# ── Skills ─────────────────────────────────────────────────────────────────────

SKILLS = {
    "iron_skin":    {"name": "Iron Skin",    "desc": "-1 damage from all hits",          "stat": "defense", "val": 1},
    "keen_eye":     {"name": "Keen Eye",     "desc": "+1 vision radius",                 "stat": "vision",  "val": 1},
    "quick_feet":   {"name": "Quick Feet",   "desc": "you move with unusual speed",      "stat": "speed",   "val": 1},
    "tough_soul":   {"name": "Tough Soul",   "desc": "+5 max HP",                        "stat": "max_hp",  "val": 5},
    "sharp_blade":  {"name": "Sharp Blade",  "desc": "+2 attack",                        "stat": "attack",  "val": 2},
    "lucky":        {"name": "Lucky",        "desc": "10% chance to dodge any hit",      "stat": "dodge",   "val": 10},
    "bloodline":    {"name": "Bloodline",    "desc": "+3 max HP and +1 attack",          "stat": "max_hp",  "val": 3},
    "quiet_step":   {"name": "Quiet Step",   "desc": "enemies notice you 1 tile later",  "stat": "vision",  "val": 0},
    "stone_will":   {"name": "Stone Will",   "desc": "-2 damage from all hits",          "stat": "defense", "val": 2},
    "wolf_eye":     {"name": "Wolf Eye",     "desc": "+2 vision radius",                 "stat": "vision",  "val": 2},
    "killing_blow": {"name": "Killing Blow", "desc": "+3 attack, first strike",          "stat": "attack",  "val": 3},
    "old_blood":    {"name": "Old Blood",    "desc": "+8 max HP",                        "stat": "max_hp",  "val": 8},
}

SKILL_VOICE = {
    "iron_skin": [
        ("You'll learn what I learned: pain is a teacher.",
         "Every scar I carried, I carry still. Take them. They're yours now."),
        ("I stopped flinching somewhere on the third floor.",
         "By the time I died I barely felt it. That sounds worse than it is."),
    ],
    "keen_eye": [
        ("I used to close my eyes in the dark. Then I learned to look harder.",
         "The dungeon hides its worst things in plain sight. Look closer than you think you need to."),
        ("There's a moment when your eyes adjust and you see what was always there.",
         "Train yourself to notice before you need to. After is too late."),
    ],
    "quick_feet": [
        ("Running isn't cowardice. I learned that too late, maybe.",
         "The ones who survive are the ones who choose their moment. Keep your feet ready."),
        ("Distance is a weapon. Nobody tells you that.",
         "I survived twice by retreating. I died once by standing firm. Draw your own conclusions."),
    ],
    "tough_soul": [
        ("We are harder to kill than we look. This family has always been.",
         "Carry that. When you feel yourself slipping, remember who you come from."),
        ("You will take hits that should end you. Don't be surprised. Don't stop.",
         "The dungeon expects you to fall. Disappoint it."),
    ],
    "sharp_blade": [
        ("Every enemy I killed, I killed because I didn't hesitate.",
         "Strike before doubt finds you. The blade doesn't care about fairness."),
        ("The difference between alive and dead is usually one swing.",
         "Make yours first. Make it count. Don't think about it -- thinking is what they're counting on."),
    ],
    "lucky": [
        ("I can't explain it. Sometimes the blow just... misses.",
         "Maybe it's the blood. Maybe it's something older. Don't question it. Move."),
        ("I've been told I'm lucky. I think luck is something you inherit.",
         "It won't save you forever. But it might save you today. Today is enough."),
    ],
    "bloodline": [
        ("There's something in us that refuses to break cleanly.",
         "I felt it on floor four -- something deeper than training. It's in you too."),
        ("The older the line, the harder the dying.",
         "We've been down here enough times that the dungeon knows our blood. Make it regret that."),
    ],
    "quiet_step": [
        ("I went two whole floors once without a single fight. Not hiding -- just moving right.",
         "They can't kill what they can't hear. You're light. Use it."),
        ("Sound travels differently down here. Footsteps announce you before you arrive.",
         "Move like you're apologizing for existing. You can stop apologizing once they're dead."),
    ],
    "stone_will": [
        ("By the end I was taking hits that would have killed younger kin.",
         "It's not armor. It's something deeper. A refusal. Pass it on."),
        ("Pain is negotiable. I negotiated hard.",
         "Stand your ground. Let them break themselves on you."),
    ],
    "wolf_eye": [
        ("I could see them coming from across the room. That's not nothing.",
         "Vision is time. More of one means more of the other. Use both."),
        ("The dungeon rewards the ones who see it clearly.",
         "I mapped every floor in my head before I entered. You can too."),
    ],
    "killing_blow": [
        ("I stopped playing defensively around floor three. Everything got easier.",
         "The best defense is ending it before it starts. You have the hands for it."),
        ("Every fight I won, I won in the first two exchanges.",
         "If it's still standing after your opener, start worrying."),
    ],
    "old_blood": [
        ("We've been dying down here longer than most families have existed.",
         "That's not tragedy. That's depth. You carry all of it."),
        ("I don't know how old the blood is. Old enough to matter.",
         "Feel it when you're hurt and still moving. That's not you. That's everyone before you."),
    ],
}

# ── Floor data ─────────────────────────────────────────────────────────────────

FLOOR_NAMES = {
    1: ["the Shallow Dark",  "the Entry Vaults",    "the First Silence",  "the Upper Stones"],
    2: ["the Rat Warrens",   "the Gnaw Tunnels",    "the Narrow Dark",    "the Festering Halls"],
    3: ["the Goblin Halls",  "the Carved Passages", "the Old Workings",   "the Abandoned Tier"],
    4: ["the Deep Places",   "the Lower Dark",      "the Sunken Vaults",  "the Drowned Floors"],
    5: ["the Nameless Depths","the Final Dark",      "the Hollow Below",   "the Forgotten Root"],
}

FLOOR_ARRIVAL = {
    1: [
        "Damp stone. A distant drip. The dungeon breathes around you.",
        "Cold hits you first, then the dark. The staircase closes behind you.",
        "You've heard this described. The descriptions weren't wrong, exactly. Just incomplete.",
        "The torch would help. You didn't bring one. You remember now why the others always did.",
        "The floor is wet. Something was here recently. You don't think about what.",
    ],
    2: [
        "The walls narrow. Something skitters in the walls.",
        "Small bones underfoot. You try not to count them.",
        "A smell you can't name. Something animal. Close.",
        "Lower now. The sound of the surface is completely gone.",
        "The passages here were not made by hands. They were worn.",
    ],
    3: [
        "Old torches, long cold. You can smell fire that happened years ago.",
        "The walls here are worked stone. Someone built this place for a reason.",
        "Carvings you don't understand. You don't stop to study them.",
        "The ceiling is higher here. You feel, somehow, more exposed.",
        "You can hear them before you see them. That's not better.",
    ],
    4: [
        "The air tastes of iron. The dark here is a different quality of dark.",
        "Your ancestors' bones are somewhere above you. You try to find that comforting.",
        "Something has changed in the air. You don't have a word for it. Wrong.",
        "The walls sweat. The floor is slightly warm. You don't ask why.",
        "Deeper than most of your line. You remember that. It doesn't help.",
    ],
    5: [
        "Nothing has been here in a long time. Nothing that lived, anyway.",
        "You are the deepest member of your family. That is not a comfort.",
        "The silence here has weight. You move carefully inside it.",
        "No one has told you what to expect here. No one made it back to tell.",
        "Whatever is down here has been waiting. You get the sense it is patient.",
    ],
}

# ── Enemy name pools ───────────────────────────────────────────────────────────

ENEMY_NAMES = {
    "rat":         ["Blacktooth", "Mange", "Scrabble", "One-Eye", "Gnaw", "Fester",
                    "Old Grey", "Three-Claw", "the Hungry", "Riddled"],
    "cave_spider": ["Long-Legs", "Black Widow", "the Spinner", "Nestmother",
                    "Venom", "Pale", "Eight-Eye", "the Patient"],
    "goblin":      ["Grix", "Skrag", "Nip", "Bile", "Cratch", "Mung", "Squib",
                    "Notch", "Flinch", "Twice-Stabbed", "the Crooked", "Soot"],
    "kobold":      ["Yip", "Skitter", "Gnash", "the Tunnel-Runner", "Pack-Front",
                    "Runt", "the Loud", "Bonebiter"],
    "orc":         ["Grond", "Marak", "Bash", "Krug", "Stonefist", "Blackblood",
                    "the Scarred", "Broke-Horn", "Rawbone", "Cinderhand"],
    "skeleton":    ["Old Soldier", "the Rattling", "Bones", "the Restless",
                    "Hollow-Eye", "War-Debt", "the Standing", "Long-Dead"],
    "zombie":      ["the Heavy", "Old Wound", "Three-Day", "the Stumbling",
                    "Slow Death", "the Risen", "Rot-Jaw", "the Persistent"],
    "troll":       ["Gorm the Hungry", "Old Stench", "Wallbreaker", "the Patient",
                    "Mossgut", "Twice-Killed", "the Immovable"],
    "wraith":      ["Cold Memory", "the Forgotten", "Thin Air", "the Pale",
                    "Old Grief", "the Waning", "Hollow", "the Unfinished"],
    "dark_elf":    ["Shrike", "the Swift", "Needle", "Eventide",
                    "Silverthorn", "the Quiet", "Last Breath", "Ash"],
    "demon":       ["the Hollow One", "Ashvael", "the Patient", "Grief-in-Form",
                    "the Collector", "Old Wound", "the Grinning Dark", "Vael"],
    "vampire":     ["the Thirsty", "Old Red", "the Pale Count", "Ashen",
                    "Bloodkeep", "Thin-Lipped", "the Ancient", "Duskveil"],
    "lich":        ["the Remembered", "Old Knowledge", "the Preserved",
                    "Death's Scholar", "the Undying", "Ashcrown", "the Patient"],
}

FLOOR_ENEMIES = {
    1: [("rat",        "r", 4,  1, 1, 4), ("cave_spider", "s", 6,  2, 2, 4)],
    2: [("rat",        "r", 4,  1, 1, 4), ("cave_spider", "s", 6,  2, 2, 4),
        ("goblin",     "g", 8,  2, 2, 5), ("kobold",      "k", 5,  1, 1, 5)],
    3: [("goblin",     "g", 8,  2, 2, 5), ("kobold",      "k", 5,  1, 1, 5),
        ("orc",        "o", 14, 3, 3, 6), ("skeleton",    "S", 10, 3, 3, 5),
        ("zombie",     "z", 15, 2, 3, 4)],
    4: [("orc",        "o", 14, 3, 3, 6), ("skeleton",    "S", 10, 3, 3, 5),
        ("zombie",     "z", 15, 2, 3, 4), ("troll",       "T", 22, 4, 5, 6),
        ("wraith",     "W", 8,  4, 4, 7), ("dark_elf",    "e", 12, 5, 5, 7)],
    5: [("troll",      "T", 22, 4, 5, 6), ("dark_elf",    "e", 12, 5, 5, 7),
        ("demon",      "D", 30, 6, 8, 8), ("vampire",     "V", 20, 4, 6, 7),
        ("lich",       "L", 25, 6, 9, 8)],
}

# ── Items ──────────────────────────────────────────────────────────────────────

ITEMS = {
    "rusty_dagger":    {"name": "Rusty Dagger",      "glyph": ")", "slot": "weapon",     "stat": "attack",  "val": 1,  "weight": 1,
                        "flavor": "The edge is poor. It will have to do."},
    "short_sword":     {"name": "Short Sword",       "glyph": ")", "slot": "weapon",     "stat": "attack",  "val": 2,  "weight": 2,
                        "flavor": "Balanced. Someone kept this in good condition."},
    "battle_axe":      {"name": "Battle Axe",        "glyph": ")", "slot": "weapon",     "stat": "attack",  "val": 3,  "weight": 4,
                        "flavor": "Heavy. Your arm will ache. Worth it."},
    "enchanted_blade": {"name": "Enchanted Blade",   "glyph": ")", "slot": "weapon",     "stat": "attack",  "val": 4,  "weight": 2,
                        "flavor": "It hums faintly. Something is still in it."},
    "worn_buckler":    {"name": "Worn Buckler",      "glyph": "[", "slot": "armor",      "stat": "defense", "val": 1,  "weight": 2,
                        "flavor": "Dented but solid. It will catch a blow or two."},
    "leather_vest":    {"name": "Leather Vest",      "glyph": "[", "slot": "armor",      "stat": "defense", "val": 1,  "weight": 2,
                        "flavor": "Cured and fitted by someone who knew what they were doing."},
    "chainmail":       {"name": "Chainmail",         "glyph": "[", "slot": "armor",      "stat": "defense", "val": 2,  "weight": 5,
                        "flavor": "Heavy. Reassuring in the way that weight can be."},
    "plate_shard":     {"name": "Plate Shard",       "glyph": "[", "slot": "armor",      "stat": "defense", "val": 2,  "weight": 4,
                        "flavor": "Half a breastplate. The other half isn't here."},
    "healing_potion":  {"name": "Healing Potion",    "glyph": "!", "slot": "consumable", "stat": "hp",      "val": 10, "weight": 1,
                        "flavor": "Bitter. It works anyway."},
    "greater_healing": {"name": "Greater Healing",   "glyph": "!", "slot": "consumable", "stat": "hp",      "val": 20, "weight": 1,
                        "flavor": "The warmth spreads before the bottle is empty."},
    "strength_tonic":  {"name": "Strength Tonic",    "glyph": "!", "slot": "consumable", "stat": "attack",  "val": 2,  "weight": 1,
                        "flavor": "Tastes like copper. Your hands feel steadier."},
    "scroll_sight":    {"name": "Scroll of Sight",   "glyph": "?", "slot": "consumable", "stat": "vision",  "val": 2,  "weight": 1,
                        "flavor": "The words dissolve as you read them. The dark recedes."},
    "scroll_fortune":  {"name": "Scroll of Fortune", "glyph": "?", "slot": "consumable", "stat": "dodge",   "val": 10, "weight": 1,
                        "flavor": "Something shifts. You feel like things will miss you more."},
    "iron_ring":       {"name": "Iron Ring",         "glyph": "=", "slot": "accessory",  "stat": "defense", "val": 1,  "weight": 1,
                        "flavor": "Plain. Heavy. Old."},
    "wolf_tooth":      {"name": "Wolf Tooth",        "glyph": '"', "slot": "accessory",  "stat": "attack",  "val": 1,  "weight": 1,
                        "flavor": "Strung on gut. It belonged to someone who survived."},
    "ancestor_coin":   {"name": "Ancestor's Coin",   "glyph": "$", "slot": "accessory",  "stat": "max_hp",  "val": 5,  "weight": 1,
                        "flavor": "Warm to the touch. Like something is looking back."},
}

CARRY_MAX = 20

FLOOR_ITEMS = {
    1: ["rusty_dagger", "worn_buckler", "healing_potion", "wolf_tooth", "iron_ring"],
    2: ["rusty_dagger", "short_sword", "worn_buckler", "leather_vest",
        "healing_potion", "scroll_sight", "wolf_tooth", "iron_ring"],
    3: ["short_sword", "battle_axe", "leather_vest", "chainmail",
        "healing_potion", "strength_tonic", "scroll_sight", "ancestor_coin"],
    4: ["battle_axe", "chainmail", "plate_shard", "healing_potion",
        "greater_healing", "strength_tonic", "scroll_fortune", "ancestor_coin"],
    5: ["enchanted_blade", "plate_shard", "greater_healing",
        "scroll_fortune", "ancestor_coin", "strength_tonic"],
}

# ── Combat messages ────────────────────────────────────────────────────────────

PLAYER_HIT = [
    "You drive your blade into {enemy}.",
    "You swing at {enemy} and connect.",
    "You land a solid hit on {enemy}.",
    "Your strike finds {enemy}.",
    "{enemy} staggers from your blow.",
    "You catch {enemy} off-guard.",
    "A clean hit. {enemy} reels.",
    "You press forward and cut {enemy}.",
]

PLAYER_KILL = [
    "{enemy} crumples and is still.",
    "{enemy} falls. It's over.",
    "You stand over the body of {enemy}.",
    "{enemy} makes a sound and then doesn't.",
    "The fight leaves {enemy} all at once.",
    "{enemy} drops. You breathe.",
    "{enemy} is dead. You keep moving.",
]

ENEMY_HIT = [
    "{enemy} catches you with a heavy blow.",
    "A claw from {enemy} rakes your arm.",
    "{enemy} lunges and you can't get clear.",
    "{enemy} finds a gap in your guard.",
    "You take a hit from {enemy}.",
    "{enemy} strikes before you can answer.",
    "The blow from {enemy} lands harder than expected.",
    "{enemy} is faster than you thought.",
]

ENEMY_MISS = [
    "{enemy} swings -- you pull back just enough.",
    "You sidestep {enemy}'s strike.",
    "{enemy} lunges and finds nothing.",
    "The blow from {enemy} goes wide.",
    "You read {enemy}'s move and aren't there for it.",
    "{enemy} misses. You don't.",
]

ENEMY_SPOT = [
    "{enemy} turns toward you.",
    "{enemy} goes still, then moves.",
    "You hear {enemy} before you see it.",
    "{enemy} has noticed you.",
    "{enemy} comes out of the dark.",
]

ANCESTOR_LEVEL_MSGS = [
    "{ancestor} made it to floor {floor}. You are past that now.",
    "Level up. {ancestor} didn't reach this strength. You have.",
    "{ancestor} left you something for this moment. You feel it.",
    "You think of {ancestor}. Keep going.",
    "{ancestor} would know this feeling.",
    "The {ancestor} line does not stop here.",
]

ANCESTOR_KILL_MSGS = [
    "{ancestor} died to one of these. Not you.",
    "You put down the {enemy}. {ancestor} couldn't. You remember.",
    "{enemy} falls. {ancestor} would have wanted this.",
    "For {ancestor}.",
    "One of these killed {ancestor}. You are even.",
    "{ancestor} fell to its kind. The debt is paid.",
]

WIN_LINES = [
    "The passage ends in a chamber that should not exist.",
    "No bones here. No carvings. The dungeon has no name for this place.",
    "Something made this room before the dungeon was the dungeon.",
    "You stand in it and feel the weight of every generation that didn't.",
    "You do not know what you were looking for.",
    "You know that you are the first.",
]

# ── Hero traits ────────────────────────────────────────────────────────────────

HERO_TRAITS = [
    "cautious", "reckless", "curious", "quiet", "stubborn",
    "haunted", "determined", "unlucky", "proud", "weary",
    "restless", "calm", "sharp", "grim", "hopeful",
]

TRAIT_INTRO = {
    "cautious":    "You check every shadow before stepping into it. It has not saved the others.",
    "reckless":    "Your family says you move too fast. You think they moved too slow.",
    "curious":     "You want to know what's down there. That's the most dangerous thing about you.",
    "quiet":       "You don't announce yourself. You've noticed the dungeon doesn't either.",
    "stubborn":    "You've been told to turn back before. You've never listened. You don't plan to start.",
    "haunted":     "You dream about the bones you've seen. They were family. They still are.",
    "determined":  "You have a reason to reach the bottom. You haven't told anyone what it is.",
    "unlucky":     "Things go wrong around you. You've started to think that's survivable.",
    "proud":       "You are not the first. You intend to be the one they remember.",
    "weary":       "You've been preparing for this your whole life. You're tired of preparing.",
    "restless":    "The surface never felt like enough. This is where you were always going.",
    "calm":        "You don't panic. The dungeon hasn't given you a reason to yet.",
    "sharp":       "You notice things. You've been noticing things since you were small.",
    "grim":        "You don't expect to come back. You're going anyway.",
    "hopeful":     "Against all evidence, you believe it ends well. That might be the blood talking.",
}

TRAIT_EPITAPH = {
    "cautious":   "{name}, who was careful until the end.",
    "reckless":   "{name}, who went forward when others would have stopped.",
    "curious":    "{name}, who wanted to know what was in the next room.",
    "quiet":      "{name}, who moved through the dungeon like a rumor.",
    "stubborn":   "{name}, who did not turn back.",
    "haunted":    "{name}, who knew what waited below and went anyway.",
    "determined": "{name}, who had a reason none of us knew.",
    "unlucky":    "{name}, for whom the dungeon had no patience.",
    "proud":      "{name}, who deserved a better ending than this.",
    "weary":      "{name}, who had been ready for this a long time.",
    "restless":   "{name}, who finally found the place they were looking for.",
    "calm":       "{name}, who faced {cause} without flinching.",
    "sharp":      "{name}, who saw everything coming except the end.",
    "grim":       "{name}, who expected this and came anyway.",
    "hopeful":    "{name}, who believed until {cause} proved otherwise.",
}

# ── Room inscriptions ──────────────────────────────────────────────────────────

ROOM_INSCRIPTIONS = [
    "A name is scratched into the wall. You recognize it.",
    "Someone drew a line here and stopped.",
    "Old blood on the floor, dried to almost nothing.",
    "The walls here are smoother than elsewhere. Worn by hands.",
    "You find a tooth. You don't know whose.",
    "A bootprint in the dust, weeks old at least.",
    "Something was dragged through this room recently.",
    "The smell of old fire. No source you can find.",
    "A ring of stones in the corner -- a camp, long abandoned.",
    "The wall here has been clawed. Something big.",
    "A single candle stub, never lit.",
    "Scratched into the floor: 'DO NOT STOP HERE.'",
    "A broken blade, rusted past use.",
    "Fresher scratches than you'd like. Something lives here.",
    "The silence in this room is a different quality than the hall.",
    "A message in a language you don't recognize.",
    "An old fire pit. Bones in the ash. You move on.",
    "Two sets of footprints in the dust. Only one leaves the room.",
    "Someone tried to block this door from the inside.",
    "The floor slopes here. You didn't notice it at first.",
    "A gap in the ceiling. Nothing looks back through it.",
    "Dried flowers, impossibly, in a crack in the wall.",
    "A single word scratched deep: DEEPER.",
    "The room smells like rain. There is no rain down here.",
    "Something was stacked here and taken. Long ago.",
]

# ── Epitaphs ───────────────────────────────────────────────────────────────────

EPITAPH_TEMPLATES = {
    "early": [
        "{name} came with hope. The first floor took it.",
        "{name} descended on {floor_name} and did not return.",
        "Here fell {name}, who had not yet learned the dungeon's patience.",
        "{name} met {cause} before their eyes had adjusted to the dark.",
        "The dungeon was patient. {name} was not.",
        "{name} of House {family} -- brief, and not forgotten.",
        "{name} went first. That is a kind of courage.",
        "A short descent: {name}, who learned something even so.",
    ],
    "mid": [
        "{name} reached {floor_name} before {cause} ended the journey.",
        "Few in this family descended as far as {name}. {cause} ended it.",
        "{name} carried the lessons of their blood to {floor_name}. It was not enough.",
        "Here rests {name}, who knew {floor_name} better than most of this line.",
        "{name} fought well. The dungeon fought better.",
        "A capable heir: {name}, who fell halfway to the answer.",
        "{name} -- farther than some, not far enough.",
        "The middle floors claimed {name}, as they claim most.",
    ],
    "deep": [
        "{name} went where the family had never gone. {cause} waited there.",
        "None before {name} had seen {floor_name}. None after will forget it.",
        "{name} found {floor_name}. {cause} found {name} first.",
        "The deepest of the line: {name}, who fell to {cause} at the edge of the unknown.",
        "{name} reached {floor_name}. This is not nothing.",
        "House {family} has never gone deeper than {name}. Yet.",
        "They say the deep floors are different. {name} knew that.",
        "{cause} ended {name} on {floor_name}. But {name} was here.",
    ],
}

# ── Last words ─────────────────────────────────────────────────────────────────

LAST_WORDS = {
    ("rat", 1): [
        "A rat. I was killed by a rat. Remember this.",
        "It wasn't the size of the thing. It was how many.",
        "Tell the next one: even small things can end you down here.",
        "I didn't take it seriously. That's the lesson.",
        "The floor is cold. I didn't expect the floor to be cold.",
    ],
    ("rat", 2): [
        "Still rats. Still dying to rats. I'm embarrassed.",
        "I thought I knew this floor. I didn't know this floor.",
        "They were faster here than above. Nobody mentioned that.",
        "Second floor. I made it to the second floor. It isn't enough.",
    ],
    ("goblin", 2): [
        "Quick little things. I didn't expect quick.",
        "The one that got me -- it had a scar already. Someone had tried before.",
        "I was overconfident. That's on me.",
        "It took everything I had and then a little more.",
    ],
    ("goblin", 3): [
        "Goblins are smarter than they look. I know that now.",
        "It laughed when it hit me. I keep thinking about that.",
        "I should have run. There's no shame in running.",
        "Three floors. I reached the third floor. Write that down.",
        "The goblin halls. I can see why they call it that.",
    ],
    ("orc", 3): [
        "It was bigger than the stories said. Or maybe fear made it bigger.",
        "I had it. I had it and then I didn't.",
        "Don't stand still against an orc. They're stronger standing still.",
        "It hit me once and I knew it was over. That was the worst part -- knowing.",
        "Floor three. I'm proud of floor three.",
    ],
    ("orc", 4): [
        "Floor four. I was proud to make it this far. Maybe too proud.",
        "An orc in the deep places is a different thing than an orc above.",
        "I could hear it breathing before I saw it. I should have taken that seriously.",
        "If you're reading this: orcs at this depth don't negotiate.",
    ],
    ("troll", 4): [
        "It regenerated. Nobody warned me it would regenerate.",
        "I killed it four times. On the fifth I was too tired.",
        "The smell of trolls is the last thing I'll ever smell. Isn't that something.",
        "The deep places. I was in the deep places. That has to count for something.",
        "Fight smart. I forgot to fight smart.",
    ],
    ("troll", 5): [
        "This is the deepest any of us have gone. Remember that.",
        "A troll in the nameless depths. I wasn't afraid. That surprised me.",
        "Floor five. I stood on floor five. Whatever that means.",
        "It was slower than I expected. I was slower than I expected.",
    ],
    ("cave_spider", 1): [
        "I couldn't see it coming. Too small. Too fast.",
        "The venom. Not the bite -- the venom.",
        "I didn't even see it until it was already on me.",
        "Spiders. It was always going to be spiders.",
    ],
    ("cave_spider", 2): [
        "There were dozens of them. The webs slowed me down first.",
        "I thought I'd cleared the room. I was wrong.",
        "The web caught my foot. That's all it took.",
    ],
    ("kobold", 2): [
        "It was one of a dozen. I only watched the one.",
        "Pack hunters. That's what I didn't account for.",
        "Small and quick and there were so many.",
    ],
    ("kobold", 3): [
        "Kobolds coordinate. I know that now.",
        "One distracted me. The others were already moving.",
        "Little things with a plan. Worse than big things without one.",
    ],
    ("skeleton", 3): [
        "It didn't feel pain. That changes everything.",
        "I kept waiting for it to slow down. It didn't slow down.",
        "Old soldier. Still dangerous. Still angry about something.",
        "Nothing to kill. Just something to outlast. I couldn't outlast it.",
    ],
    ("skeleton", 4): [
        "Something keeps these things moving. I never found out what.",
        "It fought like it had done this ten thousand times.",
        "It had no reason to stop. So it didn't.",
    ],
    ("zombie", 3): [
        "Slow. But I let it corner me. That's mine to own.",
        "The smell was wrong. I was distracted by the smell.",
        "It doesn't care if it gets hit. That's the terrifying part.",
    ],
    ("zombie", 4): [
        "I kept thinking it was finished. It wasn't finished.",
        "Persistent. The wrong kind of persistent.",
        "It shrugged off everything I had. Then it didn't.",
    ],
    ("wraith", 4): [
        "I couldn't quite hit it. It could quite hit me.",
        "Like fighting smoke that holds a grudge.",
        "Cold. The cold was the first warning. I should have run then.",
        "It passed through my guard like I wasn't there.",
    ],
    ("wraith", 5): [
        "The deep places have things that shouldn't be anywhere.",
        "I've never been so cold. Which, granted, is ending.",
        "I think it used to be someone. I think about that.",
    ],
    ("dark_elf", 4): [
        "Fast. Faster than anything has a right to be.",
        "It moved like it had done this a thousand times before. It has.",
        "I saw the blade before I felt it. Then I stopped seeing.",
    ],
    ("dark_elf", 5): [
        "Floor five and a dark elf. Worthy enough.",
        "They say dark elves don't fight fair. Correct.",
        "It didn't even seem to hurry.",
    ],
    ("vampire", 5): [
        "Every time I hit it, it healed. The math was always against me.",
        "I bled myself dry trying to put it down.",
        "The count just watched. Then it stopped watching.",
        "It's been down here longer than our family has been alive. Maybe longer.",
    ],
    ("lich", 5): [
        "The oldest thing I've ever seen. I was temporary to it.",
        "Magic. I had no answer for magic.",
        "It knew every move before I made it. Like it had seen me before.",
        "Floor five. A lich. I lasted longer than I deserved to.",
        "The lich is still down there. You should know that.",
    ],
    ("demon", 5): [
        "I saw it coming. I still couldn't stop it. Some things are like that.",
        "It looked almost sad when it killed me. I don't know what to do with that.",
        "Floor five. I made it to floor five. Whatever comes next -- go deeper.",
        "The demon didn't speak. I expected it to speak. I was wrong about a lot of things.",
        "It wasn't what I thought a demon would look like. It was worse.",
        "Tell them I looked at it. Tell them I didn't look away.",
    ],
    "default_early": [
        "I wasn't ready. I thought I was. I wasn't.",
        "Forgive me. I tried.",
        "It happened so fast. I didn't even have time to be afraid.",
        "The next one will do better. They have to.",
        "I wanted to go deeper. I want that on record somewhere.",
        "Don't mourn long. Get back down here.",
        "I've been thinking about home. That's probably what did it.",
        "I'll be here when you pass by. Look for me.",
    ],
    "default_mid": [
        "I had a plan. The dungeon had a different plan.",
        "Tell them I made it this far. That should mean something.",
        "I kept thinking of home. That's probably what distracted me.",
        "No regrets. That's not true. Some regrets.",
        "Further than I expected. Not far enough.",
        "The lesson I'm leaving you -- use it better than I did.",
        "I've been reading the bones down here. Now I'm one of them.",
        "Something to the right. I should have gone left.",
    ],
    "default_deep": [
        "This is as far as the blood has taken us. Take it further.",
        "I can hear the dark. I know that doesn't make sense. I can hear it.",
        "We've been coming down here for generations. I wonder why we started.",
        "Go deeper. One of us has to see what's at the bottom.",
        "The deepest this family has ever gone. Bring that with you.",
        "I'm not afraid. I'm surprised by that.",
        "Whatever is below this -- it knows we're coming.",
        "Keep going. I didn't come this far just to stop here.",
    ],
}

# ── Hero intro templates ───────────────────────────────────────────────────────

HERO_INTROS = [
    "You've heard the stories all your life. The dungeon. The family debt. The bottom that no one has reached.",
    "They said you had your {parent_adj} eyes. You hope you have something more useful.",
    "You've been training for this since you could hold a blade. The training didn't cover everything.",
    "You are not the first. You are not the last. You are the one who goes now.",
    "The bones of your ancestors are down there. You will walk past them. Try not to think about that.",
    "Every generation of this family has gone down. Every generation has left something behind.",
    "The dungeon doesn't care who you are. That's almost fair.",
    "You know the family record. You intend to break it.",
    "Your {parent_adj} made it further than anyone. You will go further still.",
    "You've been told the dungeon changes you. You think you might want that.",
    "Others have tried to talk you out of this. They don't understand.",
    "This is not a choice. The family goes down. You are the family now.",
    "You know three things: your name, your inheritance, and where you're going.",
    "The dungeon has taken from this family for generations. You intend to collect.",
]

PARENT_ADJ = ["mother's", "father's", "grandmother's", "grandfather's", "ancestor's",
               "predecessor's", "forebearer's"]

FAMILY_NAMES = [
    "Ashborne", "Duskwall", "Grimholt", "Ironfen", "Mournkeep",
    "Ravenstead", "Stoneward", "Thornwick", "Vaultmere", "Wraithend",
    "Coldmantle", "Greyvane", "Emberholt", "Blackmere", "Dawnless",
]

FIRST_NAMES = [
    "Aldric", "Brynn", "Cael", "Dara", "Edric", "Fyra", "Gorm", "Hael",
    "Ivar", "Jora", "Kael", "Lyra", "Morn", "Nara", "Osric", "Petra",
    "Quell", "Ravn", "Sora", "Tarn", "Ula", "Vael", "Wren", "Xan",
    "Ysel", "Zorn", "Aura", "Brek", "Cora", "Deln", "Erra", "Fen",
]


# ── Narrative generators ──────────────────────────────────────

def get_family_name(dynasty: list[dict]) -> str:
    if dynasty and "family_name" in dynasty[0]:
        return dynasty[0]["family_name"]
    return random.choice(FAMILY_NAMES)


def get_floor_name(floor: int) -> str:
    options = FLOOR_NAMES.get(floor, [f"floor {floor}"])
    return random.choice(options)


def make_name(generation: int, family_name: str) -> str:
    return f"{random.choice(FIRST_NAMES)} {family_name}"


def _floor_tier(floor: int) -> str:
    if floor <= 1:
        return "early"
    if floor >= 4:
        return "deep"
    return "mid"


def make_epitaph(hero: Hero, cause: str, family_name: str, floor_name: str) -> str:
    tier = _floor_tier(hero.floor)
    # trait-based epitaphs ~30% of the time
    if random.random() < 0.3 and hero.trait in TRAIT_EPITAPH:
        template = TRAIT_EPITAPH[hero.trait]
    else:
        template = random.choice(EPITAPH_TEMPLATES[tier])
    return template.format(
        name=hero.name,
        floor_name=floor_name,
        cause=cause,
        family=family_name,
    )


def make_last_words(cause: str, floor: int) -> str:
    key = (cause, floor)
    if key in LAST_WORDS:
        return random.choice(LAST_WORDS[key])
    tier = _floor_tier(floor)
    return random.choice(LAST_WORDS[f"default_{tier}"])


def pick_skill_voice(skill_id: str) -> tuple[str, str]:
    return random.choice(SKILL_VOICE[skill_id])


def make_hero_intro(generation: int, family_name: str, trait: str,
                    inherited_skill: str | None) -> list[str]:
    lines = [f"Generation {generation} of the House of {family_name}.", ""]
    intro = random.choice(HERO_INTROS).replace("{parent_adj}", random.choice(PARENT_ADJ))
    lines.append(intro)
    if trait in TRAIT_INTRO:
        lines.append("")
        lines.append(TRAIT_INTRO[trait])
    if inherited_skill:
        v1, v2 = pick_skill_voice(inherited_skill)
        lines += ["", f'A memory not your own: "{v1}"', f'"{v2}"']
    return lines


def make_chronicle_entry(entry: dict) -> list[str]:
    floor_name = entry.get("floor_name", get_floor_name(entry["floor"]))
    skill_name = SKILLS[entry["skill_id"]]["name"] if entry.get("skill_id") else None
    lines = [f"  {entry['name']}"]
    if entry.get("trait"):
        lines[0] += f"  ({entry['trait']})"
    if entry.get("won"):
        lines.append(f"  Reached the bottom on {floor_name}.")
    else:
        lines.append(f"  Fell to {entry['cause']} on {floor_name}.")
    if entry.get("last_words"):
        lines.append(f'  "{entry["last_words"]}"')
    if skill_name:
        lines.append(f"  Passed down: {skill_name}.")
    lines.append("")
    return lines
