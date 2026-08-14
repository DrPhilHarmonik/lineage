"""Regression coverage for LINEAGE's systems (ROADMAP priority 5, item 12).

Scope is deliberately the five things the roadmap names -- hero stat
application, progression thresholds, save/load compatibility, dungeon placement
invariants, and enemy awareness. These are the systems a reader of the code
cannot check by eye, and the ones a refactor is most likely to break quietly:
splitting the single file (item 11) moves all of them.

Nothing here draws. `Game.__init__` only needs `stdscr` to hand to `draw()`, so
tests pass `None` and build the object directly when the constructor's floor
generation would be in the way.

Every test writes to a temporary save directory. `SAVE_DIR` is a module-level
`~/.lineage`, and a real dynasty lives there.
"""

from __future__ import annotations

import json
import random

import pytest

import lineage as L


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def temp_save_dir(tmp_path, monkeypatch):
    """Redirect the save paths for *every* test, including ones that never save.

    Autouse rather than opt-in: the failure this prevents is a test overwriting
    the player's real bones and dynasty, which is silent, permanent, and would
    be discovered long after the run that did it.

    Patched on `save`, the module that defines them, and never on `lineage`,
    which only re-exports the rest of the game. A patched copy on the façade
    would leave the functions that write the files reading the original names,
    so the redirect would look applied and the writes would land in
    `~/.lineage`. The assertion below is what would catch that.
    """
    save_dir = tmp_path / "lineage-saves"
    save_dir.mkdir()
    monkeypatch.setattr(L.save, "SAVE_DIR", save_dir)
    monkeypatch.setattr(L.save, "BONES_FILE", save_dir / "bones.json")
    monkeypatch.setattr(L.save, "DYNASTY_FILE", save_dir / "dynasty.json")
    monkeypatch.setattr(L.save, "SAVE_FILE", save_dir / "save.json")

    L.save_bones([])
    assert (save_dir / "bones.json").exists(), "save paths are not redirected"
    (save_dir / "bones.json").unlink()
    return save_dir


def make_game(hero=None, **overrides):
    """A Game with no floor generated and no curses attached.

    `Game.__init__` generates a dungeon, which is a lot of randomness to drag
    into a test about levelling. This builds the object the same way
    `_build_game_from_save` does and fills in only what the system under test
    reads.
    """
    game = object.__new__(L.Game)
    game.stdscr = None
    game.hero = hero if hero is not None else L.Hero(name="Test Heir", generation=1)
    game.bones_list = []
    game.dynasty = []
    game.family_name = "Testholt"
    game.messages = []
    game.xp = 0
    game.level = 1
    game.turn_meter = 0
    game.enemies = []
    game.seen = set()
    game.visited_rooms = set()
    game.autoexplore = False
    for key, value in overrides.items():
        setattr(game, key, value)
    return game


def open_map(width=None, height=None):
    """A map of bare floor, for tests that want geometry without a dungeon."""
    width = width or L.MAP_W
    height = height or L.MAP_H
    return [["."] * width for _ in range(height)]


# ── 1. Hero stat application ───────────────────────────────────────────────────

def test_apply_skill_grants_its_stat_and_records_the_skill():
    hero = L.Hero(name="Heir", generation=1, trait="calm")
    before = hero.stats.attack

    hero.apply_skill("sharp_blade")

    assert hero.skills == ["sharp_blade"]
    assert hero.stats.attack == before + L.SKILLS["sharp_blade"]["val"]


def test_max_hp_skills_raise_current_hp_too():
    """A hero who learns Tough Soul mid-descent should feel it immediately.

    Raising `max_hp` without raising `hp` would hand the hero a bonus they only
    receive after finding a healing potion.
    """
    hero = L.Hero(name="Heir", generation=1, trait="calm")
    hp_before, max_before = hero.hp, hero.stats.max_hp

    hero.apply_skill("tough_soul")

    assert hero.stats.max_hp == max_before + 5
    assert hero.hp == hp_before + 5


