"""Save and load a group as JSON.

Amounts are written as strings ("50.00") and read back through Money.parse,
so nothing passes through a float on the way in or out.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from susu.errors import SusuError
from susu.group import Payout, SusuGroup
from susu.money import Money

FORMAT_VERSION = 1


def to_dict(group: SusuGroup) -> dict:
    return {
        "version": FORMAT_VERSION,
        "contribution": str(group.contribution),
        "members": list(group.members),
        "current_week": group.current_week,
        "contributions": {
            str(week): {member: str(amount) for member, amount in payments.items()}
            for week, payments in group.contributions.items()
        },
        "payouts": [
            {"week": p.week, "member": p.member, "amount": str(p.amount)} for p in group.payouts
        ],
    }


def from_dict(data: dict) -> SusuGroup:
    if data.get("version") != FORMAT_VERSION:
        raise SusuError(f"Unsupported state file version: {data.get('version')!r}")
    return SusuGroup(
        contribution=Money.parse(data["contribution"]),
        members=list(data["members"]),
        current_week=int(data["current_week"]),
        contributions={
            int(week): {member: Money.parse(amount) for member, amount in payments.items()}
            for week, payments in data["contributions"].items()
        },
        payouts=[
            Payout(week=int(p["week"]), member=p["member"], amount=Money.parse(p["amount"]))
            for p in data["payouts"]
        ],
    )


def save(group: SusuGroup, path: Path) -> None:
    """Write atomically so a crash mid-write never leaves a half-written file."""
    path = Path(path)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(to_dict(group), indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def load(path: Path) -> SusuGroup | None:
    """Return the saved group, or None if the file does not exist yet."""
    path = Path(path)
    if not path.exists():
        return None
    try:
        return from_dict(json.loads(path.read_text(encoding="utf-8")))
    except (KeyError, TypeError, ValueError) as exc:
        raise SusuError(f"State file {path} is damaged: {exc}") from exc
