# ✅ Todo

Inspired by todo.txt and Emacs org-mode, Todo is a simple CLI utility to manage
your todo lists in a series of plaintext files.

[[toc]]

## Installation

Simply copy the `todo.py` file somewhere safe, e.g. for system-wide
installation:

```bash
sudo cp todo.py /usr/local/bin/
```

Add the following alias to your `.bashrc` for less typing:

```bash
alias t='/usr/local/bin/todo.py'
```

## Usage

Add a new item to the file `category.txt`:

```
t a <category> <task...>
```

List the entries from the file `category.txt`:

```
t ls <category>
```

Open the file `category.txt` for viewing and editing:

```
t o <category>
```

This will first display the entries from the category and present a prompt to
work with entries. The prompt will allow you to modify, add or remove, schedule,
set the states of entries, and more.

## File Format

### Scheduled

A task can be scheduled by giving it a date. This allows it to appear in the
agenda view.

```
TODO A scheduled task
* SCHEDULED: 4 May 2021 09:00
```

The time is optional:

```
* SCHEDULED: 4 May 2021
```

And the time can also be given a range:

```
* SCHEDULED: 4 May 2021 09:00-11:30
```

This is the only date format supported, since it is very readable and
simplifies the implementation considerably.

### Deadline

A task can be given a deadline. A task with a deadline will start appearing in
the agenda 3 days before the deadline.

```
TODO A task with a deadline
* DEADLINE: 4 May 2021
```

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
are simply there for indication, and doesn't do any automagic with the item
state if you finish all items.
