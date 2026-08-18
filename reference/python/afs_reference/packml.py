from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


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


class PackMLCommand(str, Enum):
    RESET = "RESET"
    START = "START"
    STOP = "STOP"
    ABORT = "ABORT"
    CLEAR = "CLEAR"
    HOLD = "HOLD"
    UNHOLD = "UNHOLD"
    SUSPEND = "SUSPEND"
    UNSUSPEND = "UNSUSPEND"
    COMPLETE = "COMPLETE"


REQUIRED_STATES = frozenset(
    {
        PackMLState.STOPPED,
        PackMLState.IDLE,
        PackMLState.EXECUTE,
        PackMLState.ABORTED,
    }
)


@dataclass(frozen=True)
class LifecycleCondition:
    code: str
    message: str
    fault: bool = False


@dataclass(frozen=True)
class CommandResult:
    accepted: bool
    command: PackMLCommand
    state: PackMLState
    reason: str | None = None


@dataclass(frozen=True)
class LifecycleStatus:
    state: PackMLState
    mode: str
    supported_modes: frozenset[str]
    state_complete: bool
    supported_states: frozenset[PackMLState]
    supported_commands: frozenset[PackMLCommand]
    pending_request: PackMLCommand | None
    active_command: PackMLCommand | None
    transition_target: PackMLState | None
    transition_id: int
    conditions: tuple[LifecycleCondition, ...]
    reason: str | None


@dataclass(frozen=True)
class _Transition:
    source: frozenset[PackMLState] | None
    acting: PackMLState | None
    target: PackMLState


_FIXED_TRANSITIONS = {
    PackMLCommand.RESET: _Transition(
        frozenset({PackMLState.STOPPED}),
        PackMLState.RESETTING,
        PackMLState.IDLE,
    ),
    PackMLCommand.START: _Transition(
        frozenset({PackMLState.IDLE}),
        PackMLState.STARTING,
        PackMLState.EXECUTE,
    ),
    PackMLCommand.CLEAR: _Transition(
        frozenset({PackMLState.ABORTED}),
        PackMLState.CLEARING,
        PackMLState.STOPPED,
    ),
    PackMLCommand.HOLD: _Transition(
        frozenset({PackMLState.EXECUTE}),
        PackMLState.HOLDING,
        PackMLState.HELD,
    ),
    PackMLCommand.UNHOLD: _Transition(
        frozenset({PackMLState.HELD}),
        PackMLState.UNHOLDING,
        PackMLState.EXECUTE,
    ),
    PackMLCommand.SUSPEND: _Transition(
        frozenset({PackMLState.EXECUTE}),
        PackMLState.SUSPENDING,
        PackMLState.SUSPENDED,
    ),
    PackMLCommand.UNSUSPEND: _Transition(
        frozenset({PackMLState.SUSPENDED}),
        PackMLState.UNSUSPENDING,
        PackMLState.EXECUTE,
    ),
    PackMLCommand.COMPLETE: _Transition(
        frozenset({PackMLState.EXECUTE}),
        PackMLState.COMPLETING,
        PackMLState.COMPLETE,
    ),
}


