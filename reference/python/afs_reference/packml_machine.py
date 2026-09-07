from __future__ import annotations

import json
import math
import time
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType

from .packml import PackMLState


SC_TIMEOUT_MS = 90_000
MAX_INTERNAL_STEPS = 64
PACKML_ALARM_SOURCE = "PackMLMachine"


class AlarmResponse(str, Enum):
    ABORT = "ABORT"
    HOLD = "HOLD"
    SUSPEND = "SUSPEND"


PACKML_STATES = frozenset(
    state for state in PackMLState if state is not PackMLState.SYSTEM_FAILURE
)
TRANSIENT_STATES = frozenset(
    {
        PackMLState.ABORTING,
        PackMLState.CLEARING,
        PackMLState.STOPPING,
        PackMLState.RESETTING,
        PackMLState.STARTING,
        PackMLState.COMPLETING,
        PackMLState.HOLDING,
        PackMLState.UNHOLDING,
        PackMLState.SUSPENDING,
        PackMLState.UNSUSPENDING,
    }
)
TERMINAL_STATES = frozenset(
    {
        PackMLState.STOPPED,
        PackMLState.COMPLETE,
        PackMLState.ABORTED,
        PackMLState.SYSTEM_FAILURE,
    }
)


_PACKML_TRANSITIONS: dict[PackMLState, tuple[PackMLState, ...]] = {
    PackMLState.ABORTED: (PackMLState.CLEARING,),
    PackMLState.ABORTING: (PackMLState.ABORTED,),
    PackMLState.CLEARING: (PackMLState.STOPPED,),
    PackMLState.STOPPED: (PackMLState.RESETTING,),
    PackMLState.STOPPING: (PackMLState.STOPPED,),
    PackMLState.RESETTING: (PackMLState.IDLE,),
    PackMLState.IDLE: (PackMLState.STARTING,),
    PackMLState.STARTING: (PackMLState.EXECUTE,),
    PackMLState.EXECUTE: (
        PackMLState.COMPLETING,
        PackMLState.HOLDING,
        PackMLState.SUSPENDING,
    ),
    PackMLState.COMPLETING: (PackMLState.COMPLETE,),
    PackMLState.COMPLETE: (PackMLState.RESETTING,),
    PackMLState.HOLDING: (PackMLState.HELD,),
    PackMLState.HELD: (PackMLState.UNHOLDING,),
    PackMLState.UNHOLDING: (PackMLState.EXECUTE,),
    PackMLState.SUSPENDING: (PackMLState.SUSPENDED,),
    PackMLState.SUSPENDED: (PackMLState.UNSUSPENDING,),
    PackMLState.UNSUSPENDING: (PackMLState.EXECUTE,),
}
_STOP_EXCLUDED = frozenset(
    {
        PackMLState.ABORTED,
        PackMLState.ABORTING,
        PackMLState.CLEARING,
        PackMLState.STOPPED,
        PackMLState.STOPPING,
        PackMLState.COMPLETING,
        PackMLState.SYSTEM_FAILURE,
    }
)
_ABORT_EXCLUDED = frozenset(
    {PackMLState.ABORTED, PackMLState.ABORTING, PackMLState.SYSTEM_FAILURE}
)
BASE_TRANSITIONS = MappingProxyType(
    {
        state: tuple(
            dict.fromkeys(
                _PACKML_TRANSITIONS.get(state, ())
                + (() if state in _STOP_EXCLUDED else (PackMLState.STOPPING,))
                + (() if state in _ABORT_EXCLUDED else (PackMLState.ABORTING,))
                + (PackMLState.SYSTEM_FAILURE,)
            )
        )
        for state in PACKML_STATES
    }
    | {PackMLState.SYSTEM_FAILURE: (PackMLState.ABORTING,)}
)


JsonScalar = str | int | float | bool | None
JsonValue = JsonScalar | tuple["JsonValue", ...] | Mapping[str, "JsonValue"]


def _timestamp(value: object, name: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
    ):
        raise TypeError(f"{name} must be a finite timestamp")
    if value < 0:
        raise TypeError(f"{name} must be a non-negative timestamp")
    return value


