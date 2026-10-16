"""The susu group: members, weekly contributions, closing weeks and payouts.

This module is pure domain logic. It does no input/output, so it can be driven
from the CLI, a test or any other front end.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from susu.errors import (
    DuplicateMemberError,
    GroupStateError,
    InvalidAmountError,
    OverpaymentError,
    UnknownMemberError,
)
from susu.money import Money

MIN_MEMBERS = 2


@dataclass(frozen=True)
class Payout:
    week: int
    member: str
    amount: Money


@dataclass(frozen=True)
class Debt:
    member: str
    paid: Money
    owes: Money


@dataclass(frozen=True)
class CloseResult:
    """Outcome of trying to close the current week.

    When ``closed`` is False, ``outstanding`` lists everyone who still owes and
    nothing was paid out.
    """

    week: int
    closed: bool
    payout: Payout | None = None
    outstanding: tuple[Debt, ...] = ()
    cycle_complete: bool = False


@dataclass(frozen=True)
class Report:
    week: int
    contribution: Money
    pot: Money
    members: tuple[str, ...]
    next_recipient: str | None
    paid_in_full: tuple[str, ...]
    owing: tuple[Debt, ...]
    payouts: tuple[Payout, ...]
    cycle_complete: bool


@dataclass
class SusuGroup:
    contribution: Money
    members: list[str] = field(default_factory=list)
    current_week: int = 1
    # week number -> member name -> total paid that week
    contributions: dict[int, dict[str, Money]] = field(default_factory=dict)
    payouts: list[Payout] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.contribution.is_positive():
            raise InvalidAmountError("The weekly contribution must be greater than zero")

    # ------------------------------------------------------------------ state

    @property
    def started(self) -> bool:
        """True once any money has been recorded; membership is then locked."""
        return any(self.contributions.values()) or bool(self.payouts)

    @property
    def cycle_complete(self) -> bool:
        """True once every member has received the pot exactly once."""
        return bool(self.members) and len(self.payouts) == len(self.members)

    @property
    def pot(self) -> Money:
        return self.contribution * len(self.members)

    @property
    def next_recipient(self) -> str | None:
        if self.cycle_complete or not self.members:
            return None
        return self.members[len(self.payouts)]

    # ---------------------------------------------------------------- members

    def add_member(self, name: str) -> str:
        cleaned = " ".join(str(name).split())
        if not cleaned:
            raise GroupStateError("Member name cannot be empty")
        if self._find(cleaned) is not None:
            raise DuplicateMemberError(f"'{cleaned}' is already a member")
        if self.started:
            raise GroupStateError(
                "Members can only be added before the first contribution is recorded"
            )
        self.members.append(cleaned)
        return cleaned

    def _find(self, name: str) -> str | None:
        key = " ".join(str(name).split()).casefold()
        for member in self.members:
            if member.casefold() == key:
                return member
        return None

    def resolve(self, name: str) -> str:
        """Return the member's stored name, matching case-insensitively."""
        member = self._find(name)
        if member is None:
            raise UnknownMemberError(f"'{name}' is not a member of this group")
        return member

    # ---------------------------------------------------------- contributions

    def paid(self, name: str, week: int | None = None) -> Money:
        member = self.resolve(name)
        week = self.current_week if week is None else week
        return self.contributions.get(week, {}).get(member, Money.zero())

    def owes(self, name: str) -> Money:
        """What the member still owes for the current week."""
        if self.cycle_complete:
            return Money.zero()
        return self.contribution - self.paid(name)

    def contribute(self, name: str, amount: Money, week: int | None = None) -> Money:
        """Record a (possibly partial) payment. Returns what the member still owes."""
        member = self.resolve(name)
        if not amount.is_positive():
            raise InvalidAmountError("Payment amount must be greater than zero")
        if self.cycle_complete:
            raise GroupStateError("The cycle is complete; every member has been paid out")
        if len(self.members) < MIN_MEMBERS:
            raise GroupStateError(
                f"A group needs at least {MIN_MEMBERS} members before contributions start"
            )
        if week is not None and week != self.current_week:
            raise GroupStateError(
                f"Only the current week ({self.current_week}) accepts payments, not week {week}"
            )

        outstanding = self.owes(member)
        if outstanding == Money.zero():
            raise OverpaymentError(f"{member} has already paid in full for week {self.current_week}")
        if amount > outstanding:
            raise OverpaymentError(
                f"{member} only owes {outstanding} for week {self.current_week}; "
                f"cannot accept {amount}"
            )

        week_payments = self.contributions.setdefault(self.current_week, {})
        week_payments[member] = self.paid(member) + amount
        return self.owes(member)

    def debts(self) -> tuple[Debt, ...]:
        """Everyone who has not yet paid in full this week, in joining order."""
        if self.cycle_complete:
            return ()
        return tuple(
            Debt(member, self.paid(member), self.owes(member))
            for member in self.members
            if self.owes(member).is_positive()
        )

    # ------------------------------------------------------------ close week

    def close_week(self) -> CloseResult:
        """Pay the pot out if everyone has paid in full; otherwise report debts."""
        if self.cycle_complete:
            raise GroupStateError("The cycle is complete; there is no week left to close")
        if len(self.members) < MIN_MEMBERS:
            raise GroupStateError(f"A group needs at least {MIN_MEMBERS} members to close a week")

        week = self.current_week
        outstanding = self.debts()
        if outstanding:
            return CloseResult(week=week, closed=False, outstanding=outstanding)

        payout = Payout(week=week, member=self.next_recipient, amount=self.pot)
        self.payouts.append(payout)
        if not self.cycle_complete:
            self.current_week += 1
        return CloseResult(week=week, closed=True, payout=payout, cycle_complete=self.cycle_complete)

    # ---------------------------------------------------------------- report

    def report(self) -> Report:
        debts = self.debts()
        owing_names = {debt.member for debt in debts}
        return Report(
            week=self.current_week,
            contribution=self.contribution,
            pot=self.pot,
            members=tuple(self.members),
            next_recipient=self.next_recipient,
            paid_in_full=tuple(m for m in self.members if m not in owing_names)
            if not self.cycle_complete
            else (),
            owing=debts,
            payouts=tuple(self.payouts),
            cycle_complete=self.cycle_complete,
        )
