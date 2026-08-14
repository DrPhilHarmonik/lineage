"""Persistence: where the files are, and reading and writing them.

This module owns the save paths, and nothing else in the game refers to them
directly -- callers ask `saved_game_exists()` or `read_save_data()` instead.
That indirection is not decoration: the paths are module-level constants
pointing at a real `~/.lineage`, and a test that redirects them somewhere else
has to redirect the binding the writer actually reads. Re-exporting them
elsewhere would create a second name that looks redirected and is not.

Serialising a `Game` is deliberately *not* here -- that needs to know what a
game is made of, so it lives in `game`. This module knows about bones, dynasty
records, and JSON.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from models import Bones

SAVE_DIR = Path("~/.lineage").expanduser()
BONES_FILE = SAVE_DIR / "bones.json"
DYNASTY_FILE = SAVE_DIR / "dynasty.json"
SAVE_FILE = SAVE_DIR / "save.json"


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


def saved_game_exists() -> bool:
    return SAVE_FILE.exists()


def write_save_data(data: dict) -> None:
    ensure_save_dir()
    SAVE_FILE.write_text(json.dumps(data))


def read_save_data() -> dict | None:
    """The saved run as raw JSON, or None if there isn't one worth reading.

    A save that will not parse is deleted rather than returned: it costs the run
    in progress, which is already lost, instead of the game.
    """
    if not SAVE_FILE.exists():
        return None
    try:
        return json.loads(SAVE_FILE.read_text())
    except Exception:
        delete_save()
        return None


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
