# Susu Group Tracker

A small command-line program that manages one rotating savings group (susu).
Every member pays the same fixed amount each week; each week the whole pot goes
to one member, in the order they joined.

Written in Python using only the standard library — there is nothing to install.

## Requirements

- Python 3.10 or newer (`python --version`)

## Run it

From the repository root:

```bash
python -m susu
```

This opens an interactive shell:

```
susu> create 50.00
susu> add Ama
susu> add Kofi
susu> add Esi
susu> pay Ama 50
susu> pay Kofi 50
susu> pay Esi 30
susu> close
Week 1 cannot close. No payout was made.
  Esi owes 20.00
susu> pay Esi 20
susu> close
Week 1 closed. Ama receives GHS 150.00.
Week 2 begins.
susu> report
```

The interactive shell keeps the group in memory only. To keep it between runs,
pass a state file:

```bash
python -m susu --state group.json
```

You can also run single commands against a state file, which is handy for
scripting. The exit code is `0` on success and `1` if the command was refused
(including a week that cannot close):

```bash
python -m susu --state group.json create 50.00
python -m susu --state group.json add Ama
python -m susu --state group.json pay Ama 50
python -m susu --state group.json report
```

To replay the example from the brief in one go:

```bash
python -m susu < examples/brief-example.txt
```

### Commands

| Command | What it does |
| --- | --- |
| `create <amount>` | Create the group with a fixed weekly contribution in GHS, e.g. `create 50.00` |
| `add <name>` | Add a member. Quote names with spaces: `add "Kofi Mensah"` |
| `pay <name> <amount> [week]` | Record a full or partial payment for the current week |
| `close` | Close the week: pay out if everyone paid in full, otherwise list who owes what |
| `report` | Current week, who has paid in full, who owes what, payout history |
| `help [command]` | Show help |
| `quit` | Exit |

Amounts are GHS with up to two decimal places (`50`, `50.5`, `50.00`, `GHS 50`).

## Run the tests

```bash
python -m unittest discover -v
```

The suite (35 tests) covers money arithmetic, every validation rule, partial
payments, the week-cannot-close case, the full example from the brief, a full
payout cycle, the report, the CLI and saving/loading. It also runs on GitHub
Actions for Python 3.10, 3.12 and 3.13 on every push.

## Project layout

```
susu/
  money.py     Money type: exact amounts stored as integer pesewas
  group.py     SusuGroup: all the rules (members, payments, closing, report)
  errors.py    One exception type per kind of rule violation
  cli.py       Interactive shell and one-shot command runner (text in, text out)
  storage.py   Save/load the group as JSON
tests/         unittest suites, one per module
examples/      Script replaying the example from the brief
NOTES.md       Assumptions, decisions, and what I would improve
```

The rules live only in `group.py`, which does no input or output. The CLI is a
thin layer on top, so the same model could be put behind an API without change.

See [NOTES.md](NOTES.md) for assumptions and design decisions.