def _json_value(value: object, *, name: str, seen: set[int] | None = None) -> JsonValue:
    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if not math.isfinite(value):
            raise TypeError(f"{name} must be JSON-like")
        return value
    seen = set() if seen is None else seen
    identity = id(value)
    if identity in seen:
        raise TypeError(f"{name} must be JSON-like")
    seen.add(identity)
    try:
        if isinstance(value, (list, tuple)):
            return tuple(_json_value(item, name=name, seen=seen) for item in value)
        if isinstance(value, Mapping) and all(isinstance(key, str) for key in value):
            return MappingProxyType(
                {
                    key: _json_value(value[key], name=name, seen=seen)
                    for key in sorted(value)
                }
            )
    finally:
        seen.remove(identity)
    raise TypeError(f"{name} must be JSON-like")


def _plain(value: JsonValue) -> object:
    if isinstance(value, Mapping):
        return {key: _plain(child) for key, child in value.items()}
    if isinstance(value, tuple):
        return [_plain(child) for child in value]
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
            "details": _plain(self.details),
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


def _response(value: object, source: str) -> AlarmResponse | None:
    if value is None:
        return None
    try:
        return AlarmResponse(value)
    except (TypeError, ValueError) as error:
        raise TypeError(f"Invalid alarm response from PackML component: {source}") from error


def _component_alarm(
    source: str, alarm: ComponentAlarm | Mapping[str, object]
) -> PackMLAlarm:
    if isinstance(alarm, ComponentAlarm):
        code, response, details = alarm.code, alarm.response, alarm.details
    elif isinstance(alarm, Mapping):
        if set(alarm) - {"code", "response", "details"} or "response" not in alarm:
            raise TypeError(f"Invalid alarm from PackML component: {source}")
        code = alarm.get("code")
        response = _response(alarm.get("response"), source)
        details = alarm.get("details", {})
    else:
        raise TypeError(f"Invalid alarm from PackML component: {source}")
    if not isinstance(code, str) or not code:
        raise TypeError(f"Invalid alarm from PackML component: {source}")
    if (
        isinstance(alarm, ComponentAlarm)
        and response is not None
        and not isinstance(response, AlarmResponse)
    ):
        response = _response(response, source)
    return PackMLAlarm(
        source=source,
        code=code,
        response=response,
        details=_json_value(
            details,
            name=f"Invalid alarm details from PackML component: {source}",
        ),
    )


def _alarm_key(alarm: PackMLAlarm) -> str:
    return json.dumps(alarm.to_dict(), sort_keys=True, separators=(",", ":"))


def _sort_alarms(alarms: Iterable[PackMLAlarm]) -> tuple[PackMLAlarm, ...]:
    return tuple(sorted(alarms, key=_alarm_key))


def _snapshot_alarm(alarm: object) -> PackMLAlarm:
    if isinstance(alarm, PackMLAlarm):
        source, code, response, details = (
            alarm.source,
            alarm.code,
            alarm.response,
            alarm.details,
        )
    elif isinstance(alarm, Mapping):
        if set(alarm) - {"source", "code", "response", "details"} or "details" not in alarm:
            raise TypeError("snapshot contains an invalid normalized alarm")
        source, code = alarm.get("source"), alarm.get("code")
        try:
            response = (
                None
                if alarm.get("response") is None
                else AlarmResponse(alarm.get("response"))
            )
        except (TypeError, ValueError) as error:
            raise TypeError("snapshot contains an invalid normalized alarm") from error
        details = alarm.get("details")
    else:
        raise TypeError("snapshot contains an invalid normalized alarm")
    if not isinstance(source, str) or not source or not isinstance(code, str) or not code:
        raise TypeError("snapshot contains an invalid normalized alarm")
    try:
        normalized_details = _json_value(details, name="snapshot alarm details")
    except TypeError as error:
        raise TypeError("snapshot contains an invalid normalized alarm") from error
    return PackMLAlarm(source, code, response, normalized_details)


