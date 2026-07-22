from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol


class Unit(Protocol):
    """The minimal interface an AFS Unit exposes to the Application."""

    @property
    def name(self) -> str: ...

    def scan(self) -> None: ...


class Application:
    """Owns Units and executes them explicitly in registration order."""

    def __init__(self) -> None:
        self._units: list[Unit] = []

    @property
    def units(self) -> Iterable[Unit]:
        return tuple(self._units)

    def add_unit(self, unit: Unit) -> None:
        """Register one Unit explicitly; AFS performs no automatic discovery."""
        self._units.append(unit)

    def run(self, scans: int = 1) -> None:
        if scans < 1:
            raise ValueError("scans must be at least 1")

        for _ in range(scans):
            for unit in self._units:
                unit.scan()
