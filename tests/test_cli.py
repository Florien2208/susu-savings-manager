import io
import unittest

from susu.cli import SusuShell


def run(*lines: str) -> tuple[SusuShell, str]:
    out = io.StringIO()
    shell = SusuShell(stdout=out)
    for line in lines:
        shell.onecmd(line)
    return shell, out.getvalue()


class ShellTests(unittest.TestCase):
    def test_brief_example_through_the_shell(self):
        _, output = run(
            "create 50.00",
            "add Ama",
            "add Kofi",
            "add Esi",
            "pay Ama 50",
            "pay Kofi 50",
            "pay Esi 30",
            "close",
            "pay Esi 20",
            "close",
            "report",
        )
        self.assertIn("Week 1 cannot close", output)
        self.assertIn("Esi owes 20.00", output)
        self.assertIn("Week 1 closed. Ama receives GHS 150.00.", output)
        self.assertIn("Current week: 2", output)
        self.assertIn("Pot this week: GHS 150.00 -> Kofi", output)
        self.assertIn("Week 1: Ama received GHS 150.00", output)

    def test_rule_violations_are_reported_not_raised(self):
        shell, output = run("create 50", "add Ama", "add Kofi", "pay Ama 60")
        self.assertIn("Error: Ama only owes 50.00", output)
        self.assertIsNotNone(shell.last_error)

    def test_commands_need_a_group_first(self):
        _, output = run("add Ama")
        self.assertIn("No group yet", output)

    def test_names_with_spaces_can_be_quoted(self):
        _, output = run("create 10", 'add "Kofi Mensah"', "add Esi", 'pay "kofi mensah" 10')
        self.assertIn("Recorded 10.00 from Kofi Mensah for week 1; paid in full.", output)

    def test_rejects_bad_amount_text(self):
        _, output = run("create 10", "add Ama", "add Kofi", "pay Ama ten")
        self.assertIn("'ten' is not a valid amount", output)


if __name__ == "__main__":
    unittest.main()