class PackMLLifecycle:
    """Implementation-neutral AFS PackML Unit Profile 0.1 runtime."""

    def __init__(
        self,
        *,
        mode: str,
        supported_states: Iterable[PackMLState],
        restored_state: PackMLState | str | None = None,
    ) -> None:
        states = frozenset(supported_states)
        missing = REQUIRED_STATES - states
        if missing:
            names = ", ".join(sorted(state.value for state in missing))
            raise ValueError(f"missing required PackML states: {names}")
        if not mode.strip():
            raise ValueError("mode must not be empty")

        self._mode = mode
        self._supported_states = states
        self._supported_commands = self._derive_supported_commands(states)
        self._pending_request: PackMLCommand | None = None
        self._active_command: PackMLCommand | None = None
        self._transition_target: PackMLState | None = None
        self._transition_id = 0
        self._state_complete = True
        self._entered_transition_this_scan = False
        self._conditions: tuple[LifecycleCondition, ...] = ()
        self._reason: str | None = None

        self._state = PackMLState.STOPPED
        if restored_state is not None:
            self._restore(restored_state)

    @staticmethod
    def _derive_supported_commands(
        states: frozenset[PackMLState],
    ) -> frozenset[PackMLCommand]:
        commands = {
            PackMLCommand.RESET,
            PackMLCommand.START,
            PackMLCommand.STOP,
            PackMLCommand.ABORT,
            PackMLCommand.CLEAR,
        }
        optional = {
            PackMLCommand.HOLD: {PackMLState.HELD},
            PackMLCommand.UNHOLD: {PackMLState.HELD},
            PackMLCommand.SUSPEND: {PackMLState.SUSPENDED},
            PackMLCommand.UNSUSPEND: {PackMLState.SUSPENDED},
            PackMLCommand.COMPLETE: {PackMLState.COMPLETE},
        }
        for command, required in optional.items():
            if required <= states:
                commands.add(command)
        return frozenset(commands)

    def _restore(self, restored_state: PackMLState | str) -> None:
        try:
            state = PackMLState(restored_state)
        except ValueError:
            self._enter_restore_fault(f"unknown restored state: {restored_state}")
            return

        if state not in self._supported_states:
            self._enter_restore_fault(f"unsupported restored state: {state.value}")
            return

        self._state = state

    def _enter_restore_fault(self, message: str) -> None:
        self._state = PackMLState.ABORTED
        self._conditions = (
            LifecycleCondition("RESTORE_STATE_INVALID", message, fault=True),
        )
        self._reason = "RESTORE_STATE_INVALID"

    @property
    def state(self) -> PackMLState:
        return self._state

    @property
    def status(self) -> LifecycleStatus:
        return LifecycleStatus(
            state=self._state,
            mode=self._mode,
            supported_modes=frozenset({self._mode}),
            state_complete=self._state_complete,
            supported_states=self._supported_states,
            supported_commands=self._supported_commands,
            pending_request=self._pending_request,
            active_command=self._active_command,
            transition_target=self._transition_target,
            transition_id=self._transition_id,
            conditions=self._conditions,
            reason=self._reason,
        )

    def set_conditions(self, conditions: Iterable[LifecycleCondition]) -> None:
        self._conditions = tuple(conditions)

    def request(
        self,
        command: PackMLCommand,
        *,
        reason: str | None = None,
    ) -> CommandResult:
        if command not in self._supported_commands:
            return CommandResult(False, command, self._state, "unsupported command")

        if self._pending_request is command:
            self._reason = reason
            return CommandResult(True, command, self._state, "request already pending")

        if self._pending_request is not None and command is not PackMLCommand.ABORT:
            return CommandResult(False, command, self._state, "another request is pending")

        if self._active_command is not None and command is not PackMLCommand.ABORT:
            return CommandResult(False, command, self._state, "transition in progress")

        self._pending_request = command
        self._reason = reason
        return CommandResult(True, command, self._state)

    def begin_scan(
        self,
        *,
        request_guard: bool = True,
        blocked_reason: str | None = None,
    ) -> CommandResult | None:
        self._entered_transition_this_scan = False
        command = self._pending_request
        if command is None:
            return None

        if not request_guard and command is not PackMLCommand.ABORT:
            self._reason = blocked_reason
            return None

        result = self._issue(command)
        if result.accepted:
            self._pending_request = None
            self._reason = None
        else:
            self._pending_request = None
            self._reason = result.reason
        return result

    def complete_scan(self, *, state_complete: bool) -> None:
        if self._active_command is None:
            return
        if self._entered_transition_this_scan:
            return
        if not state_complete:
            return

        if self._transition_target is None:
            raise RuntimeError("active transition has no target")
        self._state = self._transition_target
        self._state_complete = True
        self._active_command = None
        self._transition_target = None

    def _issue(self, command: PackMLCommand) -> CommandResult:
        transition = self._transition_for(command)
        if transition is None:
            return CommandResult(False, command, self._state, "invalid source state")

        if command is PackMLCommand.ABORT:
            self._active_command = None
            self._transition_target = None

        acting = transition.acting
        if acting is not None and acting in self._supported_states:
            self._state = acting
            self._active_command = command
            self._transition_target = transition.target
            self._transition_id += 1
            self._state_complete = False
            self._entered_transition_this_scan = True
        else:
            self._state = transition.target
            self._active_command = None
            self._transition_target = None
            self._transition_id += 1
            self._state_complete = True

        return CommandResult(True, command, self._state)

    def _transition_for(self, command: PackMLCommand) -> _Transition | None:
        if command is PackMLCommand.ABORT:
            if self._state in {PackMLState.ABORTING, PackMLState.ABORTED}:
                return None
            return _Transition(None, PackMLState.ABORTING, PackMLState.ABORTED)

        if command is PackMLCommand.STOP:
            invalid = {
                PackMLState.STOPPED,
                PackMLState.STOPPING,
                PackMLState.ABORTING,
                PackMLState.ABORTED,
                PackMLState.CLEARING,
            }
            if self._state in invalid:
                return None
            return _Transition(None, PackMLState.STOPPING, PackMLState.STOPPED)

        transition = _FIXED_TRANSITIONS.get(command)
        if transition is None or transition.source is None:
            return None
        if self._state not in transition.source:
            return None
        if transition.target not in self._supported_states:
            return None
        return transition
