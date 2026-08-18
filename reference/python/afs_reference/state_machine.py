from __future__ import annotations

from .packml import (
    PackMLCommand,
    PackMLLifecycle,
    PackMLState,
    REQUIRED_STATES,
)


State = PackMLState


# =============================================================================
# AFS TEMPLATE 02
#
# Template purpose:
#     Concrete business State Machine class owned by one Unit.
#
# Example replacement:
#     ChargingStateMachine
#
# This comment intentionally remains after customization. It documents the
# architectural role and origin of the class in the AFS Reference Implementation.
# =============================================================================
class AFS_TEMPLATE_02_STATE_MACHINE:
    """Small deterministic State Machine owned by one Unit."""

    def __init__(self, target: int) -> None:
        if target < 1:
            raise ValueError("target must be at least 1")
        self.target = target
        self.lifecycle = PackMLLifecycle(
            mode="AUTOMATIC",
            supported_states=REQUIRED_STATES
            | {
                State.RESETTING,
                State.STARTING,
                State.STOPPING,
                State.ABORTING,
                State.CLEARING,
                State.COMPLETING,
                State.COMPLETE,
            },
        )

    @property
    def state(self) -> State:
        return self.lifecycle.state

    def evaluate(self, value: int, start_requested: bool) -> State:
        """Evaluate one scan and return the resulting state."""
        if self.state is State.STOPPED and self.lifecycle.status.pending_request is None:
            self.lifecycle.request(PackMLCommand.RESET)
        elif (
            self.state is State.IDLE
            and start_requested
            and self.lifecycle.status.pending_request is None
        ):
            self.lifecycle.request(PackMLCommand.START)
        elif (
            self.state is State.EXECUTE
            and value >= self.target
            and self.lifecycle.status.pending_request is None
        ):
            self.lifecycle.request(PackMLCommand.COMPLETE)

        self.lifecycle.begin_scan()
        self.lifecycle.complete_scan(state_complete=True)
        return self.state
