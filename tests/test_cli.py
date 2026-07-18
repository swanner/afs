from __future__ import annotations

import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from afs_cli.cli import (
    adr_template,
    command_validate,
    next_adr_number,
    slugify,
    validate_repository,
)


class Namespace:
    def __init__(self, path: str) -> None:
        self.path = path


class CliTests(unittest.TestCase):
    def test_slugify(self) -> None:
        self.assertEqual(slugify("Use YAML for AFS"), "use-yaml-for-afs")

    def test_next_adr_number(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            (directory / "ADR-0002-example.md").write_text("", encoding="utf-8")
            self.assertEqual(next_adr_number(directory), 3)

    def test_template_contains_required_sections(self) -> None:
        content = adr_template(7, "Example")
        self.assertIn("# ADR-0007: Example", content)
        self.assertIn("- Status: Proposed", content)
        self.assertIn("## Alternatives considered", content)

    def test_valid_repository_has_no_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.create_repository(root)
            self.write_adr(root, "ADR-0001-example.md", adr_template(1, "Example"))

            self.assertEqual(validate_repository(root), [])

    def test_command_can_validate_explicit_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.create_repository(root)
            self.write_adr(root, "ADR-0001-example.md", adr_template(1, "Example"))

            output = StringIO()
            with redirect_stdout(output):
                result = command_validate(Namespace(str(root)))

            self.assertEqual(result, 0)
            self.assertEqual(output.getvalue(), "AFS repository validation passed.\n")

    def test_invalid_status_reports_afs006(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.create_repository(root)
            invalid = adr_template(1, "Example").replace(
                "- Status: Proposed",
                "- Status: Unknown",
            )
            self.write_adr(root, "ADR-0001-example.md", invalid)

            errors = validate_repository(root)

            self.assertEqual(len(errors), 1)
            self.assertIn("AFS006", errors[0])
            self.assertIn("Invalid ADR status 'Unknown'", errors[0])

    def test_missing_required_path_reports_afs001(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            errors = validate_repository(Path(tmp))

            self.assertTrue(any(error.startswith("AFS001:") for error in errors))

    def test_invalid_date_reports_afs007(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.create_repository(root)
            invalid = adr_template(1, "Example").replace(
                f"- Date: {__import__('datetime').date.today().isoformat()}",
                "- Date: 2026-99-99",
            )
            self.write_adr(root, "ADR-0001-example.md", invalid)

            errors = validate_repository(root)

            self.assertEqual(len(errors), 1)
            self.assertIn("AFS007", errors[0])

    @staticmethod
    def create_repository(root: Path) -> None:
        (root / "README.md").write_text("# Test\n", encoding="utf-8")
        (root / "LICENSE").write_text("Test\n", encoding="utf-8")
        (root / "pyproject.toml").write_text(
            '[project]\nname = "test"\nversion = "0.1.0"\n',
            encoding="utf-8",
        )
        (root / "specification" / "adr").mkdir(parents=True)

    @staticmethod
    def write_adr(root: Path, filename: str, content: str) -> None:
        path = root / "specification" / "adr" / filename
        path.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
