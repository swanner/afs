import tempfile
import unittest
from pathlib import Path

from afs_cli.cli import next_adr_number, slugify


class CliTests(unittest.TestCase):
    def test_slugify(self):
        self.assertEqual(slugify("AFS is a Specification"), "afs-is-a-specification")

    def test_next_adr_number_for_empty_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(next_adr_number(Path(directory)), 1)

    def test_next_adr_number_uses_highest_existing_number(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / "ADR-0001-first.md").write_text("", encoding="utf-8")
            (path / "ADR-0003-third.md").write_text("", encoding="utf-8")
            self.assertEqual(next_adr_number(path), 4)


if __name__ == "__main__":
    unittest.main()
