"""PackML scan orchestration and its central explicit state switch."""

from __future__ import annotations

import math
import time
from collections.abc import Mapping
from types import MappingProxyType

from .packml_models import (
    AlarmResponse,
    Component,
    ComponentResult,
    MachineComponentResult,
    PackMLContext,
    PackMLScanResult,
    PackMLSnapshot,
    plain_json,
)
from .packml_states import (
    PackMLState,
    TERMINAL_STATES,
    TRANSIENT_STATES,
    legal_transition,
)
from .packml_validation import (
    PACKML_ALARM_SOURCE,
    freeze_json,
    normalize_component_alarm,
    sort_alarms,
    validate_snapshot,
    validate_timestamp,
)


SC_TIMEOUT_MS = 90_000
MAX_INTERNAL_STEPS = 64


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
            validate_timestamp(restoration_now, "now")
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
        validate_timestamp(scan_now, "now")
        if not isinstance(operation_requested, bool):
            raise TypeError("operation_requested must be boolean")
        if not isinstance(acknowledge_requested, bool):
            raise TypeError("acknowledge_requested must be boolean")
        if input is not None and not isinstance(input, Mapping):
            raise TypeError("input must be a mapping")
        if not self._components:
            raise RuntimeError("PackMLMachine requires at least one registered component")
        frozen_input = freeze_json(dict(input or {}), name="input")
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
                    normalize_component_alarm(name, alarm) for alarm in result.alarms
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
                and scan_now - self._state_entered_at >= self._sc_timeout_ms
            ):
                failed_from = self._state
                alarms.append(
                    normalize_component_alarm(
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
                self._alarms = sort_alarms(alarms)
                if self._abort_reason is None:
                    self._abort_reason = "SC_TIMEOUT"
                self._failed_from_state = failed_from
                self._enter(PackMLState.SYSTEM_FAILURE, scan_now)
                transitions += 1
                terminal_boundary = True
                continue

            normalized_alarms = sort_alarms(alarms)
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
                details = plain_json(abort_alarm.details)
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
        """Apply priorities and one explicit PackML state case."""
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


__all__ = ["MAX_INTERNAL_STEPS", "PackMLMachine", "SC_TIMEOUT_MS"]
