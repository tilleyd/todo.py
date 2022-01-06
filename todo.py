#!/usr/bin/env python3

import os
import sys
import subprocess
import numpy as np
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from typing import List, Optional, Dict, Tuple
from enum import Enum, auto

class State(Enum):
    DOING = "DOING"
    NEXT = "NEXT"
    TODO = "TODO"
    EVENT = "EVENT"
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


class RepeatType(Enum):
    DAILY = "d"
    WEEKLY = "w"
    MONTHLY = "m"
    YEARLY = "y"


class Repeat:
    period: RepeatType
    every: int

    def __init__(self, period: RepeatType, every: int):
        self.period = period
        self.every = every


class Item:
    category: str
    state: State
    summary: str
    scheduled: Optional[datetime] = None
    deadline: Optional[datetime] = None
    repeat: Optional[Repeat] = None
    repeated: Optional[datetime] = None
    priority: Optional[int] = None
    notes: List[str]
    checklist: List[CheckItem]

    def __init__(self, category: str, state: State, summary: str):
        self.category = category
        self.state = state
        self.summary = summary
        self.notes = []
        self.checklist = []


def c(text: str, fg: Color, bg: Color = Color.NONE):
    return f"{colors_fg[fg]}{colors_bg[bg]}{text}{colors_reset}"


def get_todo_dir() -> str:
    fallback = os.path.join(os.environ["HOME"], ".todo")
    return os.environ.get("TODO_DIRECTORY", fallback)


def get_file(category: str, create: bool = False) -> str:
    path = os.path.join(get_todo_dir(), f"{category}.td")
    if os.path.isfile(path):
        return path
    else:
        if create:
            with open(path, "w") as fd:
                pass
            return path
        else:
            raise FileNotFoundError(f"No such category '{category}'")


def get_all_categories() -> List[str]:
    files = os.listdir(get_todo_dir())
    cats = []
    for f in files:
        if f.endswith(".td"):
            cats.append(f[:-3])
    return cats


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


def next_repeat(item: Item) -> datetime:
    if item.scheduled is None or item.repeat is None:
        return False

    if item.repeat.period == RepeatType.DAILY:
        delta = relativedelta(days=item.repeat.every)
    elif item.repeat.period == RepeatType.WEEKLY:
        delta = relativedelta(weeks=item.repeat.every)
    elif item.repeat.period == RepeatType.MONTHLY:
        delta = relativedelta(months=item.repeat.every)
    elif item.repeat.period == RepeatType.YEARLY:
        delta = relativedelta(years=item.repeat.every)

    if item.repeated is None:
        return item.scheduled

    cast = item.scheduled
    while (cast <= item.repeated):
        cast = cast + delta
    return cast


def repeats_on(item: Item, date: datetime) -> bool:
    if item.scheduled is None or item.repeat is None:
        return False

    if item.repeat.period == RepeatType.DAILY:
        delta = relativedelta(days=item.repeat.every)
    elif item.repeat.period == RepeatType.WEEKLY:
        delta = relativedelta(weeks=item.repeat.every)
    elif item.repeat.period == RepeatType.MONTHLY:
        delta = relativedelta(months=item.repeat.every)
    elif item.repeat.period == RepeatType.YEARLY:
        delta = relativedelta(years=item.repeat.every)

    cast = item.scheduled
    while (cast <= date):
        if same_day(cast, date):
            return True
        else:
            cast = cast + delta
    return False


def is_done(item: Item) -> bool:
    return item.state in [State.DONE, State.CANCELLED]


def parse_category(category: str) -> List[Item]:
    items: List[Item] = []
    item: Optional[Item] = None

    filepath = get_file(category)

    with open(filepath, "r") as fd:
        for line in fd:
            line = line.strip()
            if line == "":
                continue

            tokens = line.split()

            try:
                state = State(tokens[0]) # will except if not a state
                summary = " ".join(tokens[1:])
                item = Item(category, state, summary)
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
                    ridx = value.find("+")
                    if ridx >= 0:
                        # has a repeat
                        repeat = value[ridx + 1:].strip()
                        value = value[:ridx].strip()

                        try:
                            period = RepeatType(repeat[-1])
                            every = int(repeat[:-1])
                            item.repeat = Repeat(period, every)
                        except ValueError:
                            print(f"WARN: Invalid repeat '{repeat}'")
                        
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

                elif key == "repeated:":
                    try:
                        item.repeated = parse_absolute_date(value)
                    except ValueError:
                        print(f"WARN: Invalid repeated date '{value}'")

                elif key == "note:":
                    item.notes.append(value)

                elif key == "[x]" or key == "[]":
                    ci = CheckItem(done=key != "[]", task=value)
                    item.checklist.append(ci)

                else:
                    print(f"WARN: Unknown property '{key}' in category '{category}'")

    return items


def parse_all() -> List[Item]:
    categories = get_all_categories()
    items = []
    for category in categories:
        cat_items = parse_category(category)
        items.extend(cat_items)
    return items


def sort_items(items: List[Item]) -> List[Item]:
    # separate items into the following strata
    todo = []
    scheduled = []
    priority = []
    doing = []
    done = []
    backlog = []

    for item in items:
        if is_done(item):  # DONE, CANCELLED
            done.append(item)
        elif item.state == State.BACKLOG:
            backlog.append(item)
        elif item.state in [State.DOING, State.NEXT]:
            doing.append(item)
        elif item.priority is not None:
            priority.append(item)
        elif item.scheduled is not None or item.deadline is not None:
            scheduled.append(item)
        else:
            todo.append(item)

    # sort priority items
    p_ranks = [i.priority for i in priority]
    priority = [priority[i] for i in np.argsort(p_ranks)]

    # sort todo items according to date
    s_dates = []
    for item in scheduled:
        if item.scheduled is not None:
            if item.repeat is not None:
                s_dates.append(next_repeat(item))
            else:
                s_dates.append(item.scheduled)
        else:
            assert item.deadline is not None
            s_dates.append(item.deadline)
    scheduled = [scheduled[i] for i in np.argsort(s_dates)]

    sorted_items = doing
    sorted_items.extend(priority)
    sorted_items.extend(scheduled)
    sorted_items.extend(todo)
    sorted_items.extend(backlog)
    sorted_items.extend(done)
    return sorted_items


