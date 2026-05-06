#!/usr/bin/env python3
"""
LINEAGE -- ASCII Roguelike
Each hero is the child of the last. Find your ancestor's bones. Inherit their final lesson.
"""

import curses
import json
import math
import random
from dataclasses import dataclass, field, asdict
from pathlib import Path

# ── Save paths ─────────────────────────────────────────────────────────────────

SAVE_DIR = Path("~/.lineage").expanduser()
BONES_FILE = SAVE_DIR / "bones.json"
DYNASTY_FILE = SAVE_DIR / "dynasty.json"
SAVE_FILE = SAVE_DIR / "save.json"

MAP_W, MAP_H = 60, 30
MIN_ROOMS, MAX_ROOMS = 6, 12
ROOM_MIN, ROOM_MAX = 4, 10

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


# ── Data classes ───────────────────────────────────────────────────────────────

@dataclass
class Stats:
    max_hp:  int = 20
    attack:  int = 4
    defense: int = 0
    vision:  int = 6
    speed:   int = 1
    dodge:   int = 0


@dataclass
class Hero:
    name:        str
    generation:  int
    trait:       str  = ""
    skills:      list = field(default_factory=list)
    found_items: list = field(default_factory=list)
    inventory:   list = field(default_factory=list)
    equipped:    dict = field(default_factory=lambda: {"weapon": None, "armor": None, "accessory": None})
    stats:       Stats = field(default_factory=Stats)
    hp:          int  = 0
    floor:       int  = 1
    x:           int  = 0
    y:           int  = 0

    def __post_init__(self):
        if not self.trait:
            self.trait = random.choice(HERO_TRAITS)
        if self.hp == 0:
            self.hp = self.stats.max_hp

    def apply_skill(self, skill_id):
        if skill_id not in self.skills:
            self.skills.append(skill_id)
        s = SKILLS[skill_id]
        setattr(self.stats, s["stat"], getattr(self.stats, s["stat"]) + s["val"])
        if s["stat"] == "max_hp":
            self.hp += s["val"]
        if skill_id == "bloodline":
            self.stats.attack += 1

    def equip(self, item_id: str) -> str | None:
        item = ITEMS[item_id]
        slot = item["slot"]
        old_id = self.equipped.get(slot)
        if old_id:
            old = ITEMS[old_id]
            val = old["val"]
            setattr(self.stats, old["stat"], getattr(self.stats, old["stat"]) - val)
            if old["stat"] == "max_hp":
                self.hp = min(self.hp, self.stats.max_hp)
        self.equipped[slot] = item_id
        if item_id in self.inventory:
            self.inventory.remove(item_id)
        setattr(self.stats, item["stat"], getattr(self.stats, item["stat"]) + item["val"])
        if item["stat"] == "max_hp":
            self.hp += item["val"]
        return old_id

    def optimize_gear(self) -> list:
        """Equip the best item per slot from inventory. Skips ambiguous cross-stat comparisons."""
        messages = []
        for slot in ("weapon", "armor", "accessory"):
            candidates = [iid for iid in self.inventory if ITEMS[iid]["slot"] == slot]
            if not candidates:
                continue
            eq_id = self.equipped.get(slot)
            all_ids = candidates + ([eq_id] if eq_id else [])
            if len({ITEMS[iid]["stat"] for iid in all_ids}) > 1:
                continue  # different stats in same slot -- leave it to the player
            best = max(candidates, key=lambda iid: ITEMS[iid]["val"])
            if eq_id and ITEMS[best]["val"] <= ITEMS[eq_id]["val"]:
                continue
            old_id = self.equip(best)
            if old_id:
                self.inventory.append(old_id)
                messages.append(f"Equipped {ITEMS[best]['name']}; {ITEMS[old_id]['name']} to pack.")
            else:
                messages.append(f"Equipped {ITEMS[best]['name']}.")
        return messages or ["Already wearing the best available gear."]

    def use_consumable(self, item_id: str) -> str:
        item = ITEMS[item_id]
        if item_id in self.inventory:
            self.inventory.remove(item_id)
        stat, val = item["stat"], item["val"]
        if stat == "hp":
            healed = min(val, self.stats.max_hp - self.hp)
            self.hp = min(self.hp + val, self.stats.max_hp)
            return f"{item['flavor']} (+{healed} HP)"
        setattr(self.stats, stat, getattr(self.stats, stat) + val)
        return f"{item['flavor']}"


@dataclass
class Enemy:
    name:   str
    glyph:  str
    hp:     int
    attack: int
    xp:     int
    notice: int = 5
    x:      int = 0
    y:      int = 0
    title:  str = ""
    max_hp: int = 0
    alerted: bool = False
    recovering: int = 0
    regen_suppressed: int = 0

    def __post_init__(self):
        if self.max_hp == 0:
            self.max_hp = self.hp

    @property
    def display(self):
        return f"{self.title} the {self.name}" if self.title else f"the {self.name}"

    @property
    def Display(self):
        return f"{self.title} the {self.name}" if self.title else f"The {self.name}"


@dataclass
class Bones:
    hero_name:  str
    generation: int
    floor:      int
    cause:      str
    skill_id:   str
    x:          int
    y:          int
    epitaph:    str
    last_words: str  = ""
    trait:      str  = ""
    relics:     list = field(default_factory=list)


@dataclass
class Item:
    item_id: str
    x:       int
    y:       int


# ── Save / load ────────────────────────────────────────────────────────────────

def ensure_save_dir():
    SAVE_DIR.mkdir(exist_ok=True)


def load_bones() -> list[Bones]:
    if not BONES_FILE.exists():
        return []
    data = json.loads(BONES_FILE.read_text())
    return [Bones(**b) for b in data]


def save_bones(bones_list: list[Bones]):
    ensure_save_dir()
    BONES_FILE.write_text(json.dumps([asdict(b) for b in bones_list], indent=2))


def load_dynasty() -> list[dict]:
    if not DYNASTY_FILE.exists():
        return []
    return json.loads(DYNASTY_FILE.read_text())


def save_dynasty(dynasty: list[dict]):
    ensure_save_dir()
    DYNASTY_FILE.write_text(json.dumps(dynasty, indent=2))


def save_game(game) -> None:
    ensure_save_dir()
    data = {
        "progression_version": 2,
        "hero":               asdict(game.hero),
        "xp":                 game.xp,
        "level":              game.level,
        "turn_meter":         game.turn_meter,
        "family_name":        game.family_name,
        "tiles":              game.tiles,
        "rooms":              [asdict(r) for r in game.rooms],
        "enemies":            [asdict(e) for e in game.enemies],
        "floor_bones":        [asdict(b) for b in game.floor_bones],
        "floor_items":        [asdict(i) for i in game.floor_items],
        "inscriptions":       {f"{k[0]},{k[1]}": v for k, v in game.inscriptions.items()},
        "seen":               list(game.seen),
        "visited_rooms":      list(game.visited_rooms),
        "current_floor_name": game.current_floor_name,
    }
    SAVE_FILE.write_text(json.dumps(data))


def delete_save() -> None:
    if SAVE_FILE.exists():
        SAVE_FILE.unlink()


def delete_all_data() -> None:
    for f in (SAVE_FILE, BONES_FILE, DYNASTY_FILE):
        if f.exists():
            f.unlink()


def delete_lineage_only() -> None:
    """Reset dynasty and save but keep bones -- old heroes' graves remain."""
    for f in (SAVE_FILE, DYNASTY_FILE):
        if f.exists():
            f.unlink()


def level_attack_bonus(level: int) -> int:
    return level // 2


