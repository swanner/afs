"""Minimal Unit contract for the current declarative reference."""

from __future__ import annotations

from .packml_machine import PackMLMachine, PackMLSnapshot


class PackMLUnit:
    """Own one authoritative declarative ``PackMLMachine``."""

    def __init__(self, *, name: str, machine: PackMLMachine) -> None:
        if not name.strip():
            raise ValueError("Unit name must not be empty")
        self._name = name
        self._machine = machine
        self._owner: object | None = None

    @property
    def name(self) -> str:
        return self._name

    @property
    def machine(self) -> PackMLMachine:
        return self._machine

    @property
    def owner(self) -> object | None:
        return self._owner

    @property
    def snapshot(self) -> PackMLSnapshot:
        return self._machine.snapshot()

    def _claim_owner(self, owner: object) -> None:
        if self._owner is not None:
            raise ValueError("Unit already has an owner")
        self._owner = owner

    def scan(self) -> None:
        raise NotImplementedError
