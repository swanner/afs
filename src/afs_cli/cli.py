from __future__ import annotations

import argparse
import re
import sys
from datetime import date, datetime
from pathlib import Path

ADR_DIR = Path("specification/adr")
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

REQUIRED_PATHS = (
    Path("README.md"),
    Path("LICENSE"),
    Path("pyproject.toml"),
    ADR_DIR,
)

REQUIRED_SECTIONS = (
    "## Context",
    "## Decision",
    "## Consequences",
    "## Alternatives considered",
)


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


def validate_adr(path: Path, errors: list[str], numbers: list[int]) -> None:
    match = ADR_PATTERN.match(path.name)
    if not match:
        add_error(errors, "AFS002", f"Invalid ADR filename: {path}")
        return

    number = int(match.group(1))
    numbers.append(number)
    content = path.read_text(encoding="utf-8")

    heading_match = HEADING_PATTERN.search(content)
    if not heading_match or int(heading_match.group(1)) != number:
        add_error(errors, "AFS004", f"Missing or inconsistent ADR heading: {path}")

    status_match = STATUS_PATTERN.search(content)
    date_match = DATE_PATTERN.search(content)

    if not status_match:
        add_error(errors, "AFS005", f"Missing Status metadata: {path}")
    elif status_match.group(1) not in ALLOWED_STATUSES:
        add_error(
            errors,
            "AFS006",
            f"Invalid ADR status '{status_match.group(1)}': {path}",
        )

    if not date_match:
        add_error(errors, "AFS005", f"Missing Date metadata: {path}")
    else:
        try:
            datetime.strptime(date_match.group(1), "%Y-%m-%d")
        except ValueError:
            add_error(
                errors,
                "AFS007",
                f"Invalid ADR date '{date_match.group(1)}': {path}",
            )

    for section in REQUIRED_SECTIONS:
        if section not in content:
            add_error(errors, "AFS008", f"Missing section '{section}': {path}")


def command_validate(_: argparse.Namespace) -> int:
    errors: list[str] = []

    for path in REQUIRED_PATHS:
        if not path.exists():
            add_error(errors, "AFS001", f"Missing required path: {path}")

    numbers: list[int] = []
    if ADR_DIR.exists():
        for path in sorted(ADR_DIR.glob("*.md")):
            if path.name == "README.md":
                continue
            validate_adr(path, errors, numbers)

    for number in sorted({n for n in numbers if numbers.count(n) > 1}):
        add_error(errors, "AFS003", f"Duplicate ADR number: {number:04d}")

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

    validate = sub.add_parser("validate", help="Validate repository structure")
    validate.set_defaults(func=command_validate)

    adr = sub.add_parser("adr", help="Manage architecture decision records")
    adr_sub = adr.add_subparsers(dest="adr_command", required=True)

    adr_new = adr_sub.add_parser("new", help="Create a new ADR")
    adr_new.add_argument("title")
    adr_new.add_argument("--directory", default=str(ADR_DIR))
    adr_new.set_defaults(func=command_adr_new)

    adr_list = adr_sub.add_parser("list", help="List ADR files")
    adr_list.add_argument("--directory", default=str(ADR_DIR))
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
