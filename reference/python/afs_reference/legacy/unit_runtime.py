from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from .packml_lifecycle import LifecycleStatus, PackMLCommand, PackMLLifecycle


@dataclass(frozen=True)
class PackMLUnitStatus:
    name: str
    lifecycle: LifecycleStatus


class PackMLUnit:
    """Legacy ownership contract used by the 0.1 composition examples."""

    def __init__(self, *, name: str, lifecycle: PackMLLifecycle) -> None:
        if not name.strip():
            raise ValueError("Unit name must not be empty")
        self._name = name
        self._lifecycle = lifecycle
        self._owner: object | None = None
        self._subunits: list[PackMLUnit] = []

    @property
    def name(self) -> str:
        return self._name

    @property
    def lifecycle(self) -> PackMLLifecycle:
        return self._lifecycle

    @property
    def owner(self) -> object | None:
        return self._owner

    @property
    def subunits(self) -> Iterable[PackMLUnit]:
        return tuple(self._subunits)

    @property
    def status(self) -> PackMLUnitStatus:
        return PackMLUnitStatus(name=self.name, lifecycle=self.lifecycle.status)

    def request(self, command: PackMLCommand, *, reason: str | None = None) -> None:
        result = self._lifecycle.request(command, reason=reason)
        if not result.accepted:
            raise ValueError(result.reason or "lifecycle request rejected")

    def add_subunit(self, unit: PackMLUnit) -> None:
        if unit is self:
            raise ValueError("a Unit cannot own itself")
        if unit in self._subunits:
            raise ValueError("Subunit is already registered")
        if unit._contains(self):
            raise ValueError("Unit ownership must be acyclic")
        unit._claim_owner(self)
        self._subunits.append(unit)

    def _claim_owner(self, owner: object) -> None:
        if self._owner is not None:
            raise ValueError("Unit already has an owner")
        self._owner = owner

    def _contains(self, candidate: PackMLUnit) -> bool:
        return self is candidate or any(
            child._contains(candidate) for child in self._subunits
        )

    def scan(self) -> None:
        raise NotImplementedError
