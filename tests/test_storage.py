import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from susu import storage
from susu.cli import main
from susu.errors import SusuError
from susu.group import SusuGroup
from susu.money import Money


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "group.json"

    def tearDown(self):
        self.tmp.cleanup()

    def test_round_trip_keeps_every_amount_exact(self):
        group = SusuGroup(contribution=Money.parse("33.33"))
        for name in ["Ama", "Kofi", "Esi"]:
            group.add_member(name)
        for name in group.members:
            group.contribute(name, Money.parse("33.33"))
        group.close_week()
        group.contribute("Esi", Money.parse("0.01"))

        storage.save(group, self.path)
        loaded = storage.load(self.path)

        self.assertEqual(loaded, group)
        self.assertEqual(json.loads(self.path.read_text())["payouts"][0]["amount"], "99.99")

    def test_missing_file_loads_as_no_group(self):
        self.assertIsNone(storage.load(self.path))

    def test_damaged_file_gives_a_clear_error(self):
        self.path.write_text("{not json")
        with self.assertRaises(SusuError):
            storage.load(self.path)

    def test_one_shot_commands_share_state_between_runs(self):
        def cli(*args: str) -> tuple[int, str]:
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = main(["--state", str(self.path), *args])
            return code, out.getvalue()

        for args in [("create", "50"), ("add", "Ama"), ("add", "Kofi"), ("pay", "Ama", "50")]:
            self.assertEqual(cli(*args)[0], 0, args)

        code, output = cli("close")
        self.assertEqual(code, 1)
        self.assertIn("Kofi owes 50.00", output)

        self.assertEqual(cli("pay", "Kofi", "50")[0], 0)
        code, output = cli("close")
        self.assertEqual(code, 0)
        self.assertIn("Ama receives GHS 100.00", output)


if __name__ == "__main__":
    unittest.main()
