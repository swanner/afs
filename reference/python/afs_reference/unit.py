"""
AFS Unit.

A Unit owns application state and its Sequencer.
It evaluates inputs, updates state and exposes status.
"""

from __future__ import annotations

from dataclasses import dataclass

from .sequencer import AFS_TEMPLATE_02_SEQUENCER, State


# =============================================================================
# AFS TEMPLATE WORKFLOW
# =============================================================================
#
# This file is part of the executable AFS Reference Implementation.
# To create application code from it:
#
# 1. Copy the complete reference implementation.
#
# 2. Perform project-wide Search & Replace for every identifier beginning with
#    "AFS_TEMPLATE_". The prefix is deliberately unique, so all required name
#    changes can be found safely.
#
#    Example:
#
#        AFS_TEMPLATE_01_UNIT
#            -> ChargingUnit
#
#        AFS_TEMPLATE_02_SEQUENCER
#            -> ChargingSequencer
#
#    This also updates integration code such as:
#
#        app.add_unit(AFS_TEMPLATE_01_UNIT(...))
#
#    Do not introduce another AFS_TEMPLATE_* identifier unless the adaptation
#    cannot reasonably be eliminated through a simpler architecture.
#
# 3. Search project-wide for "AFS REQUIRED ADAPTATION". Review and adapt every
#    occurrence. These markers identify application-specific behavior that a
#    name replacement cannot complete.
#
#    Example:
#
#        # AFS REQUIRED ADAPTATION: Replace this demonstration input with the
#        # real application input owned by this Unit.
#        self.value += 1
#
# 4. Search project-wide for "AFS OPTIONAL". Keep useful examples and delete
#    optional behavior that the application does not need.
#
# 5. Keep and follow "AFS PATTERN" comments. They explain architecture rules,
#    not demonstration details.
#
# 6. Run the application and its tests. No generator, decorator, reflection,
#    automatic registration, or hidden discovery is required.
#
# =============================================================================


@dataclass(frozen=True)
class UnitStatus:
    name: str
    state: State
    value: int
    alarm: str | None


# =============================================================================
# AFS TEMPLATE 01
#
# Template purpose:
#     Concrete business Unit class.
#
# Example replacement:
#     ChargingUnit
#
# This comment intentionally remains after customization. It documents the
# architectural role and origin of the class in the AFS Reference Implementation.
# =============================================================================
class AFS_TEMPLATE_01_UNIT:
    """Reference Unit demonstrating ownership, parameters, state and alarms."""

    def __init__(self, target: int = 3) -> None:
        self._name = "template-unit"
        self._value = 0
        self._start_requested = True
        self._alarm: str | None = None

        # AFS PATTERN: A Unit owns its Sequencer. The Application knows only
        # the Unit and never registers or drives the Sequencer directly.
        self._sequencer = AFS_TEMPLATE_02_SEQUENCER(target=target)

    @property
    def name(self) -> str:
        return self._name

    @property
    def status(self) -> UnitStatus:
        return UnitStatus(
            name=self.name,
            state=self._sequencer.state,
            value=self._value,
            alarm=self._alarm,
        )

    def scan(self) -> None:
        # AFS REQUIRED ADAPTATION: Replace this deterministic demonstration
        # input with the real input evaluation owned by this Unit.
        if self._sequencer.state is State.EXECUTE:
            self._value += 1

        state = self._sequencer.evaluate(
            value=self._value,
            start_requested=self._start_requested,
        )

        # AFS OPTIONAL: This alarm demonstrates that alarm creation remains in
        # the Unit that understands the underlying condition. Delete it when
        # the application does not need an equivalent alarm.
        self._alarm = "target exceeded" if self._value > self._sequencer.target else None

        if state is State.COMPLETE:
            self._start_requested = False