def display_item(
    item: Item,
    short: bool = False,
    ignore_dates: bool = False,
    ignore_category: bool = False,
):
    token_color = Color.NONE
    summary_color = Color.NONE
    if item.state in [State.DOING, State.NEXT]:
        token_color = Color.GREEN
    elif item.state in [State.TODO, State.EVENT]:
        token_color = Color.YELLOW
    elif item.state in [State.WAITING, State.HELD]:
        token_color = Color.RED
    elif item.state in [State.DONE]:
        token_color = Color.BLUE
        summary_color = Color.DIM
    else:
        token_color = Color.DIM
        summary_color = Color.DIM
    print(c(item.state.value, token_color), end=" ")
    if not ignore_category:
        print(c(item.category, Color.DIM), end=" ")
    if item.priority is not None:
        print(c(f"[{item.priority}]", Color.RED), end=" ")
    print(c(item.summary, summary_color))

    if short:
        return

    if len(item.checklist) > 0:
        for check in item.checklist:
            mark = c("●", Color.GREEN) if check.done else c("○", Color.RED)
            print(f"  {mark} {check.task}")

    if len(item.notes) > 0:
        for note in item.notes:
            print(c(f"  - {note}", Color.DIM))

    if ignore_dates:
        return

    if item.scheduled is not None:
        if item.repeat is not None:
            next_date = next_repeat(item)
            print(f"  Repeats {fmt_relative_date(next_date)} (+{item.repeat.every} {item.repeat.period.name.lower()})")
            if item.repeated is not None:
                print(f"  Last done {fmt_relative_date(item.repeated)}")
        else:
            print(f"  Scheduled {fmt_relative_date(item.scheduled)}")

    if item.deadline is not None:
        print(f"  Due {fmt_relative_date(item.deadline)}")


def display_agenda(items: List[Item], date: Optional[datetime] = None):
    if date is None:
        showing_today = True
        date = datetime.now()
    else:
        showing_today = False
    print(c(date.strftime('%a %d %b %Y'), Color.BLUE))

    doing: List[Item] = []
    scheduled: List[Item] = []
    deadlines: List[Item] = []
    overdue: List[Item] = []

    for item in items:

        if item.state in [State.DOING, State.NEXT]:
            doing.append(item)

        if item.scheduled is not None:
            if item.repeat is not None:
                if item.repeated is not None:
                    if same_day(item.repeated, date) or item.repeated > date:
                        item.state = State.DONE

                if repeats_on(item, date):
                    scheduled.append(item)
                elif not is_done(item) and next_repeat(item) < date:
                    overdue.append(item)

            elif same_day(item.scheduled, date):
                scheduled.append(item)
            elif not is_done(item) and item.scheduled < date:
                overdue.append(item)

        if item.deadline is not None:
            delta = item.deadline - date
            if same_day(item.deadline, date) or (delta.days < deadline_warning and delta.days >= 0):
                deadlines.append(item)
            elif not is_done(item) and item.deadline < date:
                overdue.append(item)
    
    if showing_today:
        if len(doing) > 0:
            print(f"\n{c('Active items', Color.YELLOW)}")
            for item in doing:
                display_item(item, ignore_dates=True)

        if len(overdue) > 0:
            print(f"\n{c('Overdue items', Color.RED)}")
            for item in overdue:
                display_item(item)

    if len(scheduled) > 0:
        print(f"\n{c('Agenda', Color.YELLOW)}")
        for item in scheduled:
            if item.scheduled.hour == 0 and item.scheduled.minute == 0:
                time = "--:--"
            else:
                time = item.scheduled.strftime("%H:%M")
            print(time, end=" ")
            display_item(item, ignore_dates=True)
    else:
        print(c("\nNo scheduled items", Color.GREEN))

    if len(deadlines) > 0:
        print(f"\n{c('Upcoming deadlines', Color.YELLOW)}")
        for item in deadlines:
            print(fmt_relative_date(item.deadline), end=" ")
            display_item(item, ignore_dates=True)
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
        items = sort_items(parse_all())
        display_agenda(items, date)

    elif command in ["list", "ls"]:
        if len(sys.argv) == 3:
            category = sys.argv[2]
            items = sort_items(parse_category(category))
            for item in reversed(items):
                display_item(item, ignore_category=True)
        else:
            items = sort_items(parse_all())
            for item in reversed(items):
                display_item(item)

    elif command in ["open", "o"]:
        if len(sys.argv) < 3:
            print(f"Usage: {sys.argv[0]} {command} <category>")
            exit(1)
        category = sys.argv[2]
        try:
            category_file = get_file(category)
        except FileNotFoundError:
            ans = input(f"Create category {c(category, Color.BLUE)}? Y/N ")
            if ans.lower() == "y":
                os.makedirs(get_todo_dir(), exist_ok=True)
                category_file = get_file(category, create=True)
            else:
                exit(1)
        editor = os.environ.get("EDITOR", "vim")
        subprocess.call([editor, category_file])

    elif command in ["help", "h"]:
        # TODO
        print("HELP")

    else:
        print(f"Unknown command '{command}'")
        print(f"Use {sys.argv[0]} h for a list of commands.")
        exit(1)


if __name__ == "__main__":
    main()