def test_bloodline_grants_attack_on_top_of_its_table_entry():
    """Bloodline is the one skill whose table row understates it: the entry says
    +3 max_hp, and `apply_skill` adds +1 attack besides. Pinned because the
    description ("+3 max HP and +1 attack") lives in a different place from the
    code that grants it."""
    hero = L.Hero(name="Heir", generation=1, trait="calm")
    hp_before, atk_before = hero.stats.max_hp, hero.stats.attack

    hero.apply_skill("bloodline")

    assert hero.stats.max_hp == hp_before + 3
    assert hero.stats.attack == atk_before + 1


def test_applying_the_same_skill_twice_stacks_its_stats():
    """Documents current behaviour rather than endorsing it.

    The skill list is de-duplicated but the stat bonus is not, so a second
    application is invisible on the character sheet and permanent on the stats.
    Inheritance can hand down a skill the hero already has, which is the path
    that reaches this. If the intent is that re-learning does nothing, this
    test is the one to change.
    """
    hero = L.Hero(name="Heir", generation=1, trait="calm")
    base = hero.stats.attack

    hero.apply_skill("sharp_blade")
    hero.apply_skill("sharp_blade")

    assert hero.skills == ["sharp_blade"]
    assert hero.stats.attack == base + 2 * L.SKILLS["sharp_blade"]["val"]


def test_equipping_over_an_item_removes_the_old_bonus():
    hero = L.Hero(name="Heir", generation=1, trait="calm")
    base = hero.stats.attack
    hero.inventory = ["rusty_dagger", "battle_axe"]

    hero.equip("rusty_dagger")
    old = hero.equip("battle_axe")

    assert old == "rusty_dagger"
    assert hero.equipped["weapon"] == "battle_axe"
    assert hero.stats.attack == base + L.ITEMS["battle_axe"]["val"]
    assert "battle_axe" not in hero.inventory


def test_swapping_max_hp_gear_never_leaves_hp_above_max():
    """Unequipping a max_hp item has to clamp `hp`, or the hero walks around
    with more health than their sheet allows until something damages them."""
    hero = L.Hero(name="Heir", generation=1, trait="calm")
    max_hp_items = [iid for iid, item in L.ITEMS.items()
                    if item.get("stat") == "max_hp" and item.get("slot")]
    if not max_hp_items:
        pytest.skip("no equippable max_hp items in the item table")
    item_id = max_hp_items[0]
    slot = L.ITEMS[item_id]["slot"]
    same_slot_other = next(
        (iid for iid, item in L.ITEMS.items()
         if item.get("slot") == slot and iid != item_id),
        None,
    )
    hero.equip(item_id)
    assert hero.hp <= hero.stats.max_hp

    if same_slot_other:
        hero.equip(same_slot_other)
        assert hero.hp <= hero.stats.max_hp


def test_healing_never_exceeds_max_hp():
    hero = L.Hero(name="Heir", generation=1, trait="calm")
    hero.inventory = ["healing_potion"]
    hero.hp = hero.stats.max_hp - 1

    hero.use_consumable("healing_potion")

    assert hero.hp == hero.stats.max_hp
    assert "healing_potion" not in hero.inventory


def test_optimize_gear_leaves_cross_stat_slots_alone():
    """Two items in one slot that raise *different* stats is a judgement call,
    not an upgrade, so the auto-equip declines rather than deciding for the
    player."""
    equip_slots = ("weapon", "armor", "accessory")  # what optimize_gear considers
    slot_stats = {}
    for iid, item in L.ITEMS.items():
        if item.get("slot") in equip_slots:
            slot_stats.setdefault(item["slot"], {}).setdefault(item["stat"], []).append(iid)
    mixed = next((slot for slot, stats in slot_stats.items() if len(stats) > 1), None)
    if mixed is None:
        pytest.skip("no equip slot in the item table holds items with differing stats")

    hero = L.Hero(name="Heir", generation=1, trait="calm")
    hero.inventory = [ids[0] for ids in slot_stats[mixed].values()][:2]
    before = hero.equipped[mixed]

    hero.optimize_gear()

    assert hero.equipped[mixed] == before


