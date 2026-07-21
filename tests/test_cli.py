from __future__ import annotations

import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from afs_cli.cli import (
    adr_template,
    command_init,
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

    def test_init_creates_valid_repository(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            result = command_init(Namespace(str(root)))

            self.assertEqual(result, 0)
            self.assertEqual(validate_repository(root), [])

    def test_init_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            command_init(Namespace(str(root)))
            result = command_init(Namespace(str(root)))

            self.assertEqual(result, 0)
            self.assertEqual(validate_repository(root), [])

    def test_init_does_not_overwrite_existing_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            readme = root / "README.md"
            readme.write_text("# Existing project\n", encoding="utf-8")

            command_init(Namespace(str(root)))

            self.assertEqual(
                readme.read_text(encoding="utf-8"),
                "# Existing project\n",
            )
            self.assertEqual(validate_repository(root), [])

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

    def test_invalid_status_reports_afs202(self) -> None:
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
            self.assertIn("AFS202", errors[0])
            self.assertIn("Invalid ADR status 'Unknown'", errors[0])

    def test_missing_required_path_reports_afs001(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            errors = validate_repository(Path(tmp))

            self.assertTrue(any(error.startswith("AFS001:") for error in errors))

    def test_invalid_date_reports_afs203(self) -> None:
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
            self.assertIn("AFS203", errors[0])


    def test_duplicate_number_reports_afs102(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.create_repository(root)
            self.write_adr(root, "ADR-0001-one.md", adr_template(1, "One"))
            self.write_adr(root, "ADR-0001-two.md", adr_template(1, "Two"))

            errors = validate_repository(root)

            self.assertIn("AFS102: Duplicate ADR number: 0001", errors)

    def test_missing_number_reports_afs104(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.create_repository(root)
            self.write_adr(root, "ADR-0001-one.md", adr_template(1, "One"))
            self.write_adr(root, "ADR-0003-three.md", adr_template(3, "Three"))

            errors = validate_repository(root)

            self.assertIn("AFS104: Missing ADR number: 0002", errors)

    def test_first_number_reports_afs105(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.create_repository(root)
            self.write_adr(root, "ADR-0007-seven.md", adr_template(7, "Seven"))

            errors = validate_repository(root)

            self.assertIn("AFS105: First ADR number must be 0001", errors)

    def test_unexpected_markdown_reports_afs106(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.create_repository(root)
            path = root / "specification" / "adr" / "notes.md"
            path.write_text("# Notes\n", encoding="utf-8")

            errors = validate_repository(root)

            self.assertIn(
                "AFS106: Unexpected Markdown file: specification/adr/notes.md",
                errors,
            )

    def test_readme_is_allowed_in_adr_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.create_repository(root)
            path = root / "specification" / "adr" / "README.md"
            path.write_text("# ADRs\n", encoding="utf-8")

            self.assertEqual(validate_repository(root), [])

    def test_non_markdown_file_reports_afs107(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.create_repository(root)
            path = root / "specification" / "adr" / "notes.txt"
            path.write_text("Notes\n", encoding="utf-8")

            errors = validate_repository(root)

            self.assertIn(
                "AFS107: Non-Markdown file: specification/adr/notes.txt",
                errors,
            )

    def test_invalid_adr_filename_reports_afs101(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.create_repository(root)
            path = root / "specification" / "adr" / "ADR-1-invalid.md"
            path.write_text("# Invalid\n", encoding="utf-8")

            errors = validate_repository(root)

            self.assertIn(
                "AFS101: Invalid ADR filename: specification/adr/ADR-1-invalid.md",
                errors,
            )

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
