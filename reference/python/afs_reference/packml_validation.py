"""Alarm normalization and snapshot validation for ``PackMLMachine``."""

from __future__ import annotations

import json
import math
from collections.abc import Iterable, Mapping
from types import MappingProxyType

from .packml_models import (
    AlarmResponse,
    ComponentAlarm,
    JsonValue,
    PackMLAlarm,
    PackMLSnapshot,
    plain_json,
)
from .packml_states import PackMLState, TRANSIENT_STATES


PACKML_ALARM_SOURCE = "PackMLMachine"


def validate_timestamp(value: object, name: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
    ):
        raise TypeError(f"{name} must be a finite timestamp")
    if value < 0:
        raise TypeError(f"{name} must be a non-negative timestamp")
    return value


def freeze_json(
    value: object, *, name: str, seen: set[int] | None = None
) -> JsonValue:
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
            return tuple(freeze_json(item, name=name, seen=seen) for item in value)
        if isinstance(value, Mapping) and all(isinstance(key, str) for key in value):
            return MappingProxyType(
                {
                    key: freeze_json(value[key], name=name, seen=seen)
                    for key in sorted(value)
                }
            )
    finally:
        seen.remove(identity)
    raise TypeError(f"{name} must be JSON-like")


def _response(value: object, source: str) -> AlarmResponse | None:
    if value is None:
        return None
    try:
        return AlarmResponse(value)
    except (TypeError, ValueError) as error:
        raise TypeError(f"Invalid alarm response from PackML component: {source}") from error


def normalize_component_alarm(
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
        details=freeze_json(
            details,
            name=f"Invalid alarm details from PackML component: {source}",
        ),
    )


def _alarm_key(alarm: PackMLAlarm) -> str:
    return json.dumps(alarm.to_dict(), sort_keys=True, separators=(",", ":"))


def sort_alarms(alarms: Iterable[PackMLAlarm]) -> tuple[PackMLAlarm, ...]:
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
        normalized_details = freeze_json(details, name="snapshot alarm details")
    except TypeError as error:
        raise TypeError("snapshot contains an invalid normalized alarm") from error
    return PackMLAlarm(source, code, response, normalized_details)


def validate_snapshot(
    snapshot: PackMLSnapshot | Mapping[str, object], now: float
) -> PackMLSnapshot:
    validate_timestamp(now, "snapshot restoration now")
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
    entered_at = validate_timestamp(raw.get("stateEnteredAt"), "snapshot stateEnteredAt")
    if entered_at > now:
        raise TypeError("snapshot stateEnteredAt must not be in the future")
    raw_alarms = raw.get("alarms")
    if not isinstance(raw_alarms, (list, tuple)):
        raise TypeError("snapshot alarms must be an array")
    alarms = sort_alarms(_snapshot_alarm(alarm) for alarm in raw_alarms)
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
    details = plain_json(timeout.details)
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


__all__ = ["PACKML_ALARM_SOURCE", "validate_snapshot"]