# ── 2. Progression thresholds ──────────────────────────────────────────────────

def test_progression_curve_matches_the_level_cost_table():
    """`progression_from_total_xp` and `Game.xp_to_next_level` are two
    statements of the same curve -- one used on load, one during play. They
    have to agree, or a save round-trip silently moves the hero's level."""
    total = 0
    for level in range(1, 12):
        assert L.progression_from_total_xp(total) == (level, 0)
        total += 10 + (level - 1) * 6


def test_progression_reports_leftover_xp_toward_the_next_level():
    assert L.progression_from_total_xp(0) == (1, 0)
    assert L.progression_from_total_xp(9) == (1, 9)
    assert L.progression_from_total_xp(10) == (2, 0)
    assert L.progression_from_total_xp(11) == (2, 1)


def test_progression_treats_negative_xp_as_none():
    assert L.progression_from_total_xp(-50) == (1, 0)


def test_level_bonuses_never_decrease():
    for level in range(1, 30):
        for bonus in (L.level_attack_bonus, L.level_defense_bonus, L.level_max_hp_bonus):
            assert bonus(level + 1) >= bonus(level)
    assert L.level_max_hp_bonus(1) == 0
    assert L.level_attack_bonus(1) == 0
    assert L.level_defense_bonus(1) == 0


def test_gain_xp_levels_once_at_the_threshold_and_applies_the_bonuses():
    game = make_game()
    hero = game.hero
    atk, dfn, max_hp = hero.stats.attack, hero.stats.defense, hero.stats.max_hp

    game.gain_xp(game.xp_to_next_level())

    assert game.level == 2
    assert game.xp == 0
    assert hero.stats.attack == atk + (L.level_attack_bonus(2) - L.level_attack_bonus(1))
    assert hero.stats.defense == dfn + (L.level_defense_bonus(2) - L.level_defense_bonus(1))
    assert hero.stats.max_hp == max_hp + (L.level_max_hp_bonus(2) - L.level_max_hp_bonus(1))


def test_a_single_large_kill_can_carry_several_levels():
    """One award has to be able to cross more than one threshold: deep-floor
    enemies are worth more than an early level costs."""
    game = make_game()

    game.gain_xp(1000)

    expected_level, expected_xp = L.progression_from_total_xp(1000)
    assert (game.level, game.xp) == (expected_level, expected_xp)


def test_levelling_raises_current_hp_with_max_hp():
    game = make_game()
    game.hero.hp = game.hero.stats.max_hp
    before = game.hero.hp

    game.gain_xp(game.xp_to_next_level())

    assert game.hero.hp == before + (L.level_max_hp_bonus(2) - L.level_max_hp_bonus(1))


# ── 3. Save / load compatibility ───────────────────────────────────────────────

def saved_game_fixture():
    """A game with a real generated floor, so the save covers real structures."""
    random.seed(1234)
    hero = L.Hero(name="Saved Heir", generation=3, trait="grim")
    hero.apply_skill("iron_skin")
    hero.inventory = ["healing_potion"]
    hero.equip("rusty_dagger")
    game = L.Game(None, hero, [], [], "Testholt")
    game.xp, game.level, game.turn_meter = 4, 2, 1
    game.seen = {(1, 1), (2, 2)}
    game.visited_rooms = {(3, 3)}
    return game


def test_save_and_load_round_trips_the_whole_game():
    game = saved_game_fixture()

    L.save_game(game)
    loaded = L.load_saved_game(None, [], [], "Testholt")

    assert loaded is not None
    assert loaded.hero.name == game.hero.name
    assert loaded.hero.generation == game.hero.generation
    assert loaded.hero.skills == game.hero.skills
    assert loaded.hero.equipped == game.hero.equipped
    assert loaded.hero.stats == game.hero.stats
    assert (loaded.xp, loaded.level, loaded.turn_meter) == (game.xp, game.level, game.turn_meter)
    assert loaded.tiles == game.tiles
    assert loaded.current_floor_name == game.current_floor_name
    assert len(loaded.enemies) == len(game.enemies)
    assert len(loaded.floor_items) == len(game.floor_items)


