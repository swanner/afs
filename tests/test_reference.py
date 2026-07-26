from __future__ import annotations

import ast
import subprocess
import sys
import unittest
from pathlib import Path

from reference.python.afs_reference.application import Application
from reference.python.afs_reference.main import build_application
from reference.python.afs_reference.state_machine import State
from reference.python.afs_reference.unit import AFS_TEMPLATE_UNIT


ROOT = Path(__file__).resolve().parents[1]
REFERENCE_ROOT = ROOT / "reference" / "python" / "afs_reference"


class ReferenceImplementationTests(unittest.TestCase):
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
        unit = AFS_TEMPLATE_UNIT(target=2)

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

    def test_template_surface_is_deliberately_small(self) -> None:
        identifiers: set[str] = set()
        occurrences = 0

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
                        occurrences += 1

        self.assertEqual(
            identifiers,
            {"AFS_TEMPLATE_STATE_MACHINE", "AFS_TEMPLATE_UNIT"},
        )
        self.assertLessEqual(occurrences, 16)

    def test_template_workflow_markers_are_present(self) -> None:
        source = (REFERENCE_ROOT / "unit.py").read_text(encoding="utf-8")

        self.assertIn("AFS TEMPLATE WORKFLOW", source)
        self.assertIn("AFS REQUIRED ADAPTATION", source)
        self.assertIn("AFS OPTIONAL", source)
        self.assertIn("AFS PATTERN", source)
        self.assertIn("app.add_unit(AFS_TEMPLATE_UNIT(...))", source)


if __name__ == "__main__":
    unittest.main()
