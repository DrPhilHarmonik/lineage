"""Progression maths.

Levels are derived from total XP rather than stored, so a save can be restated
on a changed curve instead of carrying stats no current level would grant. That
is what `progression_from_total_xp` is for, and why the level bonuses are pure
functions of level: `Game.gain_xp` and the save migration both apply them, and
they must agree.
"""

from __future__ import annotations

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