def test_load_restores_tuple_keyed_structures_as_tuples():
    """`seen`, `visited_rooms` and `inscriptions` are keyed by coordinate pairs
    and pass through JSON, which has no tuples. If they come back as lists, every
    `(x, y) in seen` lookup silently misses and the map redraws as unexplored."""
    game = saved_game_fixture()
    game.inscriptions = {(4, 5): "A name has been scratched here."}

    L.save_game(game)
    loaded = L.load_saved_game(None, [], [], "Testholt")

    assert (4, 5) in loaded.inscriptions
    assert all(isinstance(pos, tuple) for pos in loaded.seen)
    assert all(isinstance(pos, tuple) for pos in loaded.visited_rooms)
    assert loaded.seen == game.seen
    assert loaded.visited_rooms == game.visited_rooms


def test_a_version_1_save_is_migrated_to_the_current_progression():
    """Old saves stored a level earned on a different curve. The migration has
    to restate it in current terms rather than leave the hero on stats no
    current level would grant."""
    game = saved_game_fixture()
    L.save_game(game)
    data = json.loads(L.save.SAVE_FILE.read_text())
    data["progression_version"] = 1
    data["xp"] = 40
    data["level"] = 5
    L.save.SAVE_FILE.write_text(json.dumps(data))

    loaded = L.load_saved_game(None, [], [], "Testholt")

    expected_level, expected_xp = L.progression_from_total_xp(40)
    assert (loaded.level, loaded.xp) == (expected_level, expected_xp)
    assert loaded.hero.hp <= loaded.hero.stats.max_hp


def test_a_corrupt_save_is_discarded_rather_than_crashing():
    """A half-written save should cost the run in progress, not the game."""
    L.save.SAVE_FILE.write_text("{ this is not json")

    assert L.load_saved_game(None, [], [], "Testholt") is None
    assert not L.save.SAVE_FILE.exists()


def test_a_structurally_wrong_save_is_discarded_too():
    L.save.SAVE_FILE.write_text(json.dumps({"hero": {"nonsense": True}}))

    assert L.load_saved_game(None, [], [], "Testholt") is None
    assert not L.save.SAVE_FILE.exists()


def test_bones_survive_a_round_trip_with_their_relics():
    """Bones outlive every save file in the game -- they are the whole lineage
    premise -- so their fields, especially the inherited skill and relics, have
    to come back intact."""
    bones = [L.Bones(hero_name="Ivar Testholt", generation=2, floor=3,
                     cause="a goblin", skill_id="iron_skin", x=5, y=6,
                     epitaph="Fell in the dark.", last_words="Not yet.",
                     trait="grim", relics=["rusty_dagger"])]

    L.save_bones(bones)
    loaded = L.load_bones()

    assert loaded == bones


def test_missing_files_load_as_empty_rather_than_failing():
    """First run of a fresh install."""
    assert L.load_bones() == []
    assert L.load_dynasty() == []
    assert L.load_saved_game(None, [], [], "Testholt") is None


def test_deleting_the_lineage_keeps_the_bones():
    L.save_bones([L.Bones(hero_name="Ivar", generation=1, floor=1, cause="a rat",
                          skill_id="lucky", x=1, y=1, epitaph="Fell early.")])
    L.save_dynasty([{"name": "Ivar", "floor": 1}])
    L.save.SAVE_FILE.write_text("{}")

    L.delete_lineage_only()

    assert L.load_bones() != []
    assert L.load_dynasty() == []
    assert not L.save.SAVE_FILE.exists()


# ── 4. Dungeon placement invariants ────────────────────────────────────────────

