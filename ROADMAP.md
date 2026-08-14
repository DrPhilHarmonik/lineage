# LINEAGE Roadmap

## Goal

Preserve the current tone and lineage fantasy while making the game mechanically trustworthy, tactically clearer, and easier to extend.

## Priority 1: Fix Core System Trust -- DONE

- [x] `Quick Feet` and speed bonuses affect turn economy
- [x] `Quiet Step` reduces enemy detection range
- [x] `Killing Blow` provides an opening-combat advantage
- [x] Enemy awareness uses per-enemy notice radius and FOV, not hero vision
- [x] Enemies track alerted state; alert messages on first notice
- [x] XP-based level progression with automatic stat bonuses
- [x] Fix: seen/visited_rooms cleared on floor transition (tiles bled between floors)
- [x] Fix: dungeon generation tracks occupied tiles -- enemies, bones, items no longer stack

## Priority 2: Improve Tactical Depth

### Enemy identity -- DONE
- [x] Rats hesitate 30% of the time when not adjacent
- [x] Goblins flee at below 25% HP
- [x] Zombies are immune to killing_blow stagger
- [x] Trolls regenerate 2 HP/turn unless hit recently
- [x] Dark elves attack from range (up to 4 tiles) and retreat when adjacent
- [x] Kobolds gain +1 attack per nearby alerted ally

### Equipment and carry -- DONE
- [x] Weight system (CARRY_MAX = 20 lbs) replaces flat slot cap
- [x] Each item has a weight; heavy armor meaningfully limits consumable capacity
- [x] Consumables stack in inventory display (x3 Healing Potion = 3lb)
- [ ] Meaningful tradeoffs beyond linear stat upgrades (cursed/storied items, slot competition)

### Recovery and attrition -- DONE
- [x] Wait (.) no longer heals; rest (r) is the only passive recovery

## Priority 3: Deliver the Promise of the Premise

### End-state -- DONE
- [x] Floor 5 stair triggers win screen instead of loading phantom floor 6
- [x] Win screen shows hero, generation count, WIN_LINES narrative
- [x] Win recorded in dynasty and bones; chronicle shows "Reached the bottom"

### Lineage consequences -- DONE
- [x] Ancestor relics: equipped items saved to bones, recoverable by heirs
- [x] Bloodline skill accumulation: gen 3+ inherits extra skill from deepest ancestor; gen 6+ inherits two extras
- [x] Dynasty context on intro screen: souls sent, deepest floor, winner acknowledgment
- [x] Named ancestors in gameplay: floor arrival, level-up, kill echo messages
- [ ] Bloodline perks from milestone generations (gen 5, 10, etc.)
- [ ] Family relics that persist across all runs (not just from bones)
- [ ] Chronicle-based unlocks or house reputation

## Priority 4: Improve Map and Content Quality

### Placement -- DONE
- [x] Shared occupied-tile tracker prevents overlapping enemy/item/bones placement

### Autoexplore -- DONE
- [x] No longer stops on visible items -- walks through and auto-collects
- [x] Stops when pack is too heavy to carry any remaining floor item
- [ ] Prioritize visible loot and unexamined bones as secondary targets
- [ ] Authored rooms or set-piece events (beyond random inscriptions)

## Priority 5: Reduce Code Friction

### 11. Split the single-file implementation
- Suggested modules:
  - `content.py` for skills, items, names, text pools
  - `models.py` for dataclasses
  - `generation.py` for rooms and floor construction
  - `systems.py` for combat, AI, progression
  - `ui.py` for curses drawing and panels
  - `save.py` for persistence

### 12. Add lightweight regression coverage -- DONE
- [x] Hero stat application
- [x] Progression thresholds
- [x] Save/load compatibility
- [x] Dungeon placement invariants
- [x] Enemy awareness behavior

`python3 -m pytest test_lineage.py` -- 84 tests, no curses, no terminal. Every
test runs against a temporary save directory, so a run can never overwrite the
real bones and dynasty in `~/.lineage`.

The suite was checked against deliberate regressions rather than assumed to
work: breaking the XP curve, letting placement stack entities on one tile, and
making enemies notice through walls each fail it.

One thing it found and does not fix, because the call is a design one:
**re-applying a skill stacks its stats.** `apply_skill` de-duplicates the skill
list but not the bonus, so inheriting a skill the hero already has grants it
twice -- invisible on the character sheet, permanent on the stats.
`test_applying_the_same_skill_twice_stacks_its_stats` pins the current
behaviour; if re-learning should be a no-op, change that test first.
