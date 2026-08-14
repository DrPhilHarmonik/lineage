"""The game's nouns: hero, enemy, bones, items, and the rooms they sit in.

Dataclasses with the behaviour that belongs to the thing itself -- a hero
applies a skill, equips gear, drinks a potion. Rules that need the wider game
(combat, levelling, awareness) live in `systems` and `game` instead.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from content import HERO_TRAITS, ITEMS, SKILLS

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
