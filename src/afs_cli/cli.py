from __future__ import annotations

import argparse
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Callable

ADR_RELATIVE_DIR = Path("specification/adr")
ADR_PATTERN = re.compile(r"^ADR-(\d{4})-([a-z0-9]+(?:-[a-z0-9]+)*)\.md$")
HEADING_PATTERN = re.compile(r"^# ADR-(\d{4}):\s+.+$", re.MULTILINE)
STATUS_PATTERN = re.compile(r"^- Status:\s*(.+?)\s*$", re.MULTILINE)
DATE_PATTERN = re.compile(r"^- Date:\s*(.+?)\s*$", re.MULTILINE)

ALLOWED_STATUSES = {
    "Proposed",
    "Accepted",
    "Rejected",
    "Deprecated",
    "Superseded",
}

REQUIRED_RELATIVE_PATHS = (
    Path("README.md"),
    Path("LICENSE"),
    Path("pyproject.toml"),
    ADR_RELATIVE_DIR,
)

REQUIRED_SECTIONS = (
    "## Context",
    "## Decision",
    "## Consequences",
    "## Alternatives considered",
)

ValidationRule = Callable[[Path, list[str]], None]


INITIAL_FILES = {
    Path("README.md"): """# Architecture

This repository uses the Architecture File Standard (AFS).

Architecture decisions are stored in:

- `specification/adr/`
""",
    Path("LICENSE"): "No license has been selected for this repository yet.\n",
    Path("pyproject.toml"): """[project]
name = "afs-architecture"
version = "0.1.0"
description = "Architecture documentation managed with AFS"
requires-python = ">=3.10"
""",
}


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "decision"


def next_adr_number(directory: Path) -> int:
    highest = 0
    if directory.exists():
        for path in directory.iterdir():
            match = ADR_PATTERN.match(path.name)
            if match:
                highest = max(highest, int(match.group(1)))
    return highest + 1


def adr_template(number: int, title: str) -> str:
    return f"""# ADR-{number:04d}: {title}

- Status: Proposed
- Date: {date.today().isoformat()}

## Context

Describe the forces, constraints, and problem that require a decision.

## Decision

Describe the chosen decision clearly and unambiguously.

## Consequences

Describe the positive, negative, and neutral consequences.

## Alternatives considered

Describe the most relevant alternatives and why they were not selected.
"""


def command_adr_new(args: argparse.Namespace) -> int:
    directory = Path(args.directory)
    directory.mkdir(parents=True, exist_ok=True)
    number = next_adr_number(directory)
    path = directory / f"ADR-{number:04d}-{slugify(args.title)}.md"
    path.write_text(adr_template(number, args.title), encoding="utf-8")
    print(path)
    return 0


def command_adr_list(args: argparse.Namespace) -> int:
    directory = Path(args.directory)
    files = sorted(directory.glob("ADR-*.md")) if directory.exists() else []
    if not files:
        print("No ADRs found.")
        return 0
    for path in files:
        print(path)
    return 0


def add_error(errors: list[str], rule: str, message: str) -> None:
    errors.append(f"{rule}: {message}")


def display_path(path: Path, root: Path) -> Path:
    try:
        return path.relative_to(root)
    except ValueError:
        return path


def adr_markdown_files(root: Path) -> list[Path]:
    directory = root / ADR_RELATIVE_DIR
    if not directory.is_dir():
        return []
    return sorted(
        path
        for path in directory.iterdir()
        if path.is_file() and path.suffix.lower() == ".md" and path.name != "README.md"
    )


def adr_numbers(root: Path) -> list[int]:
    numbers: list[int] = []
    for path in adr_markdown_files(root):
        match = ADR_PATTERN.match(path.name)
        if match:
            numbers.append(int(match.group(1)))
    return numbers


def validate_required_paths(root: Path, errors: list[str]) -> None:
    for relative_path in REQUIRED_RELATIVE_PATHS:
        if not (root / relative_path).exists():
            add_error(errors, "AFS001", f"Missing required path: {relative_path}")


def validate_adr_directory_entries(root: Path, errors: list[str]) -> None:
    directory = root / ADR_RELATIVE_DIR
    if not directory.is_dir():
        return

    for path in sorted(directory.iterdir()):
        shown_path = display_path(path, root)
        if path.is_dir():
            add_error(errors, "AFS106", f"Unexpected entry: {shown_path}")
        elif path.suffix.lower() != ".md":
            add_error(errors, "AFS107", f"Non-Markdown file: {shown_path}")
        elif path.name != "README.md" and not path.name.startswith("ADR-"):
            add_error(errors, "AFS106", f"Unexpected Markdown file: {shown_path}")