def level_defense_bonus(level: int) -> int:
    return level // 3


def level_max_hp_bonus(level: int) -> int:
    return max(0, level - 1) * 2


def progression_from_total_xp(total_xp: int) -> tuple[int, int]:
    level = 1
    remaining = max(0, total_xp)
    while remaining >= 10 + (level - 1) * 6:
        remaining -= 10 + (level - 1) * 6
        level += 1
    return level, remaining


# ── Narrative generators ───────────────────────────────────────────────────────

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


def make_enemy(kind: tuple, floor: int) -> "Enemy":
    name, glyph, hp, attack, xp, notice = kind
    title = random.choice(ENEMY_NAMES.get(name, [""])) if random.random() < 0.4 else ""
    return Enemy(name, glyph, hp, attack, xp, notice, title=title)


# ── Dungeon generation ─────────────────────────────────────────────────────────

@dataclass
class Rect:
    x: int
    y: int
    w: int
    h: int

    def center(self):
        return self.x + self.w // 2, self.y + self.h // 2

    def intersects(self, other):
        return (self.x < other.x + other.w and self.x + self.w > other.x and
                self.y < other.y + other.h and self.y + self.h > other.y)


def generate_dungeon(floor: int, bones_list: list[Bones]) -> tuple:
    tiles = [["#"] * MAP_W for _ in range(MAP_H)]
    rooms: list[Rect] = []
    num_rooms = random.randint(MIN_ROOMS, MAX_ROOMS)

    for _ in range(200):
        w = random.randint(ROOM_MIN, ROOM_MAX)
        h = random.randint(ROOM_MIN, ROOM_MAX)
        x = random.randint(1, MAP_W - w - 1)
        y = random.randint(1, MAP_H - h - 1)
        room = Rect(x, y, w, h)
        if any(room.intersects(r) for r in rooms):
            continue
        for ry in range(room.y, room.y + room.h):
            for rx in range(room.x, room.x + room.w):
                tiles[ry][rx] = "."
        if rooms:
            px, py = rooms[-1].center()
            cx, cy = room.center()
            if random.random() < 0.5:
                for rx in range(min(px, cx), max(px, cx) + 1):
                    tiles[py][rx] = "."
                for ry in range(min(py, cy), max(py, cy) + 1):
                    tiles[ry][cx] = "."
            else:
                for ry in range(min(py, cy), max(py, cy) + 1):
                    tiles[ry][px] = "."
                for rx in range(min(px, cx), max(px, cx) + 1):
                    tiles[cy][rx] = "."
        rooms.append(room)
        if len(rooms) >= num_rooms:
            break

    stair_room = rooms[-1]
    sx, sy = stair_room.center()
    tiles[sy][sx] = ">"

    def room_inner(room):
        return [(x, y)
                for x in range(room.x + 1, room.x + room.w - 1)
                for y in range(room.y + 1, room.y + room.h - 1)]

    def pick_empty(room, occupied):
        choices = [p for p in room_inner(room) if p not in occupied]
        return random.choice(choices) if choices else None

    occupied: set[tuple[int, int]] = {(sx, sy)}

    enemies = []
    pool = FLOOR_ENEMIES.get(min(floor, 5), FLOOR_ENEMIES[5])
    for room in rooms[1:]:
        if random.random() < 0.7:
            pos = pick_empty(room, occupied)
            if pos:
                e = make_enemy(random.choice(pool), floor)
                e.x, e.y = pos
                enemies.append(e)
                occupied.add(pos)

    floor_bones = [b for b in bones_list if b.floor == floor]
    placed_bones = []
    for b in floor_bones:
        if 0 < b.x < MAP_W and 0 < b.y < MAP_H and tiles[b.y][b.x] != "#" and (b.x, b.y) not in occupied:
            placed_bones.append(b)
            occupied.add((b.x, b.y))
        elif rooms:
            r = random.choice(rooms)
            pos = pick_empty(r, occupied)
            if pos:
                b.x, b.y = pos
                placed_bones.append(b)
                occupied.add(pos)

    # Room inscriptions: ~25% of rooms past the first get a flavor event
    inscriptions: dict[tuple, str] = {}
    for room in rooms[1:]:
        if random.random() < 0.25:
            cx, cy = room.center()
            inscriptions[(cx, cy)] = random.choice(ROOM_INSCRIPTIONS)

    # Place items: most rooms get at least one item; bigger rooms get more
    floor_items: list[Item] = []
    item_pool = FLOOR_ITEMS.get(min(floor, 5), FLOOR_ITEMS[5])

    def place_item(room):
        pos = pick_empty(room, occupied)
        if pos:
            floor_items.append(Item(random.choice(item_pool), pos[0], pos[1]))
            occupied.add(pos)

    for room in rooms[1:]:
        if random.random() < 0.65:
            place_item(room)
        # Larger rooms (6x6+) get a second item 40% of the time
        if room.w >= 6 and room.h >= 6 and random.random() < 0.4:
            place_item(room)
        # Rare treasure room: 15% chance of a third item regardless of size
        if random.random() < 0.15:
            place_item(room)

    # Guarantee at least 4 items per floor
    while len(floor_items) < 4 and rooms[1:]:
        place_item(random.choice(rooms[1:]))

    start = rooms[0].center()
    return tiles, rooms, enemies, placed_bones, floor_items, inscriptions, start


# ── FOV ───────────────────────────────────────────────────────────────────────

def compute_fov(tiles, px, py, radius) -> set:
    visible = set()
    for angle_step in range(360):
        angle = angle_step * math.pi / 180
        rx, ry = float(px), float(py)
        dx = 0.001 + 0.5 * math.cos(angle)
        dy = 0.5 * math.sin(angle)
        for _ in range(radius):
            rx += dx
            ry += dy
            ix, iy = int(rx), int(ry)
            if ix < 0 or ix >= MAP_W or iy < 0 or iy >= MAP_H:
                break
            visible.add((ix, iy))
            if tiles[iy][ix] == "#":
                break
    return visible


# ── UI helpers ────────────────────────────────────────────────────────────────

