from __future__ import annotations

from collections.abc import Iterable

from .unit_runtime import PackMLUnit


class Application:
    """Owns Units and executes them explicitly in registration order."""

    def __init__(self) -> None:
        self._units: list[PackMLUnit] = []

    @property
    def units(self) -> Iterable[PackMLUnit]:
        return tuple(self._units)

    def add_unit(self, unit: PackMLUnit) -> None:
        """Register one Unit explicitly; AFS performs no automatic discovery."""
        if not isinstance(unit, PackMLUnit):
            raise TypeError("Application accepts PackMLUnit instances only")
        if unit in self._units:
            raise ValueError("Unit is already registered")
        unit._claim_owner(self)
        self._units.append(unit)

    def run(self, scans: int = 1) -> None:
        if scans < 1:
            raise ValueError("scans must be at least 1")

        for _ in range(scans):
            for unit in self._units:
                unit.scan()
