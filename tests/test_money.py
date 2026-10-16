import unittest

from susu.errors import InvalidAmountError
from susu.money import Money


class MoneyParseTests(unittest.TestCase):
    def test_parses_whole_and_decimal_amounts(self):
        self.assertEqual(Money.parse("50"), Money(5000))
        self.assertEqual(Money.parse("50.5"), Money(5050))
        self.assertEqual(Money.parse("50.05"), Money(5005))
        self.assertEqual(Money.parse(" GHS 0.01 "), Money(1))

    def test_rejects_more_than_two_decimal_places(self):
        with self.assertRaises(InvalidAmountError):
            Money.parse("10.005")

    def test_rejects_non_numeric_text(self):
        for text in ["", "abc", "1e3", "10,00", "nan", "inf", "1.2.3"]:
            with self.subTest(text=text), self.assertRaises(InvalidAmountError):
                Money.parse(text)

    def test_formats_with_two_decimal_places(self):
        self.assertEqual(str(Money(15000)), "150.00")
        self.assertEqual(str(Money(5)), "0.05")
        self.assertEqual(Money(2000).with_currency(), "GHS 20.00")


class MoneyArithmeticTests(unittest.TestCase):
    def test_no_floating_point_drift(self):
        # 0.1 + 0.2 != 0.3 in binary floating point; it must here.
        total = Money.parse("0.10") + Money.parse("0.20")
        self.assertEqual(total, Money.parse("0.30"))

    def test_many_small_payments_add_up_exactly(self):
        total = Money.zero()
        for _ in range(1000):
            total = total + Money.parse("0.01")
        self.assertEqual(total, Money.parse("10.00"))

    def test_multiply_by_member_count(self):
        self.assertEqual(Money.parse("50.00") * 3, Money.parse("150.00"))


if __name__ == "__main__":
    unittest.main()
