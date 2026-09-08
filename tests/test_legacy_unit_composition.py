from __future__ import annotations

import unittest

from reference.python.afs_reference.legacy.application import Application
from reference.python.afs_reference.legacy.composition import (
    AggregationPolicy,
    CompositeUnit,
    FaultAction,
)
from reference.python.afs_reference.legacy.packml_lifecycle import (
    PackMLCommand,
    PackMLLifecycle,
    PackMLState,
    REQUIRED_STATES,
)
from reference.python.afs_reference.legacy.unit_runtime import PackMLUnit


TRANSITION_STATES = {
    PackMLState.RESETTING,
    PackMLState.STARTING,
    PackMLState.STOPPING,
    PackMLState.ABORTING,
    PackMLState.CLEARING,
}


class ControlledUnit(PackMLUnit):
    def __init__(self, name: str, calls: list[str] | None = None) -> None:
        super().__init__(
            name=name,
            lifecycle=PackMLLifecycle(
                mode="AUTOMATIC",
                supported_states=REQUIRED_STATES | TRANSITION_STATES,
            ),
        )
        self._calls = calls
        self.transition_ready = True

    def scan(self) -> None:
        if self._calls is not None:
            self._calls.append(self.name)
        self.lifecycle.begin_scan()
        self.lifecycle.complete_scan(state_complete=self.transition_ready)


