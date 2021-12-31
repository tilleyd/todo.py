#!/usr/bin/env python3

import os
import sys
import subprocess
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Tuple
from enum import Enum, auto

class State(Enum):
    DOING = "DOING"
    NEXT = "NEXT"
    TODO = "TODO"
    WAITING = "WAITING"
    HELD = "HELD"
    BACKLOG = "BACKLOG"
    DONE = "DONE"
    CANCELLED = "CANCELLED"


class Color(Enum):
    NONE = auto()  # The default color
    RED = auto()
    GREEN = auto()
    BLUE = auto()
    YELLOW = auto()
    CYAN = auto()
    MAGENTA = auto()
    WHITE = auto()
    BLACK = auto()
    DIM = auto()


colors_fg = {
    Color.NONE: "",
    Color.BLACK: "\033[30m",
    Color.RED: "\033[31m",
    Color.GREEN: "\033[32m",
    Color.YELLOW: "\033[33m",
    Color.BLUE: "\033[34m",
    Color.MAGENTA: "\033[35m",
    Color.CYAN: "\033[36m",
    Color.WHITE: "\033[37m",
    Color.DIM: "\033[2;37m",
}

colors_bg = {
    Color.NONE: "",
    Color.RED: "!",
    Color.GREEN: "!",
    Color.BLUE: "!",
    Color.YELLOW: "!",
    Color.CYAN: "!",
    Color.MAGENTA: "!",
    Color.WHITE: "!",
    Color.BLACK: "!",
    Color.DIM: "!",
}

colors_reset = "\033[00m"

date_formats = [
    "%d %b %Y", # 1 Jan 2021
    "%d %B %Y", # 1 January 2021
    "%d %b %Y %H:%M", # 1 Jan 2021 09:00
    "%d %B %Y %H:%M", # 1 January 2021 09:00
]

deadline_warning = 7  # days from deadline


class CheckItem:
    done: bool
    task: str

    def __init__(self, done: bool, task: str):
        self.done = done
        self.task = task


class Item:
    state: State
    summary: str
    scheduled: Optional[datetime] = None
    deadline: Optional[datetime] = None
    priority: Optional[int] = None
    notes: List[str]
    checklist: List[CheckItem]
    repeats: List[str]

    def __init__(self, state: State, summary: str):
        self.state = state
        self.summary = summary
        self.notes = []
        self.checklist = []
        self.repeats = []


def c(text: str, fg: Color, bg: Color = Color.NONE):
    return f"{colors_fg[fg]}{colors_bg[bg]}{text}{colors_reset}"


def get_todo_dir():
    fallback = os.path.join(os.environ["HOME"], ".todo")
    return os.environ.get("TODO_DIRECTORY", fallback)


def parse_absolute_date(string: str) -> datetime:
    d = None
    for fmt in date_formats:
        try:
            d = datetime.strptime(string, fmt)
            break
        except ValueError:
            pass
    if d is None:
        raise ValueError(f"Invalid absolute date string '{string}'")
    return d


def fmt_absolute_date(date: datetime) -> str:
    if date.hour == 0 and date.minute == 0:
        return date.strftime("%a %d %b %Y")
    else:
        return date.strftime("%a %d %b %Y %H:%M")


def parse_relative_date(string: str) -> datetime:
    string = string.strip().lower()
    try:
        return parse_absolute_date(string)
    except ValueError:
        try:
            days = int(string)
            return datetime.now() + timedelta(days=days)
        except ValueError:
            raise ValueError(f"Invalid relative date string '{string}'")


def fmt_relative_date(date: datetime) -> str:
    today = datetime.now()
    if same_day(date, today):
        if date.hour == 0 and date.minute == 0:
            return "Today"
        else:
            return "Today " + date.strftime("%H:%M")
    else:
        return fmt_absolute_date(date)


def same_day(date1: datetime, date2: datetime):
    return all(
        [
            date1.day == date2.day,
            date1.month == date2.month,
            date1.year == date2.year,
        ]
    )


def parse_file(filepath: str) -> List[Item]:
    items: List[Item] = []
    item: Optional[Item] = None

    with open(filepath, "r") as fd:
        for line in fd:
            line = line.strip()
            if line == "":
                continue

            tokens = line.split()

            try:
                state = State(tokens[0]) # will except if not a state
                summary = " ".join(tokens[1:])
                item = Item(state, summary)
                items.append(item)
                continue
            except ValueError:
                if tokens[0] != "*" or item is None:
                    continue

                if (len(tokens) < 2):
                    continue

                key = tokens[1].lower()
                value = " ".join(tokens[2:])
                
                if key == "scheduled:":
                    try:
                        item.scheduled = parse_absolute_date(value)
                    except ValueError:
                        print(f"WARN: Invalid schedule date '{value}'")

                elif key == "deadline:":
                    try:
                        item.deadline = parse_absolute_date(value)
                    except ValueError:
                        print(f"WARN: Invalid deadline date '{value}'")

                elif key == "priority:":
                    try:
                        item.priority = int(value)
                    except ValueError:
                        print(f"WARN: Invalid priority '{value}'")

                elif key == "repeat:":
                    item.repeats.append(value)

                elif key == "note:":
                    item.notes.append(value)

                elif key == "[x]" or key == "[]":
                    ci = CheckItem(done=key != "[]", task=value)
                    item.checklist.append(ci)

                else:
                    print(f"WARN: Unknown property '{key}'")

    # sort by priority
    # TODO
    # sort by state
    # TODO

    return items


