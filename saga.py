"""Dynasty saga -- watch a bloodline rise and fall, headless.

Simulates successive generations descending the dungeon. Each hero fights down
through the five floors using the game's real combat, progression, and enemy
tables, then dies (leaving an epitaph and an inherited skill for the next of the
line) or reaches the bottom and redeems the house. Prints the whole family saga
-- no curses, no interaction, and no touching your real save files.

    python3 saga.py                    # a saga of up to 8 generations
    python3 saga.py --generations 15   # give the bloodline more tries
    python3 saga.py --seed 3           # reproducible dynasty
"""

import argparse
import random

import lineage as L

BOTTOM = 5

# Small, flavorful trait tweaks so each hero descends a little differently.
# (The full game expresses traits through dialogue; here they nudge the math.)
TRAIT_TWEAKS = {
    "reckless":   {"attack": +2, "max_hp": -4},
    "cautious":   {"max_hp": +5},
    "stubborn":   {"max_hp": +4},
    "sharp":      {"attack": +1},
    "determined": {"attack": +1, "max_hp": +2},
    "grim":       {"attack": +2},
    "proud":      {"attack": +1, "max_hp": -2},
    "unlucky":    {"dodge": -5},
    "calm":       {"dodge": +5},
}


def apply_trait(hero):
    for stat, delta in TRAIT_TWEAKS.get(hero.trait, {}).items():
        setattr(hero.stats, stat, getattr(hero.stats, stat) + delta)
    hero.stats.max_hp = max(6, hero.stats.max_hp)
    hero.hp = hero.stats.max_hp  # start each descent at full


def simulate_descent(hero):
    """Fight the hero down floors 1..5. Returns (won, floor, cause)."""
    total_xp = 0
    for floor in range(1, BOTTOM + 1):
        hero.floor = floor
        encounters = 2 + floor // 2
        for _ in range(encounters):
            level, _ = L.progression_from_total_xp(total_xp)
            atk = hero.stats.attack + L.level_attack_bonus(level)
            dfn = hero.stats.defense + L.level_defense_bonus(level)
            enemy = L.make_enemy(random.choice(L.FLOOR_ENEMIES[floor]), floor)
            while True:
                enemy.hp -= max(1, atk)
                if enemy.hp <= 0:
                    total_xp += enemy.xp
                    break
                dmg = max(1, enemy.attack - dfn)
                if random.randint(1, 100) <= hero.stats.dodge:
                    dmg = 0
                hero.hp -= dmg
                if hero.hp <= 0:
                    return (False, floor, enemy.title if enemy.title else f"a {enemy.name}")
        # Survived the floor: sometimes learn a new skill (grows the bloodline's
        # inheritance), level up, patch some wounds.
        if random.random() < 0.5:
            unknown = [s for s in L.SKILLS if s not in hero.skills]
            if unknown:
                hero.apply_skill(random.choice(unknown))
        level, _ = L.progression_from_total_xp(total_xp)
        hero.stats.max_hp = 20 + L.level_max_hp_bonus(level) + (hero.stats.max_hp - 20)
        hero.hp = min(hero.stats.max_hp, hero.hp + 6 + level)
    return (True, BOTTOM, "reached the bottom")


def run_saga(generations):
    family_name = random.choice(L.FAMILY_NAMES)
    dynasty, bones = [], []
    inherited_skill = None
    deepest = 0
    champion = None
    out = ["=" * 64,
           f"  THE SAGA OF THE HOUSE OF {family_name.upper()}",
           "=" * 64, ""]

    for gen in range(1, generations + 1):
        hero = L.Hero(name=L.make_name(gen, family_name), generation=gen)
        if inherited_skill:
            hero.apply_skill(inherited_skill)
        apply_trait(hero)

        for line in L.make_hero_intro(gen, family_name, hero.trait, inherited_skill):
            out.append("  " + line if line else "")

        won, floor, cause = simulate_descent(hero)
        hero.floor = floor
        floor_name = L.get_floor_name(floor)
        passed = hero.skills[-1] if hero.skills else random.choice(list(L.SKILLS.keys()))
        deepest = max(deepest, floor)

        entry = {
            "name": hero.name, "generation": gen, "floor": floor,
            "floor_name": floor_name, "skill_id": passed, "trait": hero.trait,
            "family_name": family_name,
        }

        if won:
            out += ["", f"  {hero.name} reached the bottom on {floor_name}.",
                    "  After generations in the dark, the house is redeemed.", ""]
            entry.update({"cause": "reached the bottom", "won": True,
                          "epitaph": "", "last_words": ""})
            dynasty.append(entry)
            champion = hero.name
            break

        epitaph = L.make_epitaph(hero, cause, family_name, floor_name)
        last_words = L.make_last_words(cause.lstrip("a "), floor)
        out += ["", f"  {hero.name} fell to {cause} on {floor_name}.",
                f'  "{last_words}"', f"  {epitaph}", ""]
        entry.update({"cause": cause, "epitaph": epitaph, "last_words": last_words})
        dynasty.append(entry)
        bones.append(L.Bones(
            hero_name=hero.name, generation=gen, floor=floor, cause=cause,
            skill_id=passed, x=0, y=0, epitaph=epitaph, last_words=last_words,
            trait=hero.trait, relics=[],
        ))
        inherited_skill = passed

    out += ["=" * 64, "  THE CHRONICLE", "=" * 64, ""]
    for entry in dynasty:
        out += ["  " + line if line else "" for line in L.make_chronicle_entry(entry)]

    out += ["=" * 64]
    if champion:
        out.append(f"  {len(dynasty)} generations. The line of {family_name} reached the "
                   f"bottom at last -- {champion} redeemed the house.")
    else:
        out.append(f"  {len(dynasty)} generations. The line of {family_name} never reached "
                   f"the bottom. Deepest descent: floor {deepest}.")
    out.append("=" * 64)
    return out


def main():
    ap = argparse.ArgumentParser(description="Watch a lineage bloodline rise and fall.")
    ap.add_argument("--generations", type=int, default=8, help="max generations to simulate")
    ap.add_argument("--seed", type=int, default=None, help="RNG seed for a reproducible dynasty")
    args = ap.parse_args()
    if args.seed is not None:
        random.seed(args.seed)
    print("\n".join(run_saga(args.generations)))


if __name__ == "__main__":
    main()
