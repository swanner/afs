from __future__ import annotations

import ast
import re
import subprocess
import sys
import unittest
from pathlib import Path

from reference.python.afs_reference.application import Application
from reference.python.afs_reference.main import build_application
from reference.python.afs_reference.state_machine import State
from reference.python.afs_reference.unit import AFS_TEMPLATE_01_UNIT


ROOT = Path(__file__).resolve().parents[1]
REFERENCE_ROOT = ROOT / "reference" / "python" / "afs_reference"

REFERENCE_README = ROOT / "reference" / "README.md"

TEMPLATE_IDENTIFIER_PATTERN = re.compile(
    r"AFS_TEMPLATE_(\d{2})_[A-Z][A-Z0-9_]*"
)


class ReferenceImplementationTests(unittest.TestCase):

    def _template_identifiers_from_code(self) -> set[str]:
        identifiers: set[str] = set()

        for path in REFERENCE_ROOT.glob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))

            for node in ast.walk(tree):
                names: list[str] = []

                if isinstance(node, ast.Name):
                    names.append(node.id)
                elif isinstance(node, (ast.ClassDef, ast.FunctionDef)):
                    names.append(node.name)
                elif isinstance(node, ast.alias):
                    names.append(node.name)

                for name in names:
                    if name.startswith("AFS_TEMPLATE_"):
                        identifiers.add(name)

        return identifiers

    def test_application_runs_registered_unit(self) -> None:
        app, unit = build_application()

        app.run(scans=5)

        self.assertEqual(unit.status.state, State.COMPLETE)
        self.assertEqual(unit.status.value, 3)
        self.assertIsNone(unit.status.alarm)

    def test_application_preserves_explicit_registration_order(self) -> None:
        calls: list[str] = []

        class RecordingUnit:
            def __init__(self, name: str) -> None:
                self.name = name

            def scan(self) -> None:
                calls.append(self.name)

        app = Application()
        app.add_unit(RecordingUnit("first"))
        app.add_unit(RecordingUnit("second"))

        app.run(scans=2)

        self.assertEqual(calls, ["first", "second", "first", "second"])

    def test_unit_owns_state_machine_lifecycle(self) -> None:
        unit = AFS_TEMPLATE_01_UNIT(target=2)

        unit.scan()
        self.assertEqual(unit.status.state, State.EXECUTE)

        unit.scan()
        self.assertEqual(unit.status.state, State.EXECUTE)

        unit.scan()
        self.assertEqual(unit.status.state, State.COMPLETE)

    def test_reference_application_is_executable(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "reference.python.afs_reference"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout,
            "template-unit: state=COMPLETE value=3 alarm=none\n",
        )

    def test_template_surface_is_minimal(self) -> None:
        identifiers = self._template_identifiers_from_code()

        self.assertEqual(
            identifiers,
            {
                "AFS_TEMPLATE_01_UNIT",
                "AFS_TEMPLATE_02_STATE_MACHINE",
            },
        )

    def test_template_identifiers_are_numbered_without_gaps(self) -> None:
        identifiers = self._template_identifiers_from_code()
        numbers: list[int] = []

        for identifier in identifiers:
            match = TEMPLATE_IDENTIFIER_PATTERN.fullmatch(identifier)
            self.assertIsNotNone(
                match,
                f"Invalid template identifier: {identifier}",
            )
            numbers.append(int(match.group(1)))

        self.assertEqual(len(numbers), len(set(numbers)))
        self.assertEqual(min(numbers), 1)
        self.assertEqual(
            sorted(numbers),
            list(range(1, max(numbers) + 1)),
        )

    def test_template_api_is_documented_in_readme(self) -> None:
        code_identifiers = self._template_identifiers_from_code()

        readme = REFERENCE_README.read_text(encoding="utf-8")
        documented_identifiers = {
            match.group(0)
            for match in TEMPLATE_IDENTIFIER_PATTERN.finditer(readme)
        }

        self.assertEqual(
            documented_identifiers,
            code_identifiers,
        )

    def test_template_workflow_markers_are_present(self) -> None:
        source = (REFERENCE_ROOT / "unit.py").read_text(encoding="utf-8")

        self.assertIn("AFS TEMPLATE WORKFLOW", source)
        self.assertIn("AFS REQUIRED ADAPTATION", source)
        self.assertIn("AFS OPTIONAL", source)
        self.assertIn("AFS PATTERN", source)
        self.assertIn("app.add_unit(AFS_TEMPLATE_01_UNIT(...))", source)


if __name__ == "__main__":
    unittest.main()
