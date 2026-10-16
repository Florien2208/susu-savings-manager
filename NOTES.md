# Notes

## Assumptions

Where the brief was silent, I chose the following rules. Each is enforced in
`susu/group.py` and covered by a test.

1. **One group per program.** The tracker manages a single group, as the brief
   says. `create` is refused if a group already exists.
2. **Membership locks when money starts moving.** Members can be added only
   before the first payment is recorded. Adding someone mid-cycle would change
   the pot size for weeks already in progress and push them to the end of a
   queue others have already paid into, so the fair answer is a new cycle.
3. **At least two members.** A susu with one person is just saving, so payments
   and closing a week require two or more members.
4. **Member names are unique ignoring case and extra spaces.** `Ama`, `ama` and
   `  AMA ` are the same person. The name is stored as first typed, and lookups
   (`pay ama 50`) are case-insensitive.
5. **Payments go to the current week only.** A closed week is by definition
   fully paid, and future weeks are not open, so paying ahead is refused. The
   optional `week` argument on `pay` exists so a caller can state which week
   they mean and get an error if the group has moved on, instead of the money
   silently landing in a different week.
6. **"Payments above what a member owes"** means above what is still owed for
   that week: with 50.00 due and 30.00 paid, 20.00 is accepted and 20.01 is
   refused. A member who has paid in full cannot pay again that week. A refused
   payment changes nothing.
7. **Amounts have at most two decimal places.** `10.005` is rejected, not
   rounded. Zero and negative amounts are rejected for payments and for the
   weekly contribution.
8. **Closing a week that cannot close is not an error in the model.** It returns
   a result listing everyone who still owes (including people who have paid
   nothing). No payout is made and the week stays open. The CLI prints the list
   and, in one-shot mode, exits with code 1 so scripts can tell.
9. **The cycle ends after every member has received the pot once.** After the
   last payout, the group reports "cycle complete" and refuses further payments
   or closes. Starting a second cycle is out of scope.
10. **Pot = weekly amount × number of members**, paid in full to one member.
    The recipient also contributes that week, which is how a susu works.

## Decisions

- **Python, standard library only.** Nothing to install, runs anywhere with
  Python 3.10+, and `unittest` is enough for the tests.
- **Money as integer pesewas.** `Money` wraps an `int` count of pesewas, so
  addition and multiplication are exact. Text is parsed with a strict pattern
  and `Decimal`, never `float`. Saved files store amounts as strings
  (`"50.00"`) and re-parse them on load. There is a test that 0.10 + 0.20 is
  exactly 0.30 and that 1,000 one-pesewa payments make exactly 10.00.
- **Domain separate from input/output.** `SusuGroup` holds all the rules and
  returns plain result objects (`CloseResult`, `Report`, `Debt`, `Payout`).
  The CLI only parses text and formats output, so adding an API later means
  writing a new front end, not touching the rules.
- **One exception type per rule** (`UnknownMemberError`, `DuplicateMemberError`,
  `InvalidAmountError`, `OverpaymentError`, `GroupStateError`), all under
  `SusuError`. Tests assert the exact kind of failure, and the CLI catches the
  base class to show a readable message instead of a stack trace.
- **Interactive shell plus one-shot mode.** The shell (`cmd.Cmd`) is the easy
  way to try it. `--state FILE` adds saving, and passing a command after it runs
  just that command, which makes the program scriptable and testable from the
  outside. State files are written atomically (temp file then rename).
- **Payment history per week is kept**, not just the current week, so the data
  is there for an audit trail even though the report only needs the current
  week.

## What I would improve with more time

- **Record each payment as its own event** (who, how much, when) instead of a
  running total per week, so the report could show the payment history, and
  mistakes could be reversed with a correcting entry.
- **Validate loaded state.** Loading trusts the JSON file. A hand-edited file
  could break invariants (e.g. a payout to a non-member); I would re-check the
  rules on load.
- **Missed payments and penalties.** Real groups deal with members who cannot
  pay: allow someone else to cover them, carry a debt forward, or apply a fine.
- **Multiple cycles and multiple groups**, with members choosing their payout
  position or swapping positions by agreement.
- **Dates.** Tie weeks to calendar dates so the tracker can say a week is late.
- **A small HTTP API** over the same `SusuGroup` model, with the JSON storage
  replaced by SQLite for safe concurrent use.
- **Packaging** with a `pyproject.toml` entry point so it installs as a `susu`
  command.
