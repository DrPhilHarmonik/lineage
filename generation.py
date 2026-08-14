"""Floor construction and field of view.

`generate_dungeon` is the one place that decides where anything is, so the
placement invariants -- nothing shares a tile, nothing lands in a wall -- are
enforced here through a single `occupied` set rather than by each caller.
"""

from __future__ import annotations

import math
import random

from content import ENEMY_NAMES, FLOOR_ENEMIES, FLOOR_ITEMS, ROOM_INSCRIPTIONS
from models import Bones, Enemy, Item, Rect

MAP_W, MAP_H = 60, 30
MIN_ROOMS, MAX_ROOMS = 6, 12
ROOM_MIN, ROOM_MAX = 4, 10

def make_enemy(kind: tuple, floor: int) -> "Enemy":
    name, glyph, hp, attack, xp, notice = kind
    title = random.choice(ENEMY_NAMES.get(name, [""])) if random.random() < 0.4 else ""
    return Enemy(name, glyph, hp, attack, xp, notice, title=title)


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