def validate_adr_files(root: Path, errors: list[str]) -> None:
    for path in adr_markdown_files(root):
        shown_path = display_path(path, root)
        match = ADR_PATTERN.match(path.name)
        if not match:
            if path.name.startswith("ADR-"):
                add_error(errors, "AFS101", f"Invalid ADR filename: {shown_path}")
            continue

        number = int(match.group(1))
        content = path.read_text(encoding="utf-8")

        heading_match = HEADING_PATTERN.search(content)
        if not heading_match or int(heading_match.group(1)) != number:
            add_error(
                errors,
                "AFS103",
                f"Missing or inconsistent ADR heading: {shown_path}",
            )

        status_match = STATUS_PATTERN.search(content)
        date_match = DATE_PATTERN.search(content)

        if not status_match:
            add_error(errors, "AFS201", f"Missing Status metadata: {shown_path}")
        elif status_match.group(1) not in ALLOWED_STATUSES:
            add_error(
                errors,
                "AFS202",
                f"Invalid ADR status '{status_match.group(1)}': {shown_path}",
            )

        if not date_match:
            add_error(errors, "AFS201", f"Missing Date metadata: {shown_path}")
        else:
            try:
                datetime.strptime(date_match.group(1), "%Y-%m-%d")
            except ValueError:
                add_error(
                    errors,
                    "AFS203",
                    f"Invalid ADR date '{date_match.group(1)}': {shown_path}",
                )

        for section in REQUIRED_SECTIONS:
            if section not in content:
                add_error(
                    errors,
                    "AFS204",
                    f"Missing section '{section}': {shown_path}",
                )


def validate_duplicate_adr_numbers(root: Path, errors: list[str]) -> None:
    numbers = adr_numbers(root)
    for number in sorted({n for n in numbers if numbers.count(n) > 1}):
        add_error(errors, "AFS102", f"Duplicate ADR number: {number:04d}")


def validate_first_adr_number(root: Path, errors: list[str]) -> None:
    numbers = adr_numbers(root)
    if numbers and min(numbers) != 1:
        add_error(errors, "AFS105", "First ADR number must be 0001")


def validate_contiguous_adr_numbers(root: Path, errors: list[str]) -> None:
    numbers = sorted(set(adr_numbers(root)))
    if len(numbers) < 2:
        return

    for number in range(numbers[0], numbers[-1] + 1):
        if number not in numbers:
            add_error(errors, "AFS104", f"Missing ADR number: {number:04d}")


VALIDATION_RULES: tuple[ValidationRule, ...] = (
    validate_required_paths,
    validate_adr_directory_entries,
    validate_adr_files,
    validate_duplicate_adr_numbers,
    validate_first_adr_number,
    validate_contiguous_adr_numbers,
)


def validate_repository(root: Path) -> list[str]:
    root = root.resolve()
    errors: list[str] = []

    for rule in VALIDATION_RULES:
        rule(root, errors)

    return errors


def command_init(args: argparse.Namespace) -> int:
    root = Path(args.path)
    (root / ADR_RELATIVE_DIR).mkdir(parents=True, exist_ok=True)

    created = False
    for relative_path, content in INITIAL_FILES.items():
        path = root / relative_path
        if path.exists():
            continue

        path.write_text(content, encoding="utf-8")
        created = True

    if created:
        print(f"Initialized AFS repository at {root.resolve()}")
    else:
        print(f"AFS repository already initialized at {root.resolve()}")

    return 0


def command_validate(args: argparse.Namespace) -> int:
    root = Path(args.path)
    errors = validate_repository(root)

    if errors:
        print("Validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("AFS repository validation passed.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="afs", description="AFS repository tooling")
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="Initialize an AFS repository")
    init.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Directory to initialize (default: current directory)",
    )
    init.set_defaults(func=command_init)

    validate = sub.add_parser("validate", help="Validate an AFS repository")
    validate.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Repository path to validate (default: current directory)",
    )
    validate.set_defaults(func=command_validate)

    adr = sub.add_parser("adr", help="Manage architecture decision records")
    adr_sub = adr.add_subparsers(dest="adr_command", required=True)

    adr_new = adr_sub.add_parser("new", help="Create a new ADR")
    adr_new.add_argument("title")
    adr_new.add_argument("--directory", default=str(ADR_RELATIVE_DIR))
    adr_new.set_defaults(func=command_adr_new)

    adr_list = adr_sub.add_parser("list", help="List ADR files")
    adr_list.add_argument("--directory", default=str(ADR_RELATIVE_DIR))
    adr_list.set_defaults(func=command_adr_list)

    return parser


def main() -> None:
    args = build_parser().parse_args()
    try:
        result = args.func(args)
    except OSError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    raise SystemExit(result)


if __name__ == "__main__":
    main()
