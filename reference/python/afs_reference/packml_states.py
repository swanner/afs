"""PackML states and the explicit legal transition graph."""

from __future__ import annotations

from enum import Enum
from types import MappingProxyType


class PackMLState(str, Enum):
    CLEARING = "CLEARING"
    STOPPED = "STOPPED"
    STARTING = "STARTING"
    IDLE = "IDLE"
    SUSPENDED = "SUSPENDED"
    EXECUTE = "EXECUTE"
    STOPPING = "STOPPING"
    ABORTING = "ABORTING"
    ABORTED = "ABORTED"
    HOLDING = "HOLDING"
    HELD = "HELD"
    UNHOLDING = "UNHOLDING"
    SUSPENDING = "SUSPENDING"
    UNSUSPENDING = "UNSUSPENDING"
    RESETTING = "RESETTING"
    COMPLETING = "COMPLETING"
    COMPLETE = "COMPLETE"
    SYSTEM_FAILURE = "SYSTEM_FAILURE"


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


# This graph is deliberately literal. The scan orchestrator remains the authority
# for priority and conditions; this table only guards every state change.
BASE_TRANSITIONS = MappingProxyType(
    {
        PackMLState.ABORTED: (
            PackMLState.CLEARING,
            PackMLState.SYSTEM_FAILURE,
        ),
        PackMLState.ABORTING: (
            PackMLState.ABORTED,
            PackMLState.SYSTEM_FAILURE,
        ),
        PackMLState.CLEARING: (
            PackMLState.STOPPED,
            PackMLState.ABORTING,
            PackMLState.SYSTEM_FAILURE,
        ),
        PackMLState.STOPPED: (
            PackMLState.RESETTING,
            PackMLState.ABORTING,
            PackMLState.SYSTEM_FAILURE,
        ),
        PackMLState.STOPPING: (
            PackMLState.STOPPED,
            PackMLState.ABORTING,
            PackMLState.SYSTEM_FAILURE,
        ),
        PackMLState.RESETTING: (
            PackMLState.IDLE,
            PackMLState.STOPPING,
            PackMLState.ABORTING,
            PackMLState.SYSTEM_FAILURE,
        ),
        PackMLState.IDLE: (
            PackMLState.STARTING,
            PackMLState.STOPPING,
            PackMLState.ABORTING,
            PackMLState.SYSTEM_FAILURE,
        ),
        PackMLState.STARTING: (
            PackMLState.EXECUTE,
            PackMLState.STOPPING,
            PackMLState.ABORTING,
            PackMLState.SYSTEM_FAILURE,
        ),
        PackMLState.EXECUTE: (
            PackMLState.COMPLETING,
            PackMLState.HOLDING,
            PackMLState.SUSPENDING,
            PackMLState.STOPPING,
            PackMLState.ABORTING,
            PackMLState.SYSTEM_FAILURE,
        ),
        PackMLState.COMPLETING: (
            PackMLState.COMPLETE,
            PackMLState.ABORTING,
            PackMLState.SYSTEM_FAILURE,
        ),
        PackMLState.COMPLETE: (
            PackMLState.RESETTING,
            PackMLState.STOPPING,
            PackMLState.ABORTING,
            PackMLState.SYSTEM_FAILURE,
        ),
        PackMLState.HOLDING: (
            PackMLState.HELD,
            PackMLState.STOPPING,
            PackMLState.ABORTING,
            PackMLState.SYSTEM_FAILURE,
        ),
        PackMLState.HELD: (
            PackMLState.UNHOLDING,
            PackMLState.STOPPING,
            PackMLState.ABORTING,
            PackMLState.SYSTEM_FAILURE,
        ),
        PackMLState.UNHOLDING: (
            PackMLState.EXECUTE,
            PackMLState.STOPPING,
            PackMLState.ABORTING,
            PackMLState.SYSTEM_FAILURE,
        ),
        PackMLState.SUSPENDING: (
            PackMLState.SUSPENDED,
            PackMLState.STOPPING,
            PackMLState.ABORTING,
            PackMLState.SYSTEM_FAILURE,
        ),
        PackMLState.SUSPENDED: (
            PackMLState.UNSUSPENDING,
            PackMLState.STOPPING,
            PackMLState.ABORTING,
            PackMLState.SYSTEM_FAILURE,
        ),
        PackMLState.UNSUSPENDING: (
            PackMLState.EXECUTE,
            PackMLState.STOPPING,
            PackMLState.ABORTING,
            PackMLState.SYSTEM_FAILURE,
        ),
        PackMLState.SYSTEM_FAILURE: (PackMLState.ABORTING,),
    }
)


def legal_transition(source: PackMLState | str, target: PackMLState | str) -> bool:
    try:
        return PackMLState(target) in BASE_TRANSITIONS.get(PackMLState(source), ())
    except (TypeError, ValueError):
        return False


__all__ = [
    "BASE_TRANSITIONS",
    "PACKML_STATES",
    "PackMLState",
    "TERMINAL_STATES",
    "TRANSIENT_STATES",
    "legal_transition",
]
