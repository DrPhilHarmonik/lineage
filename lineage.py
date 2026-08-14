#!/usr/bin/env python3
"""
LINEAGE -- ASCII Roguelike
Each hero is the child of the last. Find your ancestor's bones. Inherit their final lesson.

    python3 lineage.py

This file is the entry point and the front door. The game itself lives in:

    content.py     skills, items, enemy and floor tables, every text pool
    models.py      hero, enemy, bones, item, room
    generation.py  floor construction and field of view
    systems.py     progression maths
    save.py        where the save files are, and reading and writing them
    ui.py          curses drawing helpers and modal screens
    game.py        the Game object: one floor, the hero on it, the loop over both

The names below are re-exported so `import lineage` still reaches the whole
game -- `saga.py` and the test suite both rely on it.

One deliberate omission: the save *paths* are not re-exported. `save.py` owns
them, and a second name pointing at the same Path would be a name that looks
redirectable and is not -- redirect it here and the code that writes the files
would carry on writing to `~/.lineage`. Ask `save` instead.
"""

from __future__ import annotations

import curses
import random

import save
from content import (
    ANCESTOR_KILL_MSGS,
    ANCESTOR_LEVEL_MSGS,
    CARRY_MAX,
    ENEMY_HIT,
    ENEMY_MISS,
    ENEMY_NAMES,
    ENEMY_SPOT,
    EPITAPH_TEMPLATES,
    FAMILY_NAMES,
    FIRST_NAMES,
    FLOOR_ARRIVAL,
    FLOOR_ENEMIES,
    FLOOR_ITEMS,
    FLOOR_NAMES,
    HERO_INTROS,
    HERO_TRAITS,
    ITEMS,
    LAST_WORDS,
    PARENT_ADJ,
    PLAYER_HIT,
    PLAYER_KILL,
    ROOM_INSCRIPTIONS,
    SKILL_VOICE,
    SKILLS,
    TRAIT_EPITAPH,
    TRAIT_INTRO,
    WIN_LINES,
    get_family_name,
    get_floor_name,
    make_chronicle_entry,
    make_epitaph,
    make_hero_intro,
    make_last_words,
    make_name,
    pick_skill_voice,
)
from game import Game, load_saved_game, save_game
from generation import (
    MAP_H,
    MAP_W,
    MAX_ROOMS,
    MIN_ROOMS,
    ROOM_MAX,
    ROOM_MIN,
    compute_fov,
    generate_dungeon,
    make_enemy,
)
from models import Bones, Enemy, Hero, Item, Rect, Stats
from save import (
    delete_all_data,
    delete_lineage_only,
    delete_save,
    ensure_save_dir,
    load_bones,
    load_dynasty,
    save_bones,
    save_dynasty,
)
from systems import (
    level_attack_bonus,
    level_defense_bonus,
    level_max_hp_bonus,
    progression_from_total_xp,
)
from ui import _confirm_fresh_start, _confirm_new_family, draw_box, wrap

# The re-exported surface, declared rather than implied: these names are
# imported here to be *available as `lineage.X`*, not because this module uses
# them, and `__all__` is what tells a linter (and a reader) the difference.
__all__ = [
    # content -- all of it, deliberately. Re-exporting a hand-picked subset is
    # what broke saga.py during the split: it wanted FAMILY_NAMES, which was
    # not on anybody's list of names worth forwarding.
    "ANCESTOR_KILL_MSGS", "ANCESTOR_LEVEL_MSGS", "CARRY_MAX", "ENEMY_HIT",
    "ENEMY_MISS", "ENEMY_NAMES", "ENEMY_SPOT", "EPITAPH_TEMPLATES",
    "FAMILY_NAMES", "FIRST_NAMES", "FLOOR_ARRIVAL", "FLOOR_ENEMIES",
    "FLOOR_ITEMS", "FLOOR_NAMES", "HERO_INTROS", "HERO_TRAITS", "ITEMS",
    "LAST_WORDS", "PARENT_ADJ", "PLAYER_HIT", "PLAYER_KILL",
    "ROOM_INSCRIPTIONS", "SKILL_VOICE", "SKILLS", "TRAIT_EPITAPH",
    "TRAIT_INTRO", "WIN_LINES", "get_family_name", "get_floor_name",
    "make_chronicle_entry", "make_epitaph", "make_hero_intro",
    "make_last_words", "make_name", "pick_skill_voice",
    # models
    "Bones", "Enemy", "Hero", "Item", "Rect", "Stats",
    # generation
    "MAP_H", "MAP_W", "MAX_ROOMS", "MIN_ROOMS", "ROOM_MAX", "ROOM_MIN",
    "compute_fov", "generate_dungeon", "make_enemy",
    # systems
    "level_attack_bonus", "level_defense_bonus", "level_max_hp_bonus",
    "progression_from_total_xp",
    # save (the functions; the paths stay in `save`, see the module docstring)
    "delete_all_data", "delete_lineage_only", "delete_save", "ensure_save_dir",
    "load_bones", "load_dynasty", "save_bones", "save_dynasty",
    # game
    "Game", "load_saved_game", "save_game",
    # ui
    "draw_box", "wrap",
    # this module
    "main",
]


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
    if save.saved_game_exists():
        stdscr.clear()
        draw_box(stdscr, 5, 10, 12, 44, "LINEAGE")
        stdscr.addstr(7,  14, "A saved run exists.", curses.color_pair(2))
        hero_hint = ""
        try:
            saved = save.read_save_data() or {}
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
    if dynasty and not save.saved_game_exists():
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
