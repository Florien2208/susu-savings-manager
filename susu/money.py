"""Exact money handling.

Amounts are stored as an integer number of pesewas (1 GHS = 100 pesewas), so
adding, subtracting and multiplying never introduce floating point error.
Text input is parsed with Decimal and must have at most two decimal places;
anything finer is rejected rather than silently rounded.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from susu.errors import InvalidAmountError

_AMOUNT_PATTERN = re.compile(r"^-?\d+(\.\d{1,2})?$")


@dataclass(frozen=True, order=True)
class Money:
    pesewas: int

    @classmethod
    def parse(cls, text: str) -> Money:
        """Parse a GHS amount such as "50", "50.5" or "50.00"."""
        cleaned = str(text).strip()
        if cleaned.upper().startswith("GHS"):
            cleaned = cleaned[3:].strip()
        if not _AMOUNT_PATTERN.match(cleaned):
            raise InvalidAmountError(
                f"'{text}' is not a valid amount; use a number with at most 2 decimal places, e.g. 50.00"
            )
        try:
            value = Decimal(cleaned)
        except InvalidOperation as exc:  # pragma: no cover - guarded by the regex
            raise InvalidAmountError(f"'{text}' is not a valid amount") from exc
        return cls(int(value * 100))

    @classmethod
    def zero(cls) -> Money:
        return cls(0)

    def __add__(self, other: Money) -> Money:
        return Money(self.pesewas + other.pesewas)

    def __sub__(self, other: Money) -> Money:
        return Money(self.pesewas - other.pesewas)

    def __mul__(self, times: int) -> Money:
        if not isinstance(times, int):
            return NotImplemented
        return Money(self.pesewas * times)

    __rmul__ = __mul__

    def is_positive(self) -> bool:
        return self.pesewas > 0

    def __str__(self) -> str:
        sign = "-" if self.pesewas < 0 else ""
        cedis, pesewas = divmod(abs(self.pesewas), 100)
        return f"{sign}{cedis}.{pesewas:02d}"

    def with_currency(self) -> str:
        return f"GHS {self}"
