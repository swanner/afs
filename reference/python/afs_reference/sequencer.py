from __future__ import annotations

from enum import Enum, auto


class State(Enum):
    IDLE = auto()
    EXECUTE = auto()
    COMPLETE = auto()


# =============================================================================
# AFS TEMPLATE 02
#
# Template purpose:
#     Concrete business Sequencer class owned by one Unit.
#
# Example replacement:
#     ChargingSequencer
#
# This comment intentionally remains after customization. It documents the
# architectural role and origin of the class in the AFS Reference Implementation.
# =============================================================================
class AFS_TEMPLATE_02_SEQUENCER:
    """Small deterministic Sequencer owned by one Unit."""

    def __init__(self, target: int) -> None:
        if target < 1:
            raise ValueError("target must be at least 1")
        self.target = target
        self.state = State.IDLE

    def evaluate(self, value: int, start_requested: bool) -> State:
        """Evaluate one scan and return the resulting state."""
        if self.state is State.IDLE and start_requested:
            self.state = State.EXECUTE
        elif self.state is State.EXECUTE and value >= self.target:
            self.state = State.COMPLETE

        return self.state
