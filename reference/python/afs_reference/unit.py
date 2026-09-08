"""Current component-based Unit example."""

from __future__ import annotations

from dataclasses import dataclass
from functools import partial

from .packml_machine import (
    ComponentAlarm,
    ComponentResult,
    PackMLContext,
    PackMLMachine,
    PackMLSnapshot,
    PackMLState,
    component_result,
)
from .unit_runtime import PackMLUnit


# AFS TEMPLATE WORKFLOW: replace both AFS_TEMPLATE_* identifiers, then adapt
# every AFS REQUIRED ADAPTATION marker while retaining the AFS PATTERN rules.


@dataclass(frozen=True)
class UnitStatus:
    name: str
    state: PackMLState
    snapshot: PackMLSnapshot
    value: int
    alarm: str | None


# =============================================================================
# AFS TEMPLATE 02
#
# Template purpose:
#     Pure business component evaluated by PackMLMachine.
#
# Example replacement:
#     charging_component
# =============================================================================
def AFS_TEMPLATE_02_COMPONENT(
    context: PackMLContext, *, target: int
) -> ComponentResult:
    """Return lifecycle evidence without changing Unit or machine state."""
    value = context.input.get("value")
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("value must be an integer")
    # AFS OPTIONAL: retain only alarms meaningful to the adapted Unit.
    alarms = (
        (ComponentAlarm("TARGET_EXCEEDED", None, {"target": target, "value": value}),)
        if value > target
        else ()
    )
    return component_result(
        SC=context.machine.state is not PackMLState.EXECUTE or value >= target,
        alarms=alarms,
        outputs={"value": value},
    )


# =============================================================================
# AFS TEMPLATE 01
#
# Template purpose:
#     Concrete business Unit class.
#
# Example replacement:
#     ChargingUnit
# =============================================================================
class AFS_TEMPLATE_01_UNIT(PackMLUnit):
    """Reference Unit that owns the current declarative PackMLMachine."""

    def __init__(self, target: int = 3) -> None:
        if target < 1:
            raise ValueError("target must be at least 1")
        self._value = 0
        self._scan_now = 0
        machine = PackMLMachine(unit_id="template-unit", now=0)
        machine.register_component(
            "target",
            partial(AFS_TEMPLATE_02_COMPONENT, target=target),
        )
        super().__init__(name="template-unit", machine=machine)

    @property
    def status(self) -> UnitStatus:
        snapshot = self.snapshot
        alarm = (
            "target exceeded"
            if any(item.code == "TARGET_EXCEEDED" for item in snapshot.alarms)
            else None
        )
        return UnitStatus(
            name=self.name,
            state=snapshot.state,
            snapshot=snapshot,
            value=self._value,
            alarm=alarm,
        )

    def scan(self) -> None:
        # AFS REQUIRED ADAPTATION: Replace this deterministic observation with
        # real input acquisition owned by the Unit.
        if self.machine.state is PackMLState.EXECUTE:
            self._value += 1
        self._scan_now += 1

        # AFS PATTERN: persist result.snapshot before applying external effects
        # derived from component outputs.
        self.machine.scan(
            operation_requested=True,
            input={"value": self._value},
            now=self._scan_now,
        )
