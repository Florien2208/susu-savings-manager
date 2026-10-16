import unittest

from susu.errors import (
    DuplicateMemberError,
    GroupStateError,
    InvalidAmountError,
    OverpaymentError,
    UnknownMemberError,
)
from susu.group import SusuGroup
from susu.money import Money


def ghs(text: str) -> Money:
    return Money.parse(text)


def make_group(*names: str, weekly: str = "50.00") -> SusuGroup:
    group = SusuGroup(contribution=ghs(weekly))
    for name in names:
        group.add_member(name)
    return group


class CreateGroupTests(unittest.TestCase):
    def test_rejects_zero_or_negative_weekly_contribution(self):
        for amount in ["0", "0.00", "-50"]:
            with self.subTest(amount=amount), self.assertRaises(InvalidAmountError):
                SusuGroup(contribution=ghs(amount))

    def test_new_group_starts_at_week_one_with_no_payouts(self):
        group = make_group("Ama", "Kofi")
        self.assertEqual(group.current_week, 1)
        self.assertEqual(group.payouts, [])
        self.assertEqual(group.pot, ghs("100.00"))


class MemberTests(unittest.TestCase):
    def test_rejects_duplicate_member_ignoring_case_and_spacing(self):
        group = make_group("Ama")
        for name in ["Ama", "ama", "  AMA "]:
            with self.subTest(name=name), self.assertRaises(DuplicateMemberError):
                group.add_member(name)

    def test_rejects_empty_name(self):
        with self.assertRaises(GroupStateError):
            make_group().add_member("   ")

    def test_rejects_unknown_member_payment(self):
        group = make_group("Ama", "Kofi")
        with self.assertRaises(UnknownMemberError):
            group.contribute("Yaw", ghs("50"))

    def test_cannot_add_member_after_first_contribution(self):
        group = make_group("Ama", "Kofi")
        group.contribute("Ama", ghs("10"))
        with self.assertRaises(GroupStateError):
            group.add_member("Esi")

    def test_member_names_match_case_insensitively(self):
        group = make_group("Ama", "Kofi")
        group.contribute("ama", ghs("50"))
        self.assertEqual(group.paid("AMA"), ghs("50"))


class ContributionTests(unittest.TestCase):
    def test_partial_payments_accumulate(self):
        group = make_group("Ama", "Kofi")
        remaining = group.contribute("Ama", ghs("30"))
        self.assertEqual(remaining, ghs("20"))
        remaining = group.contribute("Ama", ghs("15.50"))
        self.assertEqual(remaining, ghs("4.50"))
        self.assertEqual(group.paid("Ama"), ghs("45.50"))

    def test_rejects_zero_and_negative_payments(self):
        group = make_group("Ama", "Kofi")
        for amount in ["0", "0.00", "-5"]:
            with self.subTest(amount=amount), self.assertRaises(InvalidAmountError):
                group.contribute("Ama", ghs(amount))

    def test_rejects_payment_above_what_is_owed(self):
        group = make_group("Ama", "Kofi")
        with self.assertRaises(OverpaymentError):
            group.contribute("Ama", ghs("50.01"))
        group.contribute("Ama", ghs("30"))
        with self.assertRaises(OverpaymentError):
            group.contribute("Ama", ghs("20.01"))
        # The rejected payments left the balance untouched.
        self.assertEqual(group.owes("Ama"), ghs("20"))

    def test_rejects_payment_once_paid_in_full(self):
        group = make_group("Ama", "Kofi")
        group.contribute("Ama", ghs("50"))
        with self.assertRaises(OverpaymentError):
            group.contribute("Ama", ghs("0.01"))

    def test_only_current_week_accepts_payments(self):
        group = make_group("Ama", "Kofi")
        with self.assertRaises(GroupStateError):
            group.contribute("Ama", ghs("50"), week=2)
        group.contribute("Ama", ghs("50"), week=1)
        self.assertEqual(group.paid("Ama", week=1), ghs("50"))

    def test_needs_at_least_two_members_before_contributing(self):
        group = make_group("Ama")
        with self.assertRaises(GroupStateError):
            group.contribute("Ama", ghs("50"))


