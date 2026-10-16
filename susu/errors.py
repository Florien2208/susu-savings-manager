"""Domain errors. Every rule violation raises a SusuError with a readable message."""


class SusuError(Exception):
    """Base class for every rule the group refuses to break."""


class InvalidAmountError(SusuError):
    """Amount is malformed, zero, negative or has more than two decimal places."""


class UnknownMemberError(SusuError):
    """The named member is not in the group."""


class DuplicateMemberError(SusuError):
    """A member with the same name (ignoring case) already exists."""


class OverpaymentError(SusuError):
    """The payment is more than the member still owes for the week."""


class GroupStateError(SusuError):
    """The action is not allowed in the group's current state."""
