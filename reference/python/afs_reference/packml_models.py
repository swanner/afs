"""Immutable values exchanged by the declarative PackML runtime."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType

from .packml_states import PackMLState


class AlarmResponse(str, Enum):
    ABORT = "ABORT"
    HOLD = "HOLD"
    SUSPEND = "SUSPEND"


JsonScalar = str | int | float | bool | None
JsonValue = JsonScalar | tuple["JsonValue", ...] | Mapping[str, "JsonValue"]


def plain_json(value: JsonValue) -> object:
    if isinstance(value, Mapping):
        return {key: plain_json(child) for key, child in value.items()}
    if isinstance(value, tuple):
        return [plain_json(child) for child in value]
    return value


@dataclass(frozen=True)
class ComponentAlarm:
    code: str
    response: AlarmResponse | None
    details: JsonValue = MappingProxyType({})


@dataclass(frozen=True)
class PackMLAlarm:
    source: str
    code: str
    response: AlarmResponse | None
    details: JsonValue

    def to_dict(self) -> dict[str, object]:
        return {
            "source": self.source,
            "code": self.code,
            "response": self.response.value if self.response else None,
            "details": plain_json(self.details),
        }


@dataclass(frozen=True)
class ComponentResult:
    SC: bool = True
    alarms: tuple[ComponentAlarm | Mapping[str, object], ...] = ()
    outputs: Mapping[str, object] = MappingProxyType({})

    def __post_init__(self) -> None:
        if not isinstance(self.SC, bool):
            raise TypeError("component_result SC must be boolean")
        if not isinstance(self.alarms, tuple):
            raise TypeError("component_result alarms must be a tuple")
        if not isinstance(self.outputs, Mapping):
            raise TypeError("component_result outputs must be a mapping")


def component_result(
    *,
    SC: bool = True,
    alarms: Iterable[ComponentAlarm | Mapping[str, object]] = (),
    outputs: Mapping[str, object] | None = None,
) -> ComponentResult:
    if not isinstance(SC, bool):
        raise TypeError("component_result SC must be boolean")
    if outputs is not None and not isinstance(outputs, Mapping):
        raise TypeError("component_result outputs must be a mapping")
    return ComponentResult(
        SC=SC,
        alarms=tuple(alarms),
        outputs=MappingProxyType(dict(outputs or {})),
    )


@dataclass(frozen=True)
class PackMLSnapshot:
    unit_id: str | None
    state: PackMLState
    state_entered_at: float
    alarms: tuple[PackMLAlarm, ...]
    abort_reason: str | None
    failed_from_state: PackMLState | None

    def to_dict(self) -> dict[str, object]:
        return {
            "unitId": self.unit_id,
            "state": self.state.value,
            "stateEnteredAt": self.state_entered_at,
            "alarms": [alarm.to_dict() for alarm in self.alarms],
            "abortReason": self.abort_reason,
            "failedFromState": (
                self.failed_from_state.value if self.failed_from_state else None
            ),
        }


@dataclass(frozen=True)
class PackMLContext:
    machine: PackMLSnapshot
    input: Mapping[str, object]
    now: float
    elapsed_ms: float


@dataclass(frozen=True)
class MachineComponentResult:
    name: str
    SC: bool
    alarms: tuple[PackMLAlarm, ...]
    outputs: Mapping[str, object]


@dataclass(frozen=True)
class PackMLScanResult:
    snapshot: PackMLSnapshot
    previous_state: PackMLState
    transitioned: bool
    transitions: int
    SC: bool
    component_results: tuple[MachineComponentResult, ...]


Component = Callable[[PackMLContext], ComponentResult]


__all__ = [
    "AlarmResponse",
    "Component",
    "ComponentAlarm",
    "ComponentResult",
    "JsonScalar",
    "JsonValue",
    "MachineComponentResult",
    "PackMLAlarm",
    "PackMLContext",
    "PackMLScanResult",
    "PackMLSnapshot",
    "component_result",
]
