"""Command-line front end: an interactive shell plus one-shot commands.

All rules live in ``susu.group``; this module only parses text, calls the
domain and prints results.
"""

from __future__ import annotations

import cmd
import shlex
import sys
from typing import TextIO

from susu.errors import SusuError
from susu.group import CloseResult, Report, SusuGroup
from susu.money import Money


def render_close(result: CloseResult) -> str:
    if not result.closed:
        lines = [f"Week {result.week} cannot close. No payout was made."]
        lines += [f"  {debt.member} owes {debt.owes}" for debt in result.outstanding]
        return "\n".join(lines)
    lines = [f"Week {result.week} closed. {result.payout.member} receives {result.payout.amount.with_currency()}."]
    if result.cycle_complete:
        lines.append("Every member has now received the pot. The cycle is complete.")
    else:
        lines.append(f"Week {result.week + 1} begins.")
    return "\n".join(lines)


def render_report(report: Report) -> str:
    lines = []
    if report.cycle_complete:
        lines.append(f"Cycle complete after {len(report.payouts)} weeks.")
    else:
        lines.append(f"Current week: {report.week}")
        lines.append(f"Weekly contribution: {report.contribution.with_currency()}")
        lines.append(f"Pot this week: {report.pot.with_currency()} -> {report.next_recipient or '(no members)'}")
    lines.append(f"Members ({len(report.members)}): {', '.join(report.members) or '(none)'}")

    if not report.cycle_complete:
        lines.append("Paid in full:")
        lines += [f"  {name}" for name in report.paid_in_full] or ["  (nobody yet)"]
        lines.append("Still owes:")
        lines += [f"  {d.member} owes {d.owes} (paid {d.paid})" for d in report.owing] or ["  (nobody)"]

    lines.append("Payout history:")
    lines += [
        f"  Week {p.week}: {p.member} received {p.amount.with_currency()}" for p in report.payouts
    ] or ["  (no payouts yet)"]
    return "\n".join(lines)


class SusuShell(cmd.Cmd):
    intro = "Susu Group Tracker. Type 'help' for commands, 'quit' to exit."
    prompt = "susu> "

    def __init__(self, group: SusuGroup | None = None, stdout: TextIO | None = None) -> None:
        super().__init__(stdout=stdout)
        self.group = group
        self.last_error: str | None = None

    # -------------------------------------------------------------- helpers

    def say(self, text: str) -> None:
        self.stdout.write(text + "\n")

    def fail(self, message: str) -> None:
        self.last_error = message
        self.say(f"Error: {message}")

    def onecmd(self, line: str) -> bool:
        self.last_error = None
        try:
            return super().onecmd(line)
        except SusuError as exc:
            self.fail(str(exc))
            return False

    def _args(self, arg: str) -> list[str] | None:
        try:
            return shlex.split(arg)
        except ValueError as exc:
            self.fail(f"Could not read arguments: {exc}")
            return None

    def _require_group(self) -> SusuGroup | None:
        if self.group is None:
            self.fail("No group yet. Create one first, e.g. 'create 50.00'")
        return self.group

    def after_change(self) -> None:
        """Hook called after any command that changes the group."""

    def emptyline(self) -> bool:
        return False

    def default(self, line: str) -> None:
        self.fail(f"Unknown command '{line.split()[0]}'. Type 'help' for commands.")

    # ------------------------------------------------------------- commands

    def do_create(self, arg: str) -> None:
        """create <weekly amount>    Start a new group, e.g. 'create 50.00'."""
        args = self._args(arg)
        if args is None:
            return
        if len(args) != 1:
            self.fail("Usage: create <weekly amount>")
            return
        if self.group is not None:
            self.fail("A group already exists. This tracker manages one group.")
            return
        self.group = SusuGroup(contribution=Money.parse(args[0]))
        self.after_change()
        self.say(f"Group created with a weekly contribution of {self.group.contribution.with_currency()}.")

    def do_add(self, arg: str) -> None:
        """add <name>                Add a member. Quote names with spaces: add "Kofi Mensah"."""
        group, args = self._require_group(), self._args(arg)
        if group is None or args is None:
            return
        if len(args) != 1:
            self.fail('Usage: add <name>   (use quotes for names with spaces, e.g. add "Kofi Mensah")')
            return
        name = group.add_member(args[0])
        self.after_change()
        self.say(f"Added {name} (position {len(group.members)} in the payout order).")

    def do_pay(self, arg: str) -> None:
        """pay <name> <amount> [week]  Record a payment for the current week, e.g. 'pay Esi 30'."""
        group, args = self._require_group(), self._args(arg)
        if group is None or args is None:
            return
        if len(args) not in (2, 3):
            self.fail("Usage: pay <name> <amount> [week]")
            return
        week = None
        if len(args) == 3:
            if not args[2].isdigit():
                self.fail(f"Week must be a whole number, not '{args[2]}'")
                return
            week = int(args[2])
        member = group.resolve(args[0])
        amount = Money.parse(args[1])
        remaining = group.contribute(member, amount, week)
        self.after_change()
        status = "paid in full" if remaining == Money.zero() else f"still owes {remaining}"
        self.say(f"Recorded {amount} from {member} for week {group.current_week}; {status}.")

    def do_close(self, arg: str) -> None:
        """close                     Close the current week and pay out if everyone has paid."""
        group = self._require_group()
        if group is None:
            return
        result = group.close_week()
        if result.closed:
            self.after_change()
        else:
            self.last_error = "week cannot close"
        self.say(render_close(result))

    def do_report(self, arg: str) -> None:
        """report                    Show the current week, who has paid, who owes and payout history."""
        group = self._require_group()
        if group is None:
            return
        self.say(render_report(group.report()))

    def do_quit(self, arg: str) -> bool:
        """quit                      Leave the program."""
        return True

    do_exit = do_quit

    def do_EOF(self, arg: str) -> bool:
        self.say("")
        return True


def main(argv: list[str] | None = None) -> int:
    shell = SusuShell()
    shell.cmdloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