def validate_snapshot(
    snapshot: PackMLSnapshot | Mapping[str, object], now: float
) -> PackMLSnapshot:
    _timestamp(now, "snapshot restoration now")
    if isinstance(snapshot, PackMLSnapshot):
        raw = snapshot.to_dict()
    elif isinstance(snapshot, Mapping):
        raw = snapshot
    else:
        raise TypeError("snapshot must be a mapping")
    try:
        state = PackMLState(raw.get("state"))
    except (TypeError, ValueError) as error:
        raise TypeError(f"Unknown PackML state: {raw.get('state')}") from error
    entered_at = _timestamp(raw.get("stateEnteredAt"), "snapshot stateEnteredAt")
    if entered_at > now:
        raise TypeError("snapshot stateEnteredAt must not be in the future")
    raw_alarms = raw.get("alarms")
    if not isinstance(raw_alarms, (list, tuple)):
        raise TypeError("snapshot alarms must be an array")
    alarms = _sort_alarms(_snapshot_alarm(alarm) for alarm in raw_alarms)
    if "abortReason" not in raw:
        raise TypeError("snapshot abortReason must be a string or null")
    abort_reason = raw.get("abortReason")
    if abort_reason is not None and not isinstance(abort_reason, str):
        raise TypeError("snapshot abortReason must be a string or null")
    raw_failed = raw.get("failedFromState")
    try:
        failed_from = None if raw_failed is None else PackMLState(raw_failed)
    except (TypeError, ValueError) as error:
        raise TypeError("snapshot failedFromState must be a PackML state or null") from error
    if failed_from is PackMLState.SYSTEM_FAILURE:
        raise TypeError("snapshot failedFromState must be a PackML state or null")
    unit_id = raw.get("unitId")
    if unit_id is not None and not isinstance(unit_id, str):
        raise TypeError("snapshot unitId must be a string or null")
    restored = PackMLSnapshot(unit_id, state, entered_at, alarms, abort_reason, failed_from)
    _validate_system_failure_snapshot(restored)
    return restored


def _validate_system_failure_snapshot(snapshot: PackMLSnapshot) -> None:
    if snapshot.state is not PackMLState.SYSTEM_FAILURE:
        return
    if snapshot.failed_from_state not in TRANSIENT_STATES:
        raise TypeError(
            "SYSTEM_FAILURE snapshot failedFromState must be SC-timeout-capable"
        )
    if snapshot.abort_reason is None:
        raise TypeError("SYSTEM_FAILURE snapshot requires abortReason")
    if (
        snapshot.failed_from_state not in {PackMLState.ABORTING, PackMLState.CLEARING}
        and snapshot.abort_reason != "SC_TIMEOUT"
    ):
        raise TypeError(
            "SYSTEM_FAILURE snapshot abortReason must be SC_TIMEOUT unless previously latched"
        )
    timeouts = tuple(
        alarm
        for alarm in snapshot.alarms
        if alarm.source == PACKML_ALARM_SOURCE and alarm.code == "SC_TIMEOUT"
    )
    if len(timeouts) != 1:
        raise TypeError(
            "SYSTEM_FAILURE snapshot requires exactly one PackMLMachine SC_TIMEOUT alarm"
        )
    timeout = timeouts[0]
    details = _plain(timeout.details)
    if (
        timeout.response is not None
        or not isinstance(details, dict)
        or set(details) != {"state", "timeoutMs"}
        or details["state"] != snapshot.failed_from_state.value
        or isinstance(details["timeoutMs"], bool)
        or not isinstance(details["timeoutMs"], (int, float))
        or not math.isfinite(details["timeoutMs"])
        or details["timeoutMs"] <= 0
    ):
        raise TypeError("SYSTEM_FAILURE snapshot contains an invalid SC_TIMEOUT alarm")


def legal_transition(source: PackMLState | str, target: PackMLState | str) -> bool:
    try:
        return PackMLState(target) in BASE_TRANSITIONS.get(PackMLState(source), ())
    except (TypeError, ValueError):
        return False


