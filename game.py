"""The Game object: one loaded floor, the hero on it, and the loop over both.

Everything that needs to know about *all* of the game at once is here -- the
turn loop, combat, enemy AI, and the screens that read hero and dynasty state
together. What could be lifted out already has been: content tables, the
dataclasses, floor generation, progression maths, and persistence.

`save_game` and `load_saved_game` sit here rather than in `save` because they
have to know what a game is made of. `save` knows only about files.
"""

from __future__ import annotations

import curses
import random
from dataclasses import asdict

import save
from content import (
    ANCESTOR_KILL_MSGS,
    ANCESTOR_LEVEL_MSGS,
    CARRY_MAX,
    ENEMY_HIT,
    ENEMY_MISS,
    ENEMY_SPOT,
    FLOOR_ARRIVAL,
    FLOOR_ITEMS,
    ITEMS,
    PLAYER_HIT,
    PLAYER_KILL,
    SKILLS,
    WIN_LINES,
    get_floor_name,
    make_chronicle_entry,
    make_epitaph,
    make_hero_intro,
    make_last_words,
    make_name,
    pick_skill_voice,
)
from generation import MAP_H, MAP_W, compute_fov, generate_dungeon
from models import Bones, Enemy, Hero, Item, Rect, Stats
from save import delete_save, save_bones, save_dynasty
from systems import (
    level_attack_bonus,
    level_defense_bonus,
    level_max_hp_bonus,
    progression_from_total_xp,
)
from ui import draw_box, wrap


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


def save_game(game) -> None:
    """Serialise a running game.

    Coordinate-keyed structures are flattened to strings because JSON has no
    tuples; `_build_game_from_save` restores them.
    """
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
    save.write_save_data(data)


def load_saved_game(stdscr, bones_list: list, dynasty: list, family_name: str):
    """Rebuild the saved run, or None if there is nothing loadable.

    Unreadable JSON is handled by `save.read_save_data`; what is caught here is
    the save that parses but no longer fits the code -- a renamed field, a
    dataclass that gained a required argument. Either way the run is gone, and
    deleting it is what lets the next launch start rather than fail the same way
    forever.
    """
    data = save.read_save_data()
    if data is None:
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