@pytest.mark.parametrize("seed", range(12))
def test_nothing_shares_a_tile_with_anything_else(seed):
    """The placement bug this guards was visible in play: enemies, bones and
    items stacked on the same tile, so one glyph hid the others."""
    random.seed(seed)
    bones_list = [L.Bones(hero_name=f"Ancestor {i}", generation=i, floor=2,
                          cause="a goblin", skill_id="lucky", x=0, y=0,
                          epitaph="Fell.")
                  for i in range(1, 4)]

    tiles, rooms, enemies, placed_bones, items, _, start = L.generate_dungeon(2, bones_list)

    positions = [(e.x, e.y) for e in enemies]
    positions += [(b.x, b.y) for b in placed_bones]
    positions += [(i.x, i.y) for i in items]
    assert len(positions) == len(set(positions))

    stairs = [(x, y) for y in range(L.MAP_H) for x in range(L.MAP_W) if tiles[y][x] == ">"]
    assert len(stairs) == 1
    assert stairs[0] not in positions


@pytest.mark.parametrize("seed", range(12))
def test_everything_is_placed_on_walkable_floor(seed):
    """A hero cannot reach an item inside a wall, and an enemy in one never
    moves."""
    random.seed(seed)
    tiles, rooms, enemies, placed_bones, items, inscriptions, start = \
        L.generate_dungeon(3, [])

    for x, y in [(e.x, e.y) for e in enemies] + [(i.x, i.y) for i in items] + \
                [(b.x, b.y) for b in placed_bones] + list(inscriptions) + [start]:
        assert 0 <= x < L.MAP_W and 0 <= y < L.MAP_H
        assert tiles[y][x] != "#"


@pytest.mark.parametrize("seed", range(8))
def test_every_floor_offers_at_least_four_items(seed):
    """Descending is attrition; a floor with nothing on it is a floor the hero
    cannot afford to have entered."""
    random.seed(seed)
    _, _, _, _, items, _, _ = L.generate_dungeon(1, [])

    assert len(items) >= 4


@pytest.mark.parametrize("seed", range(8))
def test_the_hero_never_starts_on_the_stairs(seed):
    """Starting on `>` means a single keypress skips the floor."""
    random.seed(seed)
    tiles, _, _, _, _, _, start = L.generate_dungeon(4, [])

    assert tiles[start[1]][start[0]] != ">"


@pytest.mark.parametrize("floor", [1, 2, 3, 4, 5])
def test_enemies_come_from_the_floor_s_own_table(floor):
    random.seed(floor * 7)
    _, _, enemies, _, _, _, _ = L.generate_dungeon(floor, [])

    allowed = {kind[0] for kind in L.FLOOR_ENEMIES[floor]}
    assert {e.name for e in enemies} <= allowed


def test_deeper_floors_than_the_table_reuse_the_deepest_tier():
    """`generate_dungeon` clamps to floor 5 rather than raising, so a future
    sixth floor degrades instead of crashing."""
    random.seed(99)
    _, _, enemies, _, _, _, _ = L.generate_dungeon(9, [])

    allowed = {kind[0] for kind in L.FLOOR_ENEMIES[5]}
    assert {e.name for e in enemies} <= allowed


def test_bones_from_other_floors_are_left_where_they_are():
    """Only the bones of ancestors who died *here* belong on this floor."""
    random.seed(5)
    elsewhere = L.Bones(hero_name="Wrong Floor", generation=1, floor=5,
                        cause="a lich", skill_id="lucky", x=10, y=10,
                        epitaph="Fell deep.")
    here = L.Bones(hero_name="Right Floor", generation=2, floor=2,
                   cause="a goblin", skill_id="lucky", x=10, y=10,
                   epitaph="Fell here.")

    _, _, _, placed, _, _, _ = L.generate_dungeon(2, [elsewhere, here])

    assert [b.hero_name for b in placed] == ["Right Floor"]


# ── 5. Enemy awareness ─────────────────────────────────────────────────────────