class PackMLMachine:
    """Declarative, component-based PackML runtime with strict recovery semantics."""

    def __init__(
        self,
        *,
        unit_id: str | None = None,
        initial_state: PackMLState | str = PackMLState.STOPPED,
        now: float | None = None,
        sc_timeout_ms: float = SC_TIMEOUT_MS,
        snapshot: PackMLSnapshot | Mapping[str, object] | None = None,
    ) -> None:
        if (
            isinstance(sc_timeout_ms, bool)
            or not isinstance(sc_timeout_ms, (int, float))
            or not math.isfinite(sc_timeout_ms)
            or sc_timeout_ms <= 0
        ):
            raise TypeError("sc_timeout_ms must be positive")
        if snapshot is not None and now is None:
            raise TypeError("now is required when restoring a PackML snapshot")
        restoration_now = now if now is not None else time.time() * 1000
        if snapshot is not None:
            restored = validate_snapshot(snapshot, restoration_now)
        else:
            _timestamp(restoration_now, "now")
            try:
                state = PackMLState(initial_state)
            except (TypeError, ValueError) as error:
                raise TypeError(f"Unknown PackML state: {initial_state}") from error
            restored = PackMLSnapshot(unit_id, state, restoration_now, (), None, None)
        self._unit_id = restored.unit_id
        self._state = restored.state
        self._state_entered_at = restored.state_entered_at
        self._alarms = restored.alarms
        self._abort_reason = restored.abort_reason
        self._failed_from_state = restored.failed_from_state
        self._sc_timeout_ms = sc_timeout_ms
        self._components: dict[str, Component] = {}

    @property
    def state(self) -> PackMLState:
        return self._state

    def register_component(self, name: str, component: Component) -> PackMLMachine:
        if not isinstance(name, str) or not name:
            raise TypeError("Component name must be a non-empty string")
        if name == PACKML_ALARM_SOURCE:
            raise TypeError(f"Component name is reserved: {name}")
        if not callable(component):
            raise TypeError("A PackML component must be a pure function")
        if name in self._components:
            raise ValueError(f"PackML component already registered: {name}")
        self._components[name] = component
        return self

    def snapshot(self) -> PackMLSnapshot:
        return PackMLSnapshot(
            self._unit_id,
            self._state,
            self._state_entered_at,
            self._alarms,
            self._abort_reason,
            self._failed_from_state,
        )

    def scan(
        self,
        *,
        operation_requested: bool = False,
        acknowledge_requested: bool = False,
        input: Mapping[str, object] | None = None,
        now: float | None = None,
    ) -> PackMLScanResult:
        scan_now = time.time() * 1000 if now is None else now
        _timestamp(scan_now, "now")
        if not isinstance(operation_requested, bool):
            raise TypeError("operation_requested must be boolean")
        if not isinstance(acknowledge_requested, bool):
            raise TypeError("acknowledge_requested must be boolean")
        if input is not None and not isinstance(input, Mapping):
            raise TypeError("input must be a mapping")
        if not self._components:
            raise RuntimeError("PackMLMachine requires at least one registered component")
        frozen_input = _json_value(dict(input or {}), name="input")
        if not isinstance(frozen_input, Mapping):
            raise TypeError("input must be a mapping")
        previous_state = self._state
        transitions = 0
        terminal_boundary = False
        recovery_requested = (
            previous_state is PackMLState.SYSTEM_FAILURE and acknowledge_requested
        )
        final_results: tuple[MachineComponentResult, ...] = ()
        final_sc = True
        for _ in range(MAX_INTERNAL_STEPS):
            context = PackMLContext(
                self.snapshot(),
                frozen_input,
                scan_now,
                max(0, scan_now - self._state_entered_at),
            )
            evaluated: list[MachineComponentResult] = []
            for name, component in self._components.items():
                result = component(context)
                if not isinstance(result, ComponentResult):
                    raise TypeError(f"Invalid result from PackML component: {name}")
                normalized = tuple(
                    _component_alarm(name, alarm) for alarm in result.alarms
                )
                evaluated.append(
                    MachineComponentResult(
                        name,
                        result.SC,
                        normalized,
                        MappingProxyType(dict(result.outputs)),
                    )
                )
            final_results = tuple(evaluated)
            final_sc = all(result.SC for result in final_results)
            alarms = [alarm for result in final_results for alarm in result.alarms]
            if self._state is PackMLState.SYSTEM_FAILURE:
                alarms.extend(
                    alarm
                    for alarm in self._alarms
                    if alarm.source == PACKML_ALARM_SOURCE and alarm.code == "SC_TIMEOUT"
                )
            if (
                not final_sc
                and self._state in TRANSIENT_STATES
                and scan_now - self._state_entered_at
                >= self._sc_timeout_ms
            ):
                failed_from = self._state
                alarms.append(
                    _component_alarm(
                        PACKML_ALARM_SOURCE,
                        {
                            "code": "SC_TIMEOUT",
                            "response": None,
                            "details": {
                                "state": failed_from.value,
                                "timeoutMs": self._sc_timeout_ms,
                            },
                        },
                    )
                )
                self._alarms = _sort_alarms(alarms)
                if self._abort_reason is None:
                    self._abort_reason = "SC_TIMEOUT"
                self._failed_from_state = failed_from
                self._enter(PackMLState.SYSTEM_FAILURE, scan_now)
                transitions += 1
                terminal_boundary = True
                continue
            normalized_alarms = _sort_alarms(alarms)
            if normalized_alarms != self._alarms:
                self._alarms = normalized_alarms
                continue
            abort_alarm = next(
                (
                    alarm
                    for alarm in normalized_alarms
                    if alarm.response is AlarmResponse.ABORT
                ),
                None,
            )
            abort_requested = (
                abort_alarm is not None
                and self._state
                not in {
                    PackMLState.ABORTED,
                    PackMLState.ABORTING,
                    PackMLState.SYSTEM_FAILURE,
                }
            )
            if abort_requested and self._abort_reason is None and abort_alarm is not None:
                details = _plain(abort_alarm.details)
                self._abort_reason = str(
                    details.get("reason", details.get("message", abort_alarm.code))
                    if isinstance(details, dict)
                    else abort_alarm.code
                )
            if terminal_boundary and not abort_requested:
                return self._result(previous_state, transitions, final_sc, final_results)
            responses = {alarm.response for alarm in normalized_alarms}
            if not self._apply_state(
                abort_requested=abort_requested,
                operation_requested=operation_requested,
                acknowledge_requested=acknowledge_requested,
                responses=responses,
                SC=final_sc,
                now=scan_now,
            ):
                return self._result(previous_state, transitions, final_sc, final_results)
            transitions += 1
            terminal_boundary = self._state in TERMINAL_STATES and not (
                recovery_requested and self._state is PackMLState.ABORTED
            )
        raise RuntimeError(
            f"PackML internal step maximum ({MAX_INTERNAL_STEPS}) exceeded"
        )

    def _result(
        self,
        previous_state: PackMLState,
        transitions: int,
        SC: bool,
        components: tuple[MachineComponentResult, ...],
    ) -> PackMLScanResult:
        return PackMLScanResult(
            self.snapshot(), previous_state, transitions > 0, transitions, SC, components
        )

    def _apply_state(
        self,
        *,
        abort_requested: bool,
        operation_requested: bool,
        acknowledge_requested: bool,
        responses: set[AlarmResponse | None],
        SC: bool,
        now: float,
    ) -> bool:
        before = self._state
        if abort_requested:
            self._enter(PackMLState.ABORTING, now)
        elif self._state is PackMLState.ABORTED:
            if acknowledge_requested and AlarmResponse.ABORT not in responses:
                self._enter(PackMLState.CLEARING, now)
        elif self._state is PackMLState.SYSTEM_FAILURE:
            if SC and acknowledge_requested:
                self._enter(PackMLState.ABORTING, now)
        elif self._state is PackMLState.ABORTING:
            if SC:
                self._enter(PackMLState.ABORTED, now)
        elif self._state is PackMLState.CLEARING:
            if SC:
                self._abort_reason = None
                self._failed_from_state = None
                self._enter(PackMLState.STOPPED, now)
        elif self._state is PackMLState.STOPPED:
            if operation_requested:
                self._enter(PackMLState.RESETTING, now)
        elif self._state is PackMLState.STOPPING:
            if SC:
                self._enter(PackMLState.STOPPED, now)
        elif self._state is PackMLState.RESETTING:
            if not operation_requested:
                self._enter(PackMLState.STOPPING, now)
            elif SC:
                self._enter(PackMLState.IDLE, now)
        elif self._state is PackMLState.IDLE:
            self._enter(
                PackMLState.STARTING if operation_requested else PackMLState.STOPPING,
                now,
            )
        elif self._state is PackMLState.STARTING:
            if not operation_requested:
                self._enter(PackMLState.STOPPING, now)
            elif SC:
                self._enter(PackMLState.EXECUTE, now)
        elif self._state is PackMLState.EXECUTE:
            if not operation_requested:
                self._enter(PackMLState.STOPPING, now)
            elif AlarmResponse.HOLD in responses:
                self._enter(PackMLState.HOLDING, now)
            elif AlarmResponse.SUSPEND in responses:
                self._enter(PackMLState.SUSPENDING, now)
            elif SC:
                self._enter(PackMLState.COMPLETING, now)
        elif self._state is PackMLState.COMPLETING:
            if SC:
                self._enter(PackMLState.COMPLETE, now)
        elif self._state is PackMLState.COMPLETE:
            self._enter(
                PackMLState.RESETTING if operation_requested else PackMLState.STOPPING,
                now,
            )
        elif self._state is PackMLState.HOLDING:
            if not operation_requested:
                self._enter(PackMLState.STOPPING, now)
            elif SC:
                self._enter(PackMLState.HELD, now)
        elif self._state is PackMLState.HELD:
            if not operation_requested:
                self._enter(PackMLState.STOPPING, now)
            elif AlarmResponse.HOLD not in responses:
                self._enter(PackMLState.UNHOLDING, now)
        elif self._state is PackMLState.UNHOLDING:
            if not operation_requested:
                self._enter(PackMLState.STOPPING, now)
            elif SC:
                self._enter(PackMLState.EXECUTE, now)
        elif self._state is PackMLState.SUSPENDING:
            if not operation_requested:
                self._enter(PackMLState.STOPPING, now)
            elif SC:
                self._enter(PackMLState.SUSPENDED, now)
        elif self._state is PackMLState.SUSPENDED:
            if not operation_requested:
                self._enter(PackMLState.STOPPING, now)
            elif AlarmResponse.SUSPEND not in responses:
                self._enter(PackMLState.UNSUSPENDING, now)
        elif self._state is PackMLState.UNSUSPENDING:
            if not operation_requested:
                self._enter(PackMLState.STOPPING, now)
            elif SC:
                self._enter(PackMLState.EXECUTE, now)
        else:
            raise RuntimeError(f"Unhandled PackML state: {self._state.value}")
        return before is not self._state

    def _enter(self, target: PackMLState, now: float) -> None:
        if target is self._state:
            return
        if not legal_transition(self._state, target):
            raise RuntimeError(
                f"Illegal PackML transition: {self._state.value} -> {target.value}"
            )
        self._state = target
        self._state_entered_at = now


__all__ = [
    "AlarmResponse",
    "BASE_TRANSITIONS",
    "ComponentAlarm",
    "ComponentResult",
    "MAX_INTERNAL_STEPS",
    "MachineComponentResult",
    "PACKML_ALARM_SOURCE",
    "PACKML_STATES",
    "PackMLContext",
    "PackMLMachine",
    "PackMLScanResult",
    "PackMLSnapshot",
    "SC_TIMEOUT_MS",
    "TERMINAL_STATES",
    "TRANSIENT_STATES",
    "component_result",
    "legal_transition",
    "validate_snapshot",
]