class LegacyUnitCompositionTests(unittest.TestCase):
    def test_application_accepts_packml_units_only(self) -> None:
        app = Application()

        with self.assertRaisesRegex(TypeError, "PackMLUnit"):
            app.add_unit(object())  # type: ignore[arg-type]

    def test_duplicate_top_level_registration_is_rejected(self) -> None:
        app = Application()
        unit = ControlledUnit("unit")
        app.add_unit(unit)

        with self.assertRaisesRegex(ValueError, "already registered|owner"):
            app.add_unit(unit)

    def test_subunit_cannot_have_multiple_owners(self) -> None:
        first = CompositeUnit(name="first")
        second = CompositeUnit(name="second")
        child = ControlledUnit("child")
        first.add_subunit(child)

        with self.assertRaisesRegex(ValueError, "already has an owner"):
            second.add_subunit(child)

    def test_ownership_cycle_is_rejected(self) -> None:
        parent = CompositeUnit(name="parent")
        child = CompositeUnit(name="child")
        parent.add_subunit(child)

        with self.assertRaisesRegex(ValueError, "acyclic"):
            child.add_subunit(parent)

    def test_subunit_cannot_also_be_top_level(self) -> None:
        app = Application()
        parent = CompositeUnit(name="parent")
        child = ControlledUnit("child")
        parent.add_subunit(child)

        with self.assertRaisesRegex(ValueError, "already has an owner"):
            app.add_unit(child)

    def test_parent_scans_subunits_in_registration_order(self) -> None:
        calls: list[str] = []
        parent = CompositeUnit(name="parent")
        parent.add_subunit(ControlledUnit("first", calls))
        parent.add_subunit(ControlledUnit("second", calls))

        parent.scan()

        self.assertEqual(calls, ["first", "second"])

    def test_parent_declares_aggregation_policy(self) -> None:
        policy = AggregationPolicy(
            participants_by_command={PackMLCommand.START: ("first",)},
            timeout_scans=3,
            fault_action=FaultAction.WAIT,
        )
        parent = CompositeUnit(name="parent", aggregation_policy=policy)

        self.assertIs(parent.aggregation_policy, policy)
        self.assertFalse(policy.allows_degraded_operation)

    def test_parent_waits_for_every_required_subunit(self) -> None:
        parent = CompositeUnit(name="zone")
        ready = ControlledUnit("ready-room")
        delayed = ControlledUnit("delayed-room")
        delayed.transition_ready = False
        parent.add_subunit(ready)
        parent.add_subunit(delayed)
        parent.request(PackMLCommand.RESET)

        parent.scan()
        self.assertEqual(parent.lifecycle.state, PackMLState.RESETTING)
        self.assertEqual(ready.lifecycle.state, PackMLState.RESETTING)
        self.assertEqual(delayed.lifecycle.state, PackMLState.RESETTING)

        parent.scan()
        self.assertEqual(ready.lifecycle.state, PackMLState.IDLE)
        self.assertEqual(delayed.lifecycle.state, PackMLState.RESETTING)
        self.assertEqual(parent.lifecycle.state, PackMLState.RESETTING)
        self.assertEqual(parent.aggregation_status.waiting, ("delayed-room",))

        delayed.transition_ready = True
        parent.scan()
        self.assertEqual(delayed.lifecycle.state, PackMLState.IDLE)
        self.assertEqual(parent.lifecycle.state, PackMLState.IDLE)
        self.assertEqual(
            parent.aggregation_status.complete,
            ("ready-room", "delayed-room"),
        )

        parent.scan()
        self.assertEqual(parent.aggregation_status.participating, ())
        self.assertEqual(parent.aggregation_status.waiting, ())

    def test_parent_and_subunit_status_remain_independent(self) -> None:
        parent = CompositeUnit(name="zone")
        child = ControlledUnit("room")
        child.transition_ready = False
        parent.add_subunit(child)
        parent.request(PackMLCommand.RESET)

        parent.scan()

        self.assertEqual(parent.lifecycle.state, PackMLState.RESETTING)
        self.assertEqual(child.lifecycle.state, PackMLState.RESETTING)
        self.assertFalse(parent.lifecycle.status.state_complete)
        self.assertFalse(child.lifecycle.status.state_complete)
        self.assertEqual(parent.aggregation_status.participating, ("room",))

    def test_subunit_fault_remains_attributable_and_aborts_parent(self) -> None:
        parent = CompositeUnit(name="zone")
        child = ControlledUnit("faulted-room")
        child.lifecycle.request(PackMLCommand.ABORT)
        child.scan()
        child.scan()
        self.assertEqual(child.lifecycle.state, PackMLState.ABORTED)
        parent.add_subunit(child)
        parent.request(PackMLCommand.RESET)

        parent.scan()

        self.assertEqual(parent.aggregation_status.failed, ("faulted-room",))
        self.assertEqual(
            parent.lifecycle.status.pending_request,
            PackMLCommand.ABORT,
        )
        self.assertEqual(child.lifecycle.state, PackMLState.ABORTED)

        parent.scan()
        self.assertEqual(parent.lifecycle.state, PackMLState.ABORTING)

    def test_declared_degraded_policy_allows_parent_completion(self) -> None:
        policy = AggregationPolicy(fault_action=FaultAction.DEGRADED)
        parent = CompositeUnit(name="zone", aggregation_policy=policy)
        ready = ControlledUnit("ready-room")
        faulted = ControlledUnit("faulted-room")
        faulted.lifecycle.request(PackMLCommand.ABORT)
        faulted.scan()
        faulted.scan()
        parent.add_subunit(ready)
        parent.add_subunit(faulted)
        parent.request(PackMLCommand.RESET)

        parent.scan()
        parent.scan()

        self.assertEqual(parent.lifecycle.state, PackMLState.IDLE)
        self.assertEqual(parent.aggregation_status.complete, ("ready-room",))
        self.assertEqual(parent.aggregation_status.failed, ("faulted-room",))
        self.assertTrue(policy.allows_degraded_operation)

    def test_declared_timeout_aborts_waiting_parent(self) -> None:
        policy = AggregationPolicy(timeout_scans=2)
        parent = CompositeUnit(name="zone", aggregation_policy=policy)
        child = ControlledUnit("slow-room")
        child.transition_ready = False
        parent.add_subunit(child)
        parent.request(PackMLCommand.RESET)

        parent.scan()
        parent.scan()

        self.assertTrue(parent.aggregation_status.timed_out)
        self.assertEqual(
            parent.lifecycle.status.pending_request,
            PackMLCommand.ABORT,
        )

        parent.scan()
        self.assertEqual(parent.lifecycle.state, PackMLState.ABORTING)

    def test_peer_units_remain_flat(self) -> None:
        app = Application()
        solar = ControlledUnit("solar")
        charging = ControlledUnit("charging")

        app.add_unit(solar)
        app.add_unit(charging)

        self.assertIs(solar.owner, app)
        self.assertIs(charging.owner, app)
        self.assertEqual(tuple(solar.subunits), ())
        self.assertEqual(tuple(charging.subunits), ())


if __name__ == "__main__":
    unittest.main()