class CloseWeekTests(unittest.TestCase):
    def test_week_cannot_close_while_someone_owes(self):
        group = make_group("Ama", "Kofi", "Esi")
        group.contribute("Ama", ghs("50"))
        group.contribute("Kofi", ghs("50"))
        group.contribute("Esi", ghs("30"))

        result = group.close_week()

        self.assertFalse(result.closed)
        self.assertIsNone(result.payout)
        self.assertEqual([(d.member, str(d.owes)) for d in result.outstanding], [("Esi", "20.00")])
        self.assertEqual(group.current_week, 1)
        self.assertEqual(group.payouts, [])

    def test_week_cannot_close_reports_members_who_paid_nothing(self):
        group = make_group("Ama", "Kofi")
        result = group.close_week()
        self.assertFalse(result.closed)
        self.assertEqual(
            [(d.member, str(d.paid), str(d.owes)) for d in result.outstanding],
            [("Ama", "0.00", "50.00"), ("Kofi", "0.00", "50.00")],
        )

    def test_brief_example_end_to_end(self):
        group = make_group("Ama", "Kofi", "Esi")
        group.contribute("Ama", ghs("50"))
        group.contribute("Kofi", ghs("50"))
        group.contribute("Esi", ghs("30"))
        self.assertFalse(group.close_week().closed)

        group.contribute("Esi", ghs("20"))
        result = group.close_week()

        self.assertTrue(result.closed)
        self.assertEqual(result.payout.member, "Ama")
        self.assertEqual(result.payout.amount, ghs("150.00"))
        self.assertEqual(group.current_week, 2)
        self.assertEqual(group.next_recipient, "Kofi")
        # Nobody has paid for week 2 yet.
        self.assertEqual(group.owes("Ama"), ghs("50"))

    def test_payout_follows_joining_order_until_cycle_completes(self):
        group = make_group("Ama", "Kofi", "Esi")
        for _ in range(3):
            for member in group.members:
                group.contribute(member, ghs("50"))
            self.assertTrue(group.close_week().closed)

        self.assertEqual([p.member for p in group.payouts], ["Ama", "Kofi", "Esi"])
        self.assertEqual([p.week for p in group.payouts], [1, 2, 3])
        self.assertTrue(group.cycle_complete)
        self.assertIsNone(group.next_recipient)
        with self.assertRaises(GroupStateError):
            group.contribute("Ama", ghs("50"))
        with self.assertRaises(GroupStateError):
            group.close_week()

    def test_odd_amounts_pay_out_exactly(self):
        group = make_group("Ama", "Kofi", "Esi", weekly="33.33")
        for member in group.members:
            group.contribute(member, ghs("11.11"))
            group.contribute(member, ghs("22.22"))
        result = group.close_week()
        self.assertEqual(str(result.payout.amount), "99.99")


class ReportTests(unittest.TestCase):
    def test_report_shows_week_paid_owing_and_history(self):
        group = make_group("Ama", "Kofi", "Esi")
        for member in group.members:
            group.contribute(member, ghs("50"))
        group.close_week()
        group.contribute("Kofi", ghs("50"))
        group.contribute("Esi", ghs("12.50"))

        report = group.report()

        self.assertEqual(report.week, 2)
        self.assertEqual(report.next_recipient, "Kofi")
        self.assertEqual(report.paid_in_full, ("Kofi",))
        self.assertEqual(
            [(d.member, str(d.owes)) for d in report.owing],
            [("Ama", "50.00"), ("Esi", "37.50")],
        )
        self.assertEqual([(p.week, p.member, str(p.amount)) for p in report.payouts], [(1, "Ama", "150.00")])


if __name__ == "__main__":
    unittest.main()
