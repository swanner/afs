from __future__ import annotations

import unittest
from enum import Enum

from reference.python.afs_reference.composition import CompositeUnit
from reference.python.afs_reference.packml import (
    PackMLCommand,
    PackMLLifecycle,
    PackMLState,
    REQUIRED_STATES,
)
from reference.python.afs_reference.unit_runtime import PackMLUnit


BASE_TRANSITIONS = {
    PackMLState.RESETTING,
    PackMLState.STARTING,
    PackMLState.STOPPING,
    PackMLState.ABORTING,
    PackMLState.CLEARING,
}


class SolarAvailability(str, Enum):
    BELOW = "BELOW"
    WAIT_ABOVE = "WAIT_ABOVE"
    ABOVE = "ABOVE"
    WAIT_BELOW = "WAIT_BELOW"


class ScenarioLeaf(PackMLUnit):
    def __init__(
        self,
        name: str,
        *,
        observed_parent: CompositeUnit | None = None,
        observations: list[PackMLState] | None = None,
    ) -> None:
        super().__init__(
            name=name,
            lifecycle=PackMLLifecycle(
                mode="AUTOMATIC",
                supported_states=REQUIRED_STATES | BASE_TRANSITIONS,
            ),
        )
        self._observed_parent = observed_parent
        self._observations = observations

    def scan(self) -> None:
        if self._observed_parent is not None and self._observations is not None:
            self._observations.append(self._observed_parent.lifecycle.state)
        self.lifecycle.begin_scan()
        self.lifecycle.complete_scan(state_complete=True)


def complete(lifecycle: PackMLLifecycle) -> None:
    lifecycle.complete_scan(state_complete=True)
    lifecycle.begin_scan()
    lifecycle.complete_scan(state_complete=True)


def start(lifecycle: PackMLLifecycle) -> None:
    lifecycle.request(PackMLCommand.RESET)
    lifecycle.begin_scan()
    complete(lifecycle)
    lifecycle.request(PackMLCommand.START)
    lifecycle.begin_scan()
    complete(lifecycle)


class ReferenceScenarioTests(unittest.TestCase):
    def test_solar_domain_state_does_not_replace_packml_state(self) -> None:
        lifecycle = PackMLLifecycle(
            mode="AUTOMATIC",
            supported_states=REQUIRED_STATES | BASE_TRANSITIONS,
        )
        start(lifecycle)
        domain_states = (
            SolarAvailability.BELOW,
            SolarAvailability.WAIT_ABOVE,
            SolarAvailability.ABOVE,
            SolarAvailability.WAIT_BELOW,
            SolarAvailability.BELOW,
        )

        for domain_state in domain_states:
            self.assertIsInstance(domain_state, SolarAvailability)
            self.assertEqual(lifecycle.state, PackMLState.EXECUTE)

    def test_charging_waits_suspends_resumes_and_completes(self) -> None:
        lifecycle = PackMLLifecycle(
            mode="AUTOMATIC",
            supported_states=REQUIRED_STATES
            | BASE_TRANSITIONS
            | {
                PackMLState.SUSPENDING,
                PackMLState.SUSPENDED,
                PackMLState.UNSUSPENDING,
                PackMLState.COMPLETING,
                PackMLState.COMPLETE,
            },
        )
        lifecycle.request(PackMLCommand.RESET)
        lifecycle.begin_scan()
        complete(lifecycle)
        lifecycle.request(PackMLCommand.START)

        lifecycle.begin_scan(
            request_guard=False,
            blocked_reason="SOLAR_UNAVAILABLE",
        )
        self.assertEqual(lifecycle.state, PackMLState.IDLE)
        self.assertEqual(lifecycle.status.reason, "SOLAR_UNAVAILABLE")

        lifecycle.begin_scan(request_guard=True)
        complete(lifecycle)
        self.assertEqual(lifecycle.state, PackMLState.EXECUTE)

        lifecycle.request(PackMLCommand.SUSPEND, reason="SOLAR_UNAVAILABLE")
        lifecycle.begin_scan()
        complete(lifecycle)
        self.assertEqual(lifecycle.state, PackMLState.SUSPENDED)

        lifecycle.request(PackMLCommand.UNSUSPEND)
        lifecycle.begin_scan()
        complete(lifecycle)
        self.assertEqual(lifecycle.state, PackMLState.EXECUTE)

        lifecycle.request(PackMLCommand.COMPLETE, reason="TARGET_SOC_REACHED")
        lifecycle.begin_scan()
        complete(lifecycle)
        self.assertEqual(lifecycle.state, PackMLState.COMPLETE)

    def test_alarm_parent_enters_acting_state_before_room_subunits(self) -> None:
        observed_parent_states: list[PackMLState] = []
        zone = CompositeUnit(name="zone")
        room = ScenarioLeaf(
            "room",
            observed_parent=zone,
            observations=observed_parent_states,
        )
        zone.add_subunit(room)
        zone.request(PackMLCommand.RESET)

        zone.scan()
        zone.scan()
        self.assertEqual(zone.lifecycle.state, PackMLState.IDLE)
        self.assertEqual(room.lifecycle.state, PackMLState.IDLE)

        zone.request(PackMLCommand.START)
        zone.scan()

        self.assertEqual(observed_parent_states[-1], PackMLState.STARTING)
        self.assertEqual(zone.lifecycle.state, PackMLState.STARTING)
        self.assertEqual(room.lifecycle.state, PackMLState.STARTING)

        zone.scan()
        self.assertEqual(zone.lifecycle.state, PackMLState.EXECUTE)
        self.assertEqual(room.lifecycle.state, PackMLState.EXECUTE)


if __name__ == "__main__":
    unittest.main()

