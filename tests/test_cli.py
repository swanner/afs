from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from afs_cli.cli import (
    adr_template,
    command_validate,
    next_adr_number,
    slugify,
)


class Namespace:
    pass


class CliTests(unittest.TestCase):
    def test_slugify(self) -> None:
        self.assertEqual(slugify("Use YAML for AFS"), "use-yaml-for-afs")

    def test_next_adr_number(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            (directory / "ADR-0002-example.md").write_text(
                "",
                encoding="utf-8",
            )
            self.assertEqual(next_adr_number(directory), 3)

    def test_template_contains_required_sections(self) -> None:
        content = adr_template(7, "Example")

        self.assertIn("# ADR-0007: Example", content)
        self.assertIn("- Status: Proposed", content)
        self.assertIn("## Alternatives considered", content)

    def test_repository_validation_passes_for_valid_adr(self) -> None:
        original_directory = Path.cwd()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.create_repository(root)

            adr_dir = root / "specification" / "adr"
            (adr_dir / "ADR-0001-example.md").write_text(
                adr_template(1, "Example"),
                encoding="utf-8",
            )

            try:
                os.chdir(root)
                self.assertEqual(command_validate(Namespace()), 0)
            finally:
                os.chdir(original_directory)

    def test_repository_validation_rejects_invalid_status(self) -> None:
        original_directory = Path.cwd()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.create_repository(root)

            invalid = adr_template(1, "Example").replace(
                "- Status: Proposed",
                "- Status: Unknown",
            )

            adr_dir = root / "specification" / "adr"
            (adr_dir / "ADR-0001-example.md").write_text(
                invalid,
                encoding="utf-8",
            )

            try:
                os.chdir(root)
                self.assertEqual(command_validate(Namespace()), 1)
            finally:
                os.chdir(original_directory)

    @staticmethod
    def create_repository(root: Path) -> None:
        (root / "README.md").write_text("# Test\n", encoding="utf-8")
        (root / "LICENSE").write_text("Test\n", encoding="utf-8")
        (root / "pyproject.toml").write_text(
            "[project]\nname = \"test\"\nversion = \"0.1.0\"\n",
            encoding="utf-8",
        )

        (root / "specification" / "adr").mkdir(parents=True)


if __name__ == "__main__":
    unittest.main()