def wrap(text: str, width: int) -> list[str]:
    if not text:
        return [""]
    words = text.split()
    lines, cur = [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur:
        lines.append(cur)
    return lines or [""]


def draw_box(stdscr, y, x, h, w, title=""):
    try:
        stdscr.addch(y, x, curses.ACS_ULCORNER)
        stdscr.addch(y, x + w - 1, curses.ACS_URCORNER)
        stdscr.addch(y + h - 1, x, curses.ACS_LLCORNER)
        stdscr.addch(y + h - 1, x + w - 1, curses.ACS_LRCORNER)
        for i in range(1, w - 1):
            stdscr.addch(y, x + i, curses.ACS_HLINE)
            stdscr.addch(y + h - 1, x + i, curses.ACS_HLINE)
        for i in range(1, h - 1):
            stdscr.addch(y + i, x, curses.ACS_VLINE)
            stdscr.addch(y + i, x + w - 1, curses.ACS_VLINE)
        if title:
            label = f" {title} "
            stdscr.addstr(y, x + (w - len(label)) // 2, label, curses.color_pair(3))
    except curses.error:
        pass


# ── Game state ────────────────────────────────────────────────────────────────

class Game:
    def __init__(self, stdscr, hero: Hero, bones_list: list[Bones],
                 dynasty: list[dict], family_name: str):
        self.stdscr = stdscr
        self.hero = hero
        self.bones_list = bones_list
        self.dynasty = dynasty
        self.family_name = family_name
        self.messages: list[str] = []
        self.seen: set = set()
        self.visited_rooms: set = set()
        self.autoexplore: bool = False
        self.xp = 0
        self.level = 1
        self.turn_meter = 0
        self.load_floor(hero.floor)

    def load_floor(self, floor_num: int):
        self.hero.floor = floor_num
        self.seen = set()
        self.visited_rooms = set()
        self.tiles, self.rooms, self.enemies, self.floor_bones, self.floor_items, self.inscriptions, start = \
            generate_dungeon(floor_num, self.bones_list)
        self.hero.x, self.hero.y = start
        self.current_floor_name = get_floor_name(floor_num)
        self.msg(f"-- {self.current_floor_name} --")
        arrival = random.choice(FLOOR_ARRIVAL.get(floor_num, ["The dark deepens."]))
        self.msg(arrival)
        if self.dynasty:
            fallen_here = [e for e in self.dynasty if e["floor"] == floor_num and not e.get("won")]
            if fallen_here:
                a = random.choice(fallen_here)
                self.msg(f"{a['name']} died here. Their bones are somewhere in these halls.")
            elif floor_num > max(e["floor"] for e in self.dynasty):
                self.msg(f"No one in your family has reached this far.")

    def msg(self, text: str):
        self.messages.append(text)
        if len(self.messages) > 5:
            self.messages.pop(0)

    def xp_to_next_level(self) -> int:
        return 10 + (self.level - 1) * 6

    def _carry_weight(self) -> int:
        inv_w = sum(ITEMS[iid]["weight"] for iid in self.hero.inventory)
        eq_w  = sum(ITEMS[iid]["weight"] for iid in self.hero.equipped.values() if iid)
        return inv_w + eq_w

    def _max_carry(self) -> int:
        return CARRY_MAX

    def gain_xp(self, amount: int) -> None:
        self.xp += amount
        leveled = False
        while self.xp >= self.xp_to_next_level():
            self.xp -= self.xp_to_next_level()
            self.level += 1
            self.hero.stats.max_hp += level_max_hp_bonus(self.level) - level_max_hp_bonus(self.level - 1)
            self.hero.hp += level_max_hp_bonus(self.level) - level_max_hp_bonus(self.level - 1)
            self.hero.stats.attack += level_attack_bonus(self.level) - level_attack_bonus(self.level - 1)
            self.hero.stats.defense += level_defense_bonus(self.level) - level_defense_bonus(self.level - 1)
            self.msg(f"You grow stronger. Level {self.level}.")
            leveled = True
        if leveled and self.dynasty and random.random() < 0.40:
            a = random.choice(self.dynasty)
            self.msg(random.choice(ANCESTOR_LEVEL_MSGS).format(
                ancestor=a["name"], floor=a["floor"]))

    def advance_world(self) -> None:
        speed_bonus = max(0, self.hero.stats.speed - 1)
        if speed_bonus:
            self.turn_meter += speed_bonus
        if self.turn_meter >= 4:
            self.turn_meter -= 4
            self.msg("You keep the initiative.")
            return
        self.enemy_turns()

    def enemy_notice_radius(self, enemy: Enemy) -> int:
        penalty = 1 if "quiet_step" in self.hero.skills else 0
        return max(1, enemy.notice - penalty)

    def draw(self):
        self.stdscr.clear()
        h, w = self.stdscr.getmaxyx()
        fov = compute_fov(self.tiles, self.hero.x, self.hero.y, self.hero.stats.vision)
        self.seen |= fov

        for y in range(min(MAP_H, h - 8)):
            for x in range(min(MAP_W, w - 1)):
                ch = self.tiles[y][x]
                pos = (x, y)
                if pos in fov:
                    if ch == "#":
                        attr = curses.color_pair(1)
                    elif ch == ">":
                        attr = curses.color_pair(3) | curses.A_BOLD
                    else:
                        attr = curses.color_pair(2)
                    self.stdscr.addch(y, x, ch, attr)
                elif pos in self.seen:
                    self.stdscr.addch(y, x, ch, curses.color_pair(1) | curses.A_DIM)

        for it in self.floor_items:
            if (it.x, it.y) in fov:
                glyph = ITEMS[it.item_id]["glyph"]
                self.stdscr.addch(it.y, it.x, glyph, curses.color_pair(6) | curses.A_BOLD)

        for b in self.floor_bones:
            if (b.x, b.y) in fov:
                self.stdscr.addch(b.y, b.x, "%", curses.color_pair(5) | curses.A_BOLD)

        for e in self.enemies:
            if (e.x, e.y) in fov:
                self.stdscr.addch(e.y, e.x, e.glyph, curses.color_pair(4) | curses.A_BOLD)

        self.stdscr.addch(self.hero.y, self.hero.x, "@", curses.color_pair(3) | curses.A_BOLD)

        hud_y = MAP_H + 1
        skill_str = ", ".join(SKILLS[s]["name"] for s in self.hero.skills) or "none"
        self.stdscr.addstr(hud_y, 0,
            f"  {self.hero.name}  ({self.hero.trait})  |  Gen {self.hero.generation}  |  "
            f"HP {self.hero.hp}/{self.hero.stats.max_hp}  |  Lvl {self.level}  |  "
            f"{self.current_floor_name}  |  XP {self.xp}/{self.xp_to_next_level()}",
            curses.color_pair(3))

        eq_parts = []
        for slot in ("weapon", "armor", "accessory"):
            eid = self.hero.equipped.get(slot)
            if eid:
                eq_parts.append(f"[{ITEMS[eid]['name']}]")
        eq_str = "  ".join(eq_parts) if eq_parts else "nothing equipped"
        self.stdscr.addstr(hud_y + 1, 0,
            f"  {eq_str}  ({self._carry_weight()}/{self._max_carry()} lbs)", curses.color_pair(6))
        self.stdscr.addstr(hud_y + 2, 0, f"  {skill_str}", curses.color_pair(2))

        for i, m in enumerate(self.messages[-3:]):
            self.stdscr.addstr(hud_y + 4 + i, 0, f"  {m}", curses.color_pair(2))

        sx = MAP_W + 2
        ae_indicator = " [AUTO]" if self.autoexplore else ""
        self.stdscr.addstr(0,  sx, f"LINEAGE{ae_indicator}",   curses.color_pair(3) | curses.A_BOLD)
        self.stdscr.addstr(1,  sx, f"House of {self.family_name}", curses.color_pair(2))
        self.stdscr.addstr(3,  sx, "hjkl/arrows move",     curses.color_pair(1))
        self.stdscr.addstr(4,  sx, "i  inventory",         curses.color_pair(1))
        self.stdscr.addstr(5,  sx, "o  autoexplore",       curses.color_pair(1))
        self.stdscr.addstr(6,  sx, ".  wait",              curses.color_pair(1))
        self.stdscr.addstr(7,  sx, "r  rest until full",   curses.color_pair(1))
        self.stdscr.addstr(8,  sx, "g  examine bones",     curses.color_pair(1))
        self.stdscr.addstr(9,  sx, "d  chronicle",         curses.color_pair(1))
        self.stdscr.addstr(10, sx, "z  optimize gear",     curses.color_pair(1))
        self.stdscr.addstr(11, sx, "q  quit",              curses.color_pair(1))
        self.stdscr.addstr(12, sx, "!  item",              curses.color_pair(6))
        self.stdscr.addstr(13, sx, "%  ancestor",          curses.color_pair(5))
        self.stdscr.addstr(14, sx, ">  descend",           curses.color_pair(3))
        self.stdscr.refresh()

    def try_move(self, dx, dy):
        nx, ny = self.hero.x + dx, self.hero.y + dy
        if nx < 0 or nx >= MAP_W or ny < 0 or ny >= MAP_H:
            return
        if self.tiles[ny][nx] == "#":
            return

        for e in self.enemies:
            if e.x == nx and e.y == ny:
                self.do_combat(e)
                self.advance_world()
                return

        self.hero.x, self.hero.y = nx, ny

        if self.tiles[ny][nx] == ">":
            if self.hero.floor >= 5:
                self.show_win_screen()
                return
            self.load_floor(self.hero.floor + 1)
            return

        # Room inscription on first visit
        for room in self.rooms:
            cx, cy = room.center()
            if (cx, cy) not in self.visited_rooms:
                if room.x <= nx < room.x + room.w and room.y <= ny < room.y + room.h:
                    self.visited_rooms.add((cx, cy))
                    if (cx, cy) in self.inscriptions:
                        self.msg(self.inscriptions[(cx, cy)])

        for b in self.floor_bones:
            if b.x == self.hero.x and b.y == self.hero.y:
                self.msg(f"The bones of {b.hero_name} lie here. Press g.")

        # Pick up items underfoot
        for it in list(self.floor_items):
            if it.x == self.hero.x and it.y == self.hero.y:
                item_w = ITEMS[it.item_id]["weight"]
                if self._carry_weight() + item_w > self._max_carry():
                    self.msg(f"Too heavy to carry the {ITEMS[it.item_id]['name']}.")
                else:
                    self.hero.inventory.append(it.item_id)
                    self.hero.found_items.append(it.item_id)
                    name = ITEMS[it.item_id]["name"]
                    self.msg(f"You pick up {name}. [i] to use.")
                    self.floor_items.remove(it)

        self.advance_world()

    def do_combat(self, enemy: Enemy):
        opening_strike = "killing_blow" in self.hero.skills and enemy.hp == enemy.max_hp
        dmg = max(0, self.hero.stats.attack - random.randint(0, 1))
        enemy.hp -= dmg
        hit_msg = random.choice(PLAYER_HIT).format(enemy=enemy.display)
        self.msg(f"{hit_msg} ({dmg} dmg, {max(0, enemy.hp)} HP left)")
        if enemy.hp <= 0:
            kill_msg = random.choice(PLAYER_KILL).format(enemy=enemy.Display)
            self.msg(f"{kill_msg} (+{enemy.xp} XP)")
            self.gain_xp(enemy.xp)
            self.enemies.remove(enemy)
            if random.random() < 0.40:
                pool = FLOOR_ITEMS.get(min(self.hero.floor, 5), FLOOR_ITEMS[5])
                self.floor_items.append(Item(random.choice(pool), enemy.x, enemy.y))
            if self.dynasty and random.random() < 0.25:
                victims = [e for e in self.dynasty
                           if e.get("cause") and enemy.name in e["cause"] and not e.get("won")]
                if victims:
                    a = random.choice(victims)
                    self.msg(random.choice(ANCESTOR_KILL_MSGS).format(
                        ancestor=a["name"], enemy=enemy.display))
            return
        enemy.alerted = True
        if enemy.name == "troll":
            enemy.regen_suppressed = 2
        if opening_strike and enemy.name != "zombie":
            enemy.recovering = max(enemy.recovering, 1)
            self.msg(f"{enemy.Display} reels before it can answer.")
        elif opening_strike:
            self.msg(f"{enemy.Display} barely registers the blow and keeps coming.")

    def enemy_turns(self):
        px, py = self.hero.x, self.hero.y
        for e in list(self.enemies):
            if not e.alerted:
                radius = self.enemy_notice_radius(e)
                if max(abs(e.x - px), abs(e.y - py)) > radius:
                    continue
                enemy_fov = compute_fov(self.tiles, e.x, e.y, radius)
                if (px, py) not in enemy_fov:
                    continue
                e.alerted = True
                self.msg(random.choice(ENEMY_SPOT).format(enemy=e.Display))

            # Troll: regenerate when not recently hit
            if e.name == "troll":
                if e.regen_suppressed > 0:
                    e.regen_suppressed -= 1
                elif e.hp < e.max_hp:
                    e.hp = min(e.hp + 2, e.max_hp)
                    self.msg(f"{e.Display} knits itself back together.")

            if e.recovering > 0:
                e.recovering -= 1
                continue

            dist = max(abs(e.x - px), abs(e.y - py))

            # Rat: hesitate 30% of the time when not adjacent
            if e.name == "rat" and dist > 1 and random.random() < 0.30:
                continue

            # Goblin: flee at low HP
            if e.name == "goblin" and e.hp <= e.max_hp // 4:
                dx_away = 0 if e.x == px else (-1 if e.x < px else 1)
                dy_away = 0 if e.y == py else (-1 if e.y < py else 1)
                fx, fy = e.x + dx_away, e.y + dy_away
                if (0 <= fx < MAP_W and 0 <= fy < MAP_H and
                        self.tiles[fy][fx] != "#" and
                        not any(o.x == fx and o.y == fy for o in self.enemies)):
                    e.x, e.y = fx, fy
                continue

            # Dark elf: ranged attack from distance, retreats when adjacent
            if e.name == "dark_elf":
                if dist > 1:
                    elf_fov = compute_fov(self.tiles, e.x, e.y, 4)
                    if (px, py) in elf_fov:
                        if random.randint(1, 100) <= self.hero.stats.dodge:
                            self.msg(random.choice(ENEMY_MISS).format(enemy=e.Display))
                            continue
                        dmg = max(0, (e.attack - 1) - self.hero.stats.defense)
                        self.hero.hp -= dmg
                        self.msg(f"A bolt from {e.display} finds you. ({dmg} dmg)")
                        if self.hero.hp <= 0:
                            self.hero_dies(e.title if e.title else f"a {e.name}")
                            return
                        continue
                elif dist == 1:
                    dx_away = 0 if e.x == px else (-1 if e.x < px else 1)
                    dy_away = 0 if e.y == py else (-1 if e.y < py else 1)
                    fx, fy = e.x + dx_away, e.y + dy_away
                    if (0 <= fx < MAP_W and 0 <= fy < MAP_H and
                            self.tiles[fy][fx] != "#" and
                            not any(o.x == fx and o.y == fy for o in self.enemies)):
                        e.x, e.y = fx, fy
                        continue
                    # Cornered -- fall through to melee

            # Standard move-toward-player or melee
            dx = 0 if e.x == px else (1 if e.x < px else -1)
            dy = 0 if e.y == py else (1 if e.y < py else -1)
            nx, ny = e.x + dx, e.y + dy

            if nx == px and ny == py:
                # Kobold pack bonus
                pack_bonus = 0
                if e.name == "kobold":
                    pack_bonus = sum(
                        1 for o in self.enemies
                        if o is not e and o.alerted
                        and max(abs(o.x - e.x), abs(o.y - e.y)) <= 3
                    )

                if random.randint(1, 100) <= self.hero.stats.dodge:
                    self.msg(random.choice(ENEMY_MISS).format(enemy=e.Display))
                    continue

                effective_attack = e.attack + pack_bonus
                dmg = max(0, effective_attack - self.hero.stats.defense)
                self.hero.hp -= dmg
                hit_msg = random.choice(ENEMY_HIT).format(enemy=e.Display)
                suffix = " (pack!)" if pack_bonus else ""
                self.msg(f"{hit_msg} ({dmg} dmg){suffix}")
                if self.hero.hp <= 0:
                    self.hero_dies(e.title if e.title else f"a {e.name}")
                    return
            elif (self.tiles[ny][nx] != "#" and
                  not any(o.x == nx and o.y == ny for o in self.enemies)):
                e.x, e.y = nx, ny

    def hero_dies(self, cause: str):
        passed_skill = self.hero.skills[-1] if self.hero.skills else random.choice(list(SKILLS.keys()))
        floor_name = self.current_floor_name
        epitaph    = make_epitaph(self.hero, cause, self.family_name, floor_name)
        last_words = make_last_words(cause.lstrip("a "), self.hero.floor)

        bone = Bones(
            hero_name=self.hero.name,
            generation=self.hero.generation,
            floor=self.hero.floor,
            cause=cause,
            skill_id=passed_skill,
            x=self.hero.x,
            y=self.hero.y,
            epitaph=epitaph,
            last_words=last_words,
            trait=self.hero.trait,
            relics=[iid for iid in self.hero.equipped.values() if iid],
        )
        self.bones_list.append(bone)
        save_bones(self.bones_list)
        delete_save()

        self.dynasty.append({
            "name":        self.hero.name,
            "generation":  self.hero.generation,
            "floor":       self.hero.floor,
            "floor_name":  floor_name,
            "cause":       cause,
            "epitaph":     epitaph,
            "last_words":  last_words,
            "skill_id":    passed_skill,
            "trait":       self.hero.trait,
            "family_name": self.family_name,
        })
        save_dynasty(self.dynasty)

        self.show_death_screen(bone, passed_skill)

    def examine_bones(self):
        for b in self.floor_bones:
            if b.x == self.hero.x and b.y == self.hero.y:
                self.show_bones_screen(b)
                return
        self.msg("Nothing to examine here.")

    def show_bones_screen(self, b: Bones):
        LETTERS = "abcdef"
        self.stdscr.clear()
        box_w = 58
        draw_box(self.stdscr, 1, 3, 26, box_w, "Ancestor's Remains")
        y, x = 3, 6

        for line in wrap(b.epitaph, box_w - 6):
            self.stdscr.addstr(y, x, line, curses.color_pair(2)); y += 1

        if b.last_words:
            y += 1
            for line in wrap(f'"{b.last_words}"', box_w - 6):
                self.stdscr.addstr(y, x, line, curses.color_pair(1) | curses.A_ITALIC); y += 1

        y += 1
        skill = SKILLS[b.skill_id]
        self.stdscr.addstr(y, x, f"Their lesson: {skill['name']}", curses.color_pair(3) | curses.A_BOLD)
        y += 1
        v1, v2 = pick_skill_voice(b.skill_id)
        for line in wrap(v1, box_w - 6):
            self.stdscr.addstr(y, x, line, curses.color_pair(2)); y += 1
        for line in wrap(v2, box_w - 6):
            self.stdscr.addstr(y, x, line, curses.color_pair(2)); y += 1

        relic_ids = [iid for iid in b.relics if iid in ITEMS]
        if relic_ids:
            y += 1
            self.stdscr.addstr(y, x, "They left something behind:",
                               curses.color_pair(6) | curses.A_BOLD); y += 1
            for i, iid in enumerate(relic_ids[:len(LETTERS)]):
                item = ITEMS[iid]
                self.stdscr.addstr(y, x,
                    f"  {LETTERS[i]})  {item['glyph']} {item['name']}  --  {item['flavor']}",
                    curses.color_pair(6)); y += 1

        if relic_ids:
            self.stdscr.addstr(25, x, "letter to take a relic    any other key to leave",
                               curses.color_pair(1))
        else:
            self.stdscr.addstr(25, x, "[ any key ]", curses.color_pair(1))
        self.stdscr.refresh()

        k = self.stdscr.getch()
        if relic_ids and 0 <= k < 256:
            idx = LETTERS.find(chr(k).lower())
            if 0 <= idx < len(relic_ids):
                iid = relic_ids[idx]
                if self._carry_weight() + ITEMS[iid]["weight"] > self._max_carry():
                    self.msg("Too heavy to carry.")
                else:
                    self.hero.inventory.append(iid)
                    self.hero.found_items.append(iid)
                    b.relics.remove(iid)
                    save_bones(self.bones_list)
                    self.msg(f"You take {ITEMS[iid]['name']} from the remains.")

    def show_death_screen(self, bone: Bones, skill_id: str):
        self.stdscr.clear()
        box_w = 58
        draw_box(self.stdscr, 1, 3, 24, box_w, "You Have Fallen")
        skill = SKILLS[skill_id]
        y, x = 3, 6

        for line in wrap(bone.epitaph, box_w - 6):
            self.stdscr.addstr(y, x, line, curses.color_pair(2)); y += 1

        y += 1
        self.stdscr.addstr(y, x, "Your final words:", curses.color_pair(1)); y += 1
        for line in wrap(f'"{bone.last_words}"', box_w - 6):
            self.stdscr.addstr(y, x, line, curses.color_pair(2) | curses.A_ITALIC); y += 1

        y += 1
        self.stdscr.addstr(y, x, f"Your heir will carry: {skill['name']}",
                           curses.color_pair(3) | curses.A_BOLD); y += 1
        v1, v2 = pick_skill_voice(skill_id)
        for line in wrap(v1, box_w - 6):
            self.stdscr.addstr(y, x, line, curses.color_pair(2)); y += 1
        for line in wrap(v2, box_w - 6):
            self.stdscr.addstr(y, x, line, curses.color_pair(2)); y += 1

        y += 1
        self.stdscr.addstr(y,   x, "[ ENTER ]  continue the lineage", curses.color_pair(1))
        self.stdscr.addstr(y+1, x, "[ q     ]  end here",             curses.color_pair(1))
        self.stdscr.refresh()

        while True:
            k = self.stdscr.getch()
            if k in (10, 13):
                self.start_new_generation(bone)
                return
            elif k in (ord("q"), ord("Q")):
                raise SystemExit

    def show_win_screen(self):
        self.stdscr.clear()
        box_w = 58
        draw_box(self.stdscr, 1, 3, 26, box_w, f"The House of {self.family_name}")
        y, x = 3, 6
        gen_count = self.hero.generation
        for line in wrap(
            f"{self.hero.name}, Generation {gen_count}, has reached the bottom.",
            box_w - 6,
        ):
            self.stdscr.addstr(y, x, line, curses.color_pair(3) | curses.A_BOLD)
            y += 1
        y += 1
        for line in WIN_LINES:
            for wrapped in wrap(line, box_w - 6):
                self.stdscr.addstr(y, x, wrapped, curses.color_pair(2))
                y += 1
        y += 1
        count_str = f"It took {gen_count} generation{'s' if gen_count != 1 else ''}."
        self.stdscr.addstr(y, x, count_str, curses.color_pair(1))
        y += 2
        self.stdscr.addstr(y,   x, "[ ENTER ]  continue the lineage", curses.color_pair(1))
        self.stdscr.addstr(y+1, x, "[ q     ]  end the chronicle",    curses.color_pair(1))
        self.stdscr.refresh()

        skill_id = self.hero.skills[-1] if self.hero.skills else random.choice(list(SKILLS.keys()))
        bone = Bones(
            hero_name=self.hero.name,
            generation=self.hero.generation,
            floor=self.hero.floor,
            cause="reached the bottom",
            skill_id=skill_id,
            x=self.hero.x,
            y=self.hero.y,
            epitaph=f"{self.hero.name}, who reached the end of the lineage.",
            last_words="I made it.",
            trait=self.hero.trait,
            relics=[iid for iid in self.hero.equipped.values() if iid],
        )
        self.bones_list.append(bone)
        save_bones(self.bones_list)
        self.dynasty.append({
            "name":        self.hero.name,
            "generation":  self.hero.generation,
            "floor":       self.hero.floor,
            "floor_name":  self.current_floor_name,
            "cause":       "reached the bottom",
            "epitaph":     bone.epitaph,
            "last_words":  "I made it.",
            "skill_id":    skill_id,
            "trait":       self.hero.trait,
            "family_name": self.family_name,
            "won":         True,
        })
        save_dynasty(self.dynasty)
        delete_save()

        while True:
            k = self.stdscr.getch()
            if k in (10, 13):
                self.start_new_generation(bone)
                return
            elif k in (ord("q"), ord("Q")):
                raise SystemExit

    def _select_bloodline_skills(self, hero: Hero, gen: int) -> list[str]:
        """Return extra skills inherited from dynasty ancestors at gen 3+ (1 extra) and gen 6+ (2 extra)."""
        if gen < 3 or not self.dynasty:
            return []
        slots = 2 if gen >= 6 else 1
        seen = set(hero.skills)
        candidates = sorted(
            (e for e in self.dynasty if e.get("skill_id")),
            key=lambda e: e["floor"],
            reverse=True,
        )
        result = []
        for entry in candidates:
            sid = entry["skill_id"]
            if sid not in seen:
                result.append(sid)
                seen.add(sid)
                if len(result) >= slots:
                    break
        return result

    def start_new_generation(self, parent_bone: Bones):
        new_name = make_name(parent_bone.generation + 1, self.family_name)
        new_hero = Hero(name=new_name, generation=parent_bone.generation + 1)
        new_hero.apply_skill(parent_bone.skill_id)
        bloodline = self._select_bloodline_skills(new_hero, new_hero.generation)
        for sid in bloodline:
            new_hero.apply_skill(sid)
        self.hero = new_hero
        self.seen = set()
        self.visited_rooms = set()
        self.xp = 0
        self.level = 1
        self.turn_meter = 0
        self._show_intro_screen(new_hero, parent_bone.skill_id, bloodline)
        self.load_floor(1)

    def _show_intro_screen(self, hero: Hero, inherited_skill: str | None,
                           bloodline: list | None = None):
        self.stdscr.clear()
        box_w = 58
        draw_box(self.stdscr, 1, 3, 26, box_w, f"Generation {hero.generation}")
        y, x = 3, 6
        for line in make_hero_intro(hero.generation, self.family_name, hero.trait, inherited_skill):
            for wrapped in wrap(line, box_w - 6):
                self.stdscr.addstr(y, x, wrapped, curses.color_pair(2)); y += 1

        if bloodline:
            y += 1
            self.stdscr.addstr(y, x, "Bloodline memory:", curses.color_pair(3) | curses.A_BOLD); y += 1
            for sid in bloodline:
                s = SKILLS[sid]
                self.stdscr.addstr(y, x, f"  {s['name']}  --  {s['desc']}", curses.color_pair(6)); y += 1

        if self.dynasty:
            deepest = max(e["floor"] for e in self.dynasty)
            winners = [e for e in self.dynasty if e.get("won")]
            y += 1
            if winners:
                self.stdscr.addstr(y, x,
                    f"One of your blood has reached the bottom. You carry that knowledge.",
                    curses.color_pair(5)); y += 1
            else:
                souls = len(self.dynasty)
                self.stdscr.addstr(y, x,
                    f"House of {self.family_name}: {souls} soul{'s' if souls != 1 else ''} sent. "
                    f"Deepest: floor {deepest}.",
                    curses.color_pair(1)); y += 1

        self.stdscr.addstr(25, x, "[ ENTER ]  descend", curses.color_pair(1))
        self.stdscr.refresh()
        while self.stdscr.getch() not in (10, 13):
            pass

    def show_inventory(self):
        LETTERS = "abcdefghijklmnopqrstuvwxyz"
        drop_mode = False
        while True:
            self.stdscr.clear()
            box_w = 58
            title = "Inventory -- DROP MODE (press letter)" if drop_mode else "Inventory"
            draw_box(self.stdscr, 0, 3, 28, box_w, title)
            y, x = 2, 6

            self.stdscr.addstr(y, x, "Equipped", curses.color_pair(3) | curses.A_BOLD)
            y += 1
            for slot, label in (("weapon", "Weapon"), ("armor", "Armor"), ("accessory", "Accessory")):
                eid = self.hero.equipped.get(slot)
                if eid:
                    item = ITEMS[eid]
                    self.stdscr.addstr(y, x,
                        f"  {label:<10} {item['name']:<20} +{item['val']} {item['stat']:<8} {item['weight']}lb",
                        curses.color_pair(6))
                else:
                    self.stdscr.addstr(y, x, f"  {label:<10} --", curses.color_pair(1) | curses.A_DIM)
                y += 1

            y += 1
            inv = self.hero.inventory
            cw, mw = self._carry_weight(), self._max_carry()
            self.stdscr.addstr(y, x, f"Pack  ({cw}/{mw} lbs)",
                               curses.color_pair(3) | curses.A_BOLD)
            y += 1

            # Stack consumables; show equipment individually
            display_items: list[tuple[str, int]] = []
            seen_consumable: dict[str, int] = {}
            for iid in inv:
                if ITEMS[iid]["slot"] == "consumable" and iid in seen_consumable:
                    di = seen_consumable[iid]
                    display_items[di] = (display_items[di][0], display_items[di][1] + 1)
                else:
                    if ITEMS[iid]["slot"] == "consumable":
                        seen_consumable[iid] = len(display_items)
                    display_items.append((iid, 1))

            if not display_items:
                self.stdscr.addstr(y, x, "  (empty)", curses.color_pair(1) | curses.A_DIM)
                y += 1
            for i, (item_id, count) in enumerate(display_items[:20]):
                item = ITEMS[item_id]
                letter = LETTERS[i]
                count_pfx = f"x{count} " if count > 1 else "   "
                if item["slot"] == "consumable":
                    stat_str = f"heals {item['val']} HP" if item["stat"] == "hp" else f"+{item['val']} {item['stat']}"
                    kind = "use"
                else:
                    stat_str = f"+{item['val']} {item['stat']}"
                    kind = item["slot"]
                w = item["weight"] * count
                color = curses.color_pair(4) if drop_mode else curses.color_pair(2)
                self.stdscr.addstr(y, x,
                    f"  {letter})  {item['glyph']} {count_pfx}{item['name']:<18} {stat_str:<13} [{kind}] {w}lb",
                    color)
                y += 1

            if drop_mode:
                self.stdscr.addstr(26, x, "letter to drop    ESC to cancel", curses.color_pair(4))
            else:
                self.stdscr.addstr(26, x, "letter to equip/use    d to drop    ESC to close",
                                   curses.color_pair(1))
            self.stdscr.refresh()

            k = self.stdscr.getch()
            if k == 27:
                if drop_mode:
                    drop_mode = False
                    continue
                break
            if k in (ord("i"),) and not drop_mode:
                break
            if 0 <= k < 256:
                ch = chr(k).lower()
                if ch == "d" and not drop_mode:
                    drop_mode = True
                    continue
                if ch in LETTERS:
                    idx = LETTERS.index(ch)
                    if idx < len(display_items):
                        item_id, count = display_items[idx]
                        item = ITEMS[item_id]
                        if drop_mode:
                            self.hero.inventory.remove(item_id)
                            self.floor_items.append(Item(item_id, self.hero.x, self.hero.y))
                            self.msg(f"You drop the {item['name']}.")
                            drop_mode = False
                        elif item["slot"] == "consumable":
                            result = self.hero.use_consumable(item_id)
                            self.msg(f"{item['name']}: {result}")
                        else:
                            old_id = self.hero.equip(item_id)
                            self.msg(f"Equipped {item['name']}.")
                            if old_id:
                                self.hero.inventory.append(old_id)
                                self.msg(f"Unequipped {ITEMS[old_id]['name']}.")

    def show_dynasty(self):
        self.stdscr.clear()
        box_w = 62
        draw_box(self.stdscr, 0, 1, 28, box_w,
                 f"The Chronicle of House {self.family_name}")
        y = 2
        for entry in self.dynasty[-12:]:
            for line in make_chronicle_entry(entry):
                if y >= 26:
                    break
                self.stdscr.addstr(y, 4, line, curses.color_pair(2))
                y += 1
            if y >= 26:
                break
        self.stdscr.addstr(27, 4, "[ any key ]", curses.color_pair(1))
        self.stdscr.refresh()
        self.stdscr.getch()

    def wait_turn(self):
        self.msg("You wait.")
        self.advance_world()

    def rest_until_full(self):
        fov = compute_fov(self.tiles, self.hero.x, self.hero.y, self.hero.stats.vision)
        if any((e.x, e.y) in fov for e in self.enemies):
            self.msg("You can't rest with enemies nearby.")
            return
        if self.hero.hp >= self.hero.stats.max_hp:
            self.msg("You are already at full health.")
            return
        starting_gen = self.hero.generation
        healed = 0
        while self.hero.hp < self.hero.stats.max_hp:
            self.hero.hp = min(self.hero.hp + 1, self.hero.stats.max_hp)
            healed += 1
            self.advance_world()
            if self.hero.generation != starting_gen:
                return
            alerted_nearby = [e for e in self.enemies if e.alerted]
            if any(max(abs(e.x - self.hero.x), abs(e.y - self.hero.y)) <= self.enemy_notice_radius(e)
                   for e in alerted_nearby):
                self.msg(f"Rest interrupted! (+{healed} HP)")
                return
        self.msg(f"You feel steadier. (+{healed} HP)")

    def _find_explore_move(self) -> tuple[int, int] | None:
        """BFS to nearest unseen walkable tile. Returns (dx, dy) first step, or None."""
        from collections import deque
        fov = compute_fov(self.tiles, self.hero.x, self.hero.y, self.hero.stats.vision)

        # Stop if any enemy is visible
        if any((e.x, e.y) in fov for e in self.enemies):
            return None

        # Stop if an alerted enemy is already hunting you
        if any(e.alerted for e in self.enemies):
            return None

        # Stop if standing on bones
        if any(b.x == self.hero.x and b.y == self.hero.y for b in self.floor_bones):
            return None

        # Stop if too heavy to pick up any remaining floor item
        if self.floor_items:
            lightest = min(ITEMS[it.item_id]["weight"] for it in self.floor_items)
            if self._carry_weight() + lightest > self._max_carry():
                return None

        start = (self.hero.x, self.hero.y)
        queue = deque([(start, None)])
        visited = {start}

        while queue:
            (x, y), first_step = queue.popleft()
            for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
                nx, ny = x + dx, y + dy
                if not (0 <= nx < MAP_W and 0 <= ny < MAP_H):
                    continue
                if (nx, ny) in visited or self.tiles[ny][nx] == "#":
                    continue
                step = first_step if first_step else (dx, dy)
                if (nx, ny) not in self.seen:
                    return step
                visited.add((nx, ny))
                queue.append(((nx, ny), step))

        return None

    def run(self):
        while True:
            self.draw()

            if self.autoexplore:
                self.stdscr.nodelay(True)
                k = self.stdscr.getch()
                self.stdscr.nodelay(False)
                if k != -1:
                    self.autoexplore = False
                    self.msg("Autoexplore stopped.")
                    continue

                move = self._find_explore_move()
                if move is None:
                    self.autoexplore = False
                    fov = compute_fov(self.tiles, self.hero.x, self.hero.y, self.hero.stats.vision)
                    if any((e.x, e.y) in fov for e in self.enemies):
                        self.msg("Enemy spotted -- autoexplore stopped.")
                    elif any(b.x == self.hero.x and b.y == self.hero.y for b in self.floor_bones):
                        self.msg("Bones nearby -- autoexplore stopped.")
                    elif (self.floor_items and
                          self._carry_weight() + min(ITEMS[it.item_id]["weight"] for it in self.floor_items)
                          > self._max_carry()):
                        self.msg("Pack at weight limit -- autoexplore stopped.")
                    else:
                        self.msg("Nothing left to explore here.")
                    continue

                self.try_move(*move)
                curses.napms(25)
                continue

            k = self.stdscr.getch()
            if k in (ord("q"), ord("Q")):
                save_game(self)
                self.msg("Game saved.")
                break
            elif k in (curses.KEY_UP,    ord("k")):
                self.try_move(0, -1)
            elif k in (curses.KEY_DOWN,  ord("j")):
                self.try_move(0,  1)
            elif k in (curses.KEY_LEFT,  ord("h")):
                self.try_move(-1, 0)
            elif k in (curses.KEY_RIGHT, ord("l")):
                self.try_move(1,  0)
            elif k == ord("i"):
                self.show_inventory()
            elif k == ord("o"):
                self.autoexplore = True
                self.msg("Autoexploring...")
            elif k == ord("."):
                self.wait_turn()
            elif k == ord("r"):
                self.rest_until_full()
            elif k == ord("g"):
                self.examine_bones()
            elif k == ord("d"):
                self.show_dynasty()
            elif k == ord("z"):
                for line in self.hero.optimize_gear():
                    self.msg(line)


# ── Save / load (game state) ──────────────────────────────────────────────────

def load_saved_game(stdscr, bones_list: list, dynasty: list, family_name: str):
    if not SAVE_FILE.exists():
        return None
    try:
        data = json.loads(SAVE_FILE.read_text())
    except Exception:
        delete_save()
        return None
    try:
        return _build_game_from_save(stdscr, data, bones_list, dynasty, family_name)
    except Exception:
        delete_save()
        return None


def _build_game_from_save(stdscr, data: dict, bones_list, dynasty, family_name):

    hero_d = data["hero"]
    stats  = Stats(**hero_d.pop("stats"))
    hero   = Hero(**hero_d, stats=stats)
    progression_version = data.get("progression_version", 1)
    saved_level = data.get("level", 1)
    saved_xp = data.get("xp", 0)

    if progression_version < 2:
        migrated_level, migrated_xp = progression_from_total_xp(saved_xp)
        hero.stats.max_hp -= 3 * max(0, saved_level - 1)
        hero.stats.max_hp += level_max_hp_bonus(migrated_level)
        hero.hp = min(hero.hp, hero.stats.max_hp)
        hero.stats.attack -= max(0, saved_level - 1)
        hero.stats.attack += level_attack_bonus(migrated_level)
        hero.stats.defense -= saved_level // 2
        hero.stats.defense += level_defense_bonus(migrated_level)
        saved_level = migrated_level
        saved_xp = migrated_xp

    game = object.__new__(Game)
    game.stdscr             = stdscr
    game.hero               = hero
    game.bones_list         = bones_list
    game.dynasty            = dynasty
    game.family_name        = family_name
    game.messages           = []
    game.xp                 = saved_xp
    game.level              = saved_level
    game.tiles              = data["tiles"]
    game.rooms              = [Rect(**r) for r in data["rooms"]]
    game.enemies            = [Enemy(**e) for e in data["enemies"]]
    game.floor_bones        = [Bones(**b) for b in data["floor_bones"]]
    game.floor_items        = [Item(**i) for i in data.get("floor_items", [])]
    game.inscriptions       = {
        (int(k.split(",")[0]), int(k.split(",")[1])): v
        for k, v in data["inscriptions"].items()
    }
    game.seen               = {tuple(xy) for xy in data["seen"]}
    game.visited_rooms      = {tuple(xy) for xy in data["visited_rooms"]}
    game.current_floor_name = data["current_floor_name"]
    game.autoexplore        = False
    game.turn_meter         = data.get("turn_meter", 0)
    return game


# ── Main ───────────────────────────────────────────────────────────────────────

def _confirm_new_family(stdscr) -> bool:
    stdscr.clear()
    draw_box(stdscr, 5, 8, 12, 48, "NEW FAMILY")
    stdscr.addstr(7,  12, "A new bloodline will begin.", curses.color_pair(3))
    stdscr.addstr(8,  12, "The old family's bones remain in the dark.", curses.color_pair(2))
    stdscr.addstr(10, 12, "Dynasty records will be lost.", curses.color_pair(4))
    stdscr.addstr(12, 12, "[ y ]  found a new house",  curses.color_pair(1))
    stdscr.addstr(13, 12, "[ n ]  cancel",             curses.color_pair(1))
    stdscr.refresh()
    while True:
        k = stdscr.getch()
        if k in (ord("y"), ord("Y")):
            return True
        if k in (ord("n"), ord("N"), 27):
            return False


def _confirm_fresh_start(stdscr) -> bool:
    stdscr.clear()
    draw_box(stdscr, 5, 8, 12, 48, "FRESH START")
    stdscr.addstr(7,  12, "This will erase ALL lineage data:", curses.color_pair(4))
    stdscr.addstr(8,  12, "bones, dynasty, and current save.",  curses.color_pair(4))
    stdscr.addstr(10, 12, "Your family will be forgotten forever.", curses.color_pair(3))
    stdscr.addstr(12, 12, "[ y ]  yes, wipe everything",  curses.color_pair(1))
    stdscr.addstr(13, 12, "[ n ]  cancel",                curses.color_pair(1))
    stdscr.refresh()
    while True:
        k = stdscr.getch()
        if k in (ord("y"), ord("Y")):
            return True
        if k in (ord("n"), ord("N"), 27):
            return False


def main(stdscr):
    curses.curs_set(0)
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_WHITE,   -1)
    curses.init_pair(2, curses.COLOR_CYAN,    -1)
    curses.init_pair(3, curses.COLOR_YELLOW,  -1)
    curses.init_pair(4, curses.COLOR_RED,     -1)
    curses.init_pair(5, curses.COLOR_MAGENTA, -1)
    curses.init_pair(6, curses.COLOR_GREEN,   -1)

    bones_list  = load_bones()
    dynasty     = load_dynasty()
    family_name = get_family_name(dynasty)

    # Offer to continue a saved run if one exists
    if SAVE_FILE.exists():
        stdscr.clear()
        draw_box(stdscr, 5, 10, 12, 44, "LINEAGE")
        stdscr.addstr(7,  14, "A saved run exists.", curses.color_pair(2))
        hero_hint = ""
        try:
            saved = json.loads(SAVE_FILE.read_text())
            h = saved["hero"]
            fn = saved.get("current_floor_name", "unknown floor")
            hero_hint = f"{h['name']}  --  {fn}"
            stdscr.addstr(8, 14, hero_hint, curses.color_pair(3))
        except Exception:
            pass
        stdscr.addstr(11, 14, "[ ENTER ]  continue",          curses.color_pair(1))
        stdscr.addstr(12, 14, "[ n     ]  new game",          curses.color_pair(1))
        stdscr.addstr(13, 14, "[ h     ]  new family",        curses.color_pair(3))
        stdscr.addstr(14, 14, "[ f     ]  fresh start",       curses.color_pair(4))
        stdscr.addstr(15, 14, "[ q     ]  quit",              curses.color_pair(1))
        stdscr.refresh()
        while True:
            k = stdscr.getch()
            if k in (10, 13):
                game = load_saved_game(stdscr, bones_list, dynasty, family_name)
                if game:
                    game.run()
                    return
                break
            elif k in (ord("n"), ord("N")):
                delete_save()
                break
            elif k in (ord("h"), ord("H")):
                if _confirm_new_family(stdscr):
                    delete_lineage_only()
                    dynasty     = []
                    family_name = get_family_name([])
                break
            elif k in (ord("f"), ord("F")):
                if _confirm_fresh_start(stdscr):
                    delete_all_data()
                    bones_list  = []
                    dynasty     = []
                    family_name = get_family_name([])
                break
            elif k in (ord("q"), ord("Q")):
                return

    # If there's an existing dynasty but no save, offer a fresh start before continuing
    if dynasty and not SAVE_FILE.exists():
        stdscr.clear()
        gen_count = len(dynasty)
        draw_box(stdscr, 5, 8, 13, 48, "THE LINEAGE CONTINUES")
        stdscr.addstr(7,  12, f"House {family_name}  --  {gen_count} generation{'s' if gen_count != 1 else ''} fallen.",
                      curses.color_pair(3))
        stdscr.addstr(9,  12, "[ ENTER ]  continue the bloodline",   curses.color_pair(1))
        stdscr.addstr(10, 12, "[ h     ]  new family",               curses.color_pair(3))
        stdscr.addstr(11, 12, "[ f     ]  fresh start (wipe all)",   curses.color_pair(4))
        stdscr.addstr(12, 12, "[ q     ]  quit",                     curses.color_pair(1))
        stdscr.refresh()
        while True:
            k = stdscr.getch()
            if k in (10, 13):
                break
            elif k in (ord("h"), ord("H")):
                if _confirm_new_family(stdscr):
                    delete_lineage_only()
                    dynasty     = []
                    family_name = get_family_name([])
                break
            elif k in (ord("f"), ord("F")):
                if _confirm_fresh_start(stdscr):
                    delete_all_data()
                    bones_list  = []
                    dynasty     = []
                    family_name = get_family_name([])
                break
            elif k in (ord("q"), ord("Q")):
                return

    generation = len(dynasty) + 1
    if dynasty:
        parent      = dynasty[-1]
        parent_bone = next((b for b in reversed(bones_list)
                            if b.hero_name == parent["name"]), None)
        inherited_skill = parent_bone.skill_id if parent_bone else random.choice(list(SKILLS.keys()))
        name = make_name(generation, family_name)
    else:
        inherited_skill = None
        name = make_name(1, family_name)

    hero = Hero(name=name, generation=generation)
    if inherited_skill:
        hero.apply_skill(inherited_skill)

    stdscr.clear()
    box_w = 58
    draw_box(stdscr, 1, 3, 20, box_w,
             f"Generation {generation}" if generation > 1 else "The House Awakens")
    y, x = 3, 6
    for line in make_hero_intro(generation, family_name, hero.trait, inherited_skill):
        for wrapped in wrap(line, box_w - 6):
            stdscr.addstr(y, x, wrapped, curses.color_pair(2)); y += 1
    stdscr.addstr(19, x, "[ ENTER ]  descend", curses.color_pair(1))
    stdscr.refresh()
    while stdscr.getch() not in (10, 13):
        pass

    game = Game(stdscr, hero, bones_list, dynasty, family_name)
    game.run()


if __name__ == "__main__":
    curses.wrapper(main)
