from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping

from .packml import (
    PackMLCommand,
    PackMLLifecycle,
    PackMLState,
    REQUIRED_STATES,
)
from .unit_runtime import PackMLUnit


@dataclass(frozen=True)
class AggregationStatus:
    participating: tuple[str, ...]
    complete: tuple[str, ...]
    waiting: tuple[str, ...]
    failed: tuple[str, ...]
    timed_out: bool


class FaultAction(str, Enum):
    WAIT = "WAIT"
    ABORT = "ABORT"
    DEGRADED = "DEGRADED"


@dataclass(frozen=True)
class AggregationPolicy:
    participants_by_command: Mapping[PackMLCommand, tuple[str, ...]] | None = None
    timeout_scans: int | None = None
    fault_action: FaultAction = FaultAction.ABORT

    def __post_init__(self) -> None:
        if self.timeout_scans is not None and self.timeout_scans < 1:
            raise ValueError("timeout_scans must be at least 1")

    @property
    def allows_degraded_operation(self) -> bool:
        return self.fault_action is FaultAction.DEGRADED


class CompositeUnit(PackMLUnit):
    """Reference Parent that coordinates all direct Subunits deterministically."""

    def __init__(
        self,
        *,
        name: str,
        mode: str = "AUTOMATIC",
        aggregation_policy: AggregationPolicy | None = None,
    ) -> None:
        transition_states = {
            PackMLState.RESETTING,
            PackMLState.STARTING,
            PackMLState.STOPPING,
            PackMLState.ABORTING,
            PackMLState.CLEARING,
        }
        super().__init__(
            name=name,
            lifecycle=PackMLLifecycle(
                mode=mode,
                supported_states=REQUIRED_STATES | transition_states,
            ),
        )
        self._policy = aggregation_policy or AggregationPolicy()
        self._last_propagated_transition_id = 0
        self._tracked_transition_id = 0
        self._transition_scan_count = 0
        self._aggregation = AggregationStatus((), (), (), (), False)

    @property
    def aggregation_status(self) -> AggregationStatus:
        return self._aggregation

    @property
    def aggregation_policy(self) -> AggregationPolicy:
        return self._policy

    def _participants(self, command: PackMLCommand | None) -> tuple[PackMLUnit, ...]:
        children = tuple(self.subunits)
        if command is None:
            return ()
        mapping = self._policy.participants_by_command
        if not mapping or command not in mapping:
            return children

        names = mapping[command]
        by_name = {child.name: child for child in children}
        unknown = tuple(name for name in names if name not in by_name)
        if unknown:
            raise ValueError(f"unknown Subunit in aggregation policy: {unknown[0]}")
        if len(names) != len(set(names)):
            raise ValueError("aggregation policy contains duplicate Subunits")
        return tuple(by_name[name] for name in names)

    def scan(self) -> None:
        # Phase 1 and 2: accept the Parent command and visibly enter its acting
        # transition before any child receives that command.
        self.lifecycle.begin_scan()
        parent_status = self.lifecycle.status
        participants = self._participants(parent_status.active_command)

        if parent_status.transition_id != self._tracked_transition_id:
            self._tracked_transition_id = parent_status.transition_id
            self._transition_scan_count = 0
        if parent_status.active_command is not None:
            self._transition_scan_count += 1

        # Phase 3: propagate one command per Parent transition.
        if (
            parent_status.active_command is not None
            and parent_status.transition_id != self._last_propagated_transition_id
        ):
            for child in participants:
                child.request(parent_status.active_command)
            self._last_propagated_transition_id = parent_status.transition_id

        # Phase 4: scan direct Subunits once in explicit registration order.
        children = tuple(self.subunits)
        for child in children:
            child.scan()

        # Phase 5: aggregate independently observable child status.
        target = self.lifecycle.status.transition_target
        complete = tuple(
            child.name
            for child in participants
            if target is not None
            and child.lifecycle.state is target
            and child.lifecycle.status.state_complete
        )
        failed = tuple(
            child.name
            for child in participants
            if child.lifecycle.state is PackMLState.ABORTED
        )
        waiting = tuple(
            child.name
            for child in participants
            if child.name not in complete and child.name not in failed
        )
        timed_out = (
            self._policy.timeout_scans is not None
            and self._transition_scan_count >= self._policy.timeout_scans
            and bool(waiting)
        )
        self._aggregation = AggregationStatus(
            participating=tuple(child.name for child in participants),
            complete=complete,
            waiting=waiting,
            failed=failed,
            timed_out=timed_out,
        )

        should_abort = (
            failed and self._policy.fault_action is FaultAction.ABORT
        ) or timed_out
        if should_abort and self.lifecycle.state not in {
            PackMLState.ABORTING,
            PackMLState.ABORTED,
        }:
            reason = "SUBUNIT_TIMEOUT" if timed_out else "SUBUNIT_ABORTED"
            self.lifecycle.request(PackMLCommand.ABORT, reason=reason)

        # Phase 6: complete only when every required child reached the target.
        completed_count = len(complete)
        if self._policy.allows_degraded_operation:
            completed_count += len(failed)
        all_complete = not participants or completed_count == len(participants)
        self.lifecycle.complete_scan(state_complete=all_complete)