def test_quiet_step_shortens_the_radius_enemies_notice_you_at():
    game = make_game()
    enemy = L.Enemy("goblin", "g", 8, 2, 2, notice=5)

    assert game.enemy_notice_radius(enemy) == 5

    game.hero.skills.append("quiet_step")
    assert game.enemy_notice_radius(enemy) == 4


def test_notice_radius_never_falls_below_one_tile():
    """An enemy the hero is standing on top of still notices them."""
    game = make_game()
    game.hero.skills.append("quiet_step")

    assert game.enemy_notice_radius(L.Enemy("rat", "r", 4, 1, 1, notice=1)) == 1


def test_an_enemy_beyond_its_notice_radius_stays_unaware():
    game = make_game(tiles=open_map())
    game.hero.x, game.hero.y = 5, 5
    enemy = L.Enemy("rat", "r", 4, 1, 1, notice=4, x=30, y=20)
    game.enemies = [enemy]

    game.enemy_turns()

    assert not enemy.alerted


def test_an_enemy_within_radius_and_line_of_sight_wakes_up():
    game = make_game(tiles=open_map())
    game.hero.x, game.hero.y = 10, 10
    enemy = L.Enemy("goblin", "g", 8, 2, 2, notice=5, x=13, y=10)
    game.enemies = [enemy]

    game.enemy_turns()

    assert enemy.alerted


def test_a_wall_between_you_keeps_an_enemy_unaware():
    """Awareness is FOV-based, not distance-based: an enemy three tiles away
    through solid rock has not seen anything."""
    tiles = open_map()
    for y in range(L.MAP_H):
        tiles[y][12] = "#"
    game = make_game(tiles=tiles)
    game.hero.x, game.hero.y = 10, 10
    enemy = L.Enemy("goblin", "g", 8, 2, 2, notice=5, x=14, y=10)
    game.enemies = [enemy]

    game.enemy_turns()

    assert not enemy.alerted


def test_an_alerted_enemy_stays_alerted_out_of_sight():
    """Once it is hunting, breaking line of sight is not enough to call it off."""
    game = make_game(tiles=open_map())
    game.hero.x, game.hero.y = 5, 5
    enemy = L.Enemy("goblin", "g", 8, 2, 2, notice=4, x=40, y=25, alerted=True)
    game.enemies = [enemy]

    game.enemy_turns()

    assert enemy.alerted


def test_an_alerted_enemy_closes_the_distance():
    game = make_game(tiles=open_map())
    game.hero.x, game.hero.y = 10, 10
    enemy = L.Enemy("orc", "o", 14, 3, 3, notice=6, x=15, y=10, alerted=True)
    game.enemies = [enemy]

    before = abs(enemy.x - game.hero.x) + abs(enemy.y - game.hero.y)
    game.enemy_turns()

    assert abs(enemy.x - game.hero.x) + abs(enemy.y - game.hero.y) < before


def test_enemies_do_not_walk_into_each_other():
    game = make_game(tiles=open_map())
    game.hero.x, game.hero.y = 10, 10
    blocker = L.Enemy("orc", "o", 14, 3, 3, notice=6, x=12, y=10, alerted=True)
    follower = L.Enemy("orc", "o", 14, 3, 3, notice=6, x=13, y=10, alerted=True)
    game.enemies = [blocker, follower]

    game.enemy_turns()

    assert (blocker.x, blocker.y) != (follower.x, follower.y)


def test_a_wounded_goblin_runs_rather_than_fights():
    game = make_game(tiles=open_map())
    game.hero.x, game.hero.y = 10, 10
    goblin = L.Enemy("goblin", "g", 8, 2, 2, notice=5, x=11, y=10, alerted=True)
    goblin.hp = 1
    game.enemies = [goblin]
    hp_before = game.hero.hp

    game.enemy_turns()

    assert game.hero.hp == hp_before
    assert (goblin.x, goblin.y) != (11, 10)


