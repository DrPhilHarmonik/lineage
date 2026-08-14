"""Curses drawing helpers shared by every screen."""

from __future__ import annotations

import curses

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