def parse_files(filepaths: List[str]) -> Dict[str, List[Item]]:
    items = {}
    for filepath in filepaths:
        file_items = parse_file(filepath)
        category = filepath[:-4] if filepath.endswith(".txt") else filepath
        items[category] = file_items
    return items


def display_item(item: Item, short: bool = False, ignore_dates: bool = False):
    token_color = Color.NONE
    summary_color = Color.NONE
    if item.state in [State.DOING, State.NEXT]:
        token_color = Color.GREEN
    elif item.state in [State.TODO]:
        token_color = Color.YELLOW
    elif item.state in [State.WAITING, State.HELD]:
        token_color = Color.RED
    elif item.state in [State.DONE]:
        token_color = Color.BLUE
        summary_color = Color.DIM
    else:
        token_color = Color.DIM
        summary_color = Color.DIM
    print(f"{c(item.state.value, token_color)} {c(item.summary, summary_color)}")

    if short:
        return

    if len(item.checklist) > 0:
        for check in item.checklist:
            mark = c("●", Color.GREEN) if check.done else c("○", Color.RED)
            print(f"  {mark} {check.task}")

    if len(item.notes) > 0:
        for note in item.notes:
            print(c(f"  - {note}", Color.DIM))

    if item.scheduled is not None and not ignore_dates:
        print(f"  Scheduled {fmt_relative_date(item.scheduled)}")

    if item.deadline is not None and not ignore_dates:
        print(f"  Due {fmt_relative_date(item.deadline)}")


def display_items(items: List[Item]):
    for item in reversed(items):
        display_item(item)


def display_categories(items: Dict[str, List[Item]]):
    for cat, cat_items in items.items():
        print(f"{cat.upper()}\n")
        display_items(cat_items)


def display_agenda(items: Dict[str, List[Item]], date: Optional[datetime] = None):
    if date is None:
        date = datetime.now()
    print(c(date.strftime('%a %d %b %Y'), Color.BLUE))

    scheduled: List[Tuple[str, Item]] = []
    deadlines: List[Tuple[str, Item]] = []

    for category, cat_items in items.items():
        for item in cat_items:

            if item.scheduled is not None:
                if same_day(item.scheduled, date):
                    scheduled.append((category, item))

            if item.deadline is not None:
                delta = item.deadline - date
                if delta.days < deadline_warning and delta.days >= 0:
                    deadlines.append((category, item))

    if len(scheduled) > 0:
        print(f"\n{c('Agenda', Color.YELLOW)}")
        for cat, item in scheduled:
            if item.scheduled.hour == 0 and item.scheduled.minute == 0:
                time = "--:--"
            else:
                time = item.scheduled.strftime("%H:%M")
            print(time, c(cat, Color.DIM), end=" ")
            display_item(item, ignore_dates=True)
    else:
        print(c("\nNo scheduled items", Color.GREEN))

    if len(deadlines) > 0:
        print(f"\n{c('Upcoming deadlines', Color.YELLOW)}")
        for cat, item in deadlines:
            print(fmt_relative_date(item.deadline), c(cat, Color.DIM), end=" ")
            display_item(item, short=True)
    else:
        print(c("\nNo upcoming deadlines", Color.GREEN))

def main() -> None:
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <command>")
        print(f"Use {sys.argv[0]} h for a list of commands.")
        exit(1)

    command = sys.argv[1]

    if command in ["agenda", "a"]:
        date = None
        if len(sys.argv) == 3:
            try:
                date = parse_relative_date(sys.argv[2])
            except ValueError as e:
                print(str(e))
                exit(1)

        # TODO get all files
        items = parse_files(["personal.txt"])

        display_agenda(items, date)

    elif command in ["list", "ls"]:
        if len(sys.argv) == 3:
            category = sys.argv[2]
            # TODO check validity of category
            items = parse_file(f"{category}.txt")
            display_items(items)
        else:
            # TODO get all files
            items = parse_files(["personal.txt"])
            display_categories(items)

    elif command in ["open", "o"]:
        if len(sys.argv) < 3:
            print(f"Usage: {sys.argv[0]} {command} <category>")
            exit(1)
        category = sys.argv[2]
        editor = os.environ.get("EDITOR", "vim")
        subprocess.call([editor, f"{category}.txt"])

    elif command in ["help", "h"]:
        # TODO
        print("HELP")

    else:
        print(f"Unknown command '{command}'")
        print(f"Use {sys.argv[0]} h for a list of commands.")
        exit(1)


if __name__ == "__main__":
    main()