def test_a_troll_regenerates_only_when_it_has_not_been_hit():
    game = make_game(tiles=open_map())
    game.hero.x, game.hero.y = 10, 10
    troll = L.Enemy("troll", "T", 22, 4, 5, notice=6, x=20, y=20, alerted=True)
    troll.hp = 10
    troll.regen_suppressed = 1
    game.enemies = [troll]

    game.enemy_turns()
    assert troll.hp == 10  # still recovering from the last blow

    game.enemy_turns()
    assert troll.hp == 12


def test_a_hero_at_zero_hp_dies_from_an_enemy_blow(monkeypatch):
    """The death path writes bones and a dynasty entry; here we only check that
    reaching 0 HP ends the hero rather than leaving them walking at 0."""
    game = make_game(tiles=open_map())
    game.hero.x, game.hero.y = 10, 10
    game.hero.hp = 1
    game.hero.stats.dodge = 0
    game.hero.stats.defense = 0
    game.enemies = [L.Enemy("orc", "o", 14, 5, 3, notice=6, x=11, y=10, alerted=True)]

    deaths = []
    monkeypatch.setattr(L.Game, "hero_dies", lambda self, cause: deaths.append(cause))

    game.enemy_turns()

    assert game.hero.hp <= 0
    assert deaths


# ── FOV, which awareness is built on ───────────────────────────────────────────

def test_fov_stops_at_walls():
    tiles = open_map()
    for y in range(L.MAP_H):
        tiles[y][12] = "#"

    visible = L.compute_fov(tiles, 10, 10, 6)

    assert (11, 10) in visible
    assert (12, 10) in visible      # the wall itself is seen
    assert (13, 10) not in visible  # what is behind it is not


def test_fov_is_bounded_by_its_radius():
    visible = L.compute_fov(open_map(), 30, 15, 4)

    for x, y in visible:
        assert max(abs(x - 30), abs(y - 15)) <= 5


def test_fov_never_leaves_the_map():
    visible = L.compute_fov(open_map(), 0, 0, 8)

    for x, y in visible:
        assert 0 <= x < L.MAP_W and 0 <= y < L.MAP_H


# ── The module split (ROADMAP priority 5, item 11) ─────────────────────────────

def test_the_facade_re_exports_every_public_name_from_every_module():
    """`import lineage` has to keep reaching the whole game.

    This is not a style rule. Splitting the file broke `saga.py` on exactly this
    -- it wanted `FAMILY_NAMES`, which was not on the hand-written list of names
    worth forwarding, and nothing failed until the game was run. A subset chosen
    by hand is a subset that goes stale, so the invariant is parity.
    """
    import inspect

    import content
    import generation
    import models
    import systems

    missing = []
    for module in (content, models, generation, systems):
        for name in dir(module):
            if name.startswith("_") or name == "TYPE_CHECKING":
                continue
            obj = getattr(module, name)
            if inspect.ismodule(obj):
                continue
            # Only names this module actually defines; not what it imported.
            if getattr(obj, "__module__", module.__name__) not in (module.__name__, None):
                continue
            if not hasattr(L, name):
                missing.append(f"{module.__name__}.{name}")

    assert not missing, f"not reachable as lineage.X: {sorted(missing)}"


def test_the_save_paths_are_not_re_exported():
    """The one thing deliberately *not* forwarded.

    A second name bound to the same Path looks redirectable and is not: patch it
    and the code that writes the files carries on writing to `~/.lineage`. The
    test fixture patches `save`, and this keeps the tempting alternative from
    reappearing.
    """
    for name in ("SAVE_DIR", "SAVE_FILE", "BONES_FILE", "DYNASTY_FILE"):
        assert not hasattr(L, name), f"lineage.{name} would be a stale copy of save.{name}"


def test_the_headless_saga_still_runs_on_the_split_modules():
    """`saga.py` is the only consumer of the package besides the game itself,
    and it exercises models, content and progression together."""
    import saga

    random.seed(11)
    lines = saga.run_saga(3)

    assert any("THE CHRONICLE" in line for line in lines)
    assert any("generations" in line for line in lines)
