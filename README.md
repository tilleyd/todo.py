# ✅ todo.py

Inspired by todo.txt and Emacs org-mode, `todo.py` is a simple CLI utility to
manage your todo lists in a series of plaintext files.

* [Installation](#installation)
* [Usage](#usage)
* [File Format](#file-format)
  * [Tasks](#tasks)
  * [Scheduled](#scheduled)
  * [Deadline](#deadline)
  * [Priority](#priority)
  * [Notes](#notes)
  * [Checklists](#checklists)
  * [Repeats](#repeats)

## Installation

Simply copy the `todo.py` file somewhere safe, e.g. for system-wide
installation:

```bash
git clone git://github.com/tilleyd/todo.py
sudo cp todo.py /usr/local/bin/
```

Add the following alias to your `.bashrc` for less typing:

```bash
alias t='/usr/local/bin/todo.py'
```

## Usage

The application does not automatically modify the todo files in any way. You are
expected to manually edit them using the defined [file format](#file-format).

Each category (e.g. `personal` and `work`) is located in its own `.td` file in
the todo directory. By default this will be `~/.todo`, but it can be set with
the `TODO_DIRECTORY` environment variable.

To edit a file, you can either directly edit the files, or use

```bash
t o <category>
```

to open the file `category.td` with the editor set by the `EDITOR` environment variable.

You can list all entries for a category:

```bash
t ls <category>
```

or list all entries:

```bash
t ls
```

The core feature of `todo.py` is the agenda view. You can see today's agenda
with

```bash
t a
```

or a specific date's with

```bash
t a "dd Mmm YYYY" # e.g. t a "5 Sep 2021"
```

or a date relative to today with

```bash
t a <int> # e.g. t a 1, or t a -2
```

## File Format

### Tasks

Each task starts with a state, and is followed by a summary, all on a single
line. Valid states are `DOING`, `NEXT`, `TODO`, `EVENT`, `WAITING`, `HELD`,
`BACKLOG`, `DONE`, and `CANCELLED`. A most basic setup will only need `TODO` and
`DONE`.

Empty lines and lines that don't start with a state or a `*` are ignored.

### Scheduled

A task can be scheduled by giving it a date. This allows it to appear in the
agenda view for that day.

```
TODO A scheduled task
* SCHEDULED: 4 May 2021 09:00
```

The time is optional:

```
* SCHEDULED: 4 May 2021
```

The only supported date formats are `%d %b %Y` and `%d %B %Y` (e.g. `1 Dec 2021`
or `01 December 2021`).

### Deadline

A task can be given a deadline. A task with a deadline will start appearing in
the agenda 7 days before the deadline.

```
TODO A task with a deadline
* DEADLINE: 4 May 2021
```

The date format is similar to that of the schedule.

### Priority

A task can be given a priority, which orders them in the agenda view:

```
TODO An important task
* PRIORITY: 1
```

A lower number is higher priority and you can use arbitrary numbers. Any
priority is considered higher priority than no priority.

### Notes

You can add multiple notes to a task:

```
TODO A noteworthy task
* NOTE: Maybe this isn't a good idea.
* NOTE: Or maybe it is.
```

### Checklists

You can add checked items to a task:

```
TODO A piecewise task
* [] An unfinished part
* [X] A finished part
```

Note that currently a space in the unfinished `[]` is unsupported. Checklists
are simply there for indication, and don't affect the state of the item in any
way.

### Repeats

A task can be repeated by adding a repeat modifier to a scheduled date:

```
TODO A repeated task
* SCHEDULED: 1 May 2021 +2w
```

The example above will repeat every 2 weeks. Valid repeat periods are `d`, `w`,
`m`, and `y`, for daily, weekly, monthly, and yearly repeats, respectively.

In order to mark a repeated task as done, you must add a `repeated` property
indicating the last repeated date, rather than changing the state to done. The
task will be shown as done in the agenda on any days on or before the last
repeated date.

```
TODO A repeated task
* SCHEDULED: 1 May 2021 +2w
* REPEATED: 15 May 2021
```
