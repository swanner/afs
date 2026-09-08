from __future__ import annotations

import unittest

from reference.python.afs_reference.legacy.packml_lifecycle import (
    LifecycleCondition,
    PackMLCommand,
    PackMLLifecycle,
    PackMLState,
    REQUIRED_STATES,
)


TRANSITION_STATES = {
    PackMLState.RESETTING,
    PackMLState.STARTING,
    PackMLState.STOPPING,
    PackMLState.ABORTING,
    PackMLState.CLEARING,
}


class LegacyPackMLConformanceTests(unittest.TestCase):
    def lifecycle(self, *extra: PackMLState) -> PackMLLifecycle:
        return PackMLLifecycle(
            mode="AUTOMATIC",
            supported_states=REQUIRED_STATES | TRANSITION_STATES | set(extra),
        )

    def finish_transition(self, lifecycle: PackMLLifecycle) -> None:
        lifecycle.complete_scan(state_complete=True)
        lifecycle.begin_scan()
        lifecycle.complete_scan(state_complete=True)

    def to_idle(self, lifecycle: PackMLLifecycle) -> None:
        lifecycle.request(PackMLCommand.RESET)
        lifecycle.begin_scan()
        self.assertEqual(lifecycle.state, PackMLState.RESETTING)
        self.finish_transition(lifecycle)
        self.assertEqual(lifecycle.state, PackMLState.IDLE)

    def to_execute(self, lifecycle: PackMLLifecycle) -> None:
        self.to_idle(lifecycle)
        lifecycle.request(PackMLCommand.START)
        lifecycle.begin_scan()
        self.assertEqual(lifecycle.state, PackMLState.STARTING)
        self.finish_transition(lifecycle)
        self.assertEqual(lifecycle.state, PackMLState.EXECUTE)

    def test_new_lifecycle_initializes_stopped(self) -> None:
        lifecycle = self.lifecycle()

        self.assertEqual(lifecycle.state, PackMLState.STOPPED)
        self.assertTrue(lifecycle.status.state_complete)

    def test_required_states_cannot_be_omitted(self) -> None:
        with self.assertRaisesRegex(ValueError, "missing required PackML states"):
            PackMLLifecycle(
                mode="AUTOMATIC",
                supported_states={PackMLState.STOPPED},
            )

    def test_system_failure_requires_declarative_machine(self) -> None:
        with self.assertRaisesRegex(ValueError, "declarative PackMLMachine"):
            PackMLLifecycle(
                mode="AUTOMATIC",
                supported_states=REQUIRED_STATES | {PackMLState.SYSTEM_FAILURE},
            )

    def test_optional_acting_state_requires_its_wait_state(self) -> None:
        with self.assertRaisesRegex(ValueError, "SUSPENDING requires SUSPENDED"):
            self.lifecycle(PackMLState.SUSPENDING)

    def test_state_is_read_only(self) -> None:
        lifecycle = self.lifecycle()

        with self.assertRaises(AttributeError):
            lifecycle.state = PackMLState.EXECUTE  # type: ignore[misc]

    def test_reset_and_start_use_observable_transition_states(self) -> None:
        lifecycle = self.lifecycle()

        self.to_execute(lifecycle)

        self.assertEqual(lifecycle.status.transition_id, 2)
        self.assertTrue(lifecycle.status.state_complete)

    def test_pending_request_waits_for_guard(self) -> None:
        lifecycle = self.lifecycle()
        self.to_idle(lifecycle)
        lifecycle.request(PackMLCommand.START)

        lifecycle.begin_scan(
            request_guard=False,
            blocked_reason="SOLAR_UNAVAILABLE",
        )

        self.assertEqual(lifecycle.state, PackMLState.IDLE)
        self.assertEqual(lifecycle.status.pending_request, PackMLCommand.START)
        self.assertEqual(lifecycle.status.reason, "SOLAR_UNAVAILABLE")

        lifecycle.begin_scan(request_guard=True)
        self.assertEqual(lifecycle.state, PackMLState.STARTING)
        self.assertIsNone(lifecycle.status.pending_request)

    def test_invalid_command_is_rejected_without_state_change(self) -> None:
        lifecycle = self.lifecycle()
        lifecycle.request(PackMLCommand.START)

        result = lifecycle.begin_scan()

        self.assertIsNotNone(result)
        self.assertFalse(result.accepted)  # type: ignore[union-attr]
        self.assertEqual(result.reason, "invalid source state")  # type: ignore[union-attr]
        self.assertEqual(lifecycle.state, PackMLState.STOPPED)

    def test_abort_preempts_an_active_transition(self) -> None:
        lifecycle = self.lifecycle()
        self.to_idle(lifecycle)
        lifecycle.request(PackMLCommand.START)
        lifecycle.begin_scan()
        self.assertEqual(lifecycle.state, PackMLState.STARTING)

        lifecycle.request(PackMLCommand.ABORT, reason="DEVICE_FAULT")
        lifecycle.begin_scan()

        self.assertEqual(lifecycle.state, PackMLState.ABORTING)
        self.finish_transition(lifecycle)
        self.assertEqual(lifecycle.state, PackMLState.ABORTED)

    def test_clear_recovers_aborted_to_stopped(self) -> None:
        lifecycle = self.lifecycle()
        lifecycle.request(PackMLCommand.ABORT)
        lifecycle.begin_scan()
        self.finish_transition(lifecycle)
        self.assertEqual(lifecycle.state, PackMLState.ABORTED)

        lifecycle.request(PackMLCommand.CLEAR)
        lifecycle.begin_scan()
        self.assertEqual(lifecycle.state, PackMLState.CLEARING)
        self.finish_transition(lifecycle)
        self.assertEqual(lifecycle.state, PackMLState.STOPPED)

    def test_suspend_branch_uses_packml_semantics(self) -> None:
        lifecycle = self.lifecycle(
            PackMLState.SUSPENDING,
            PackMLState.SUSPENDED,
            PackMLState.UNSUSPENDING,
        )
        self.to_execute(lifecycle)

        lifecycle.request(PackMLCommand.SUSPEND, reason="SOLAR_UNAVAILABLE")
        lifecycle.begin_scan()
        self.assertEqual(lifecycle.state, PackMLState.SUSPENDING)
        self.finish_transition(lifecycle)
        self.assertEqual(lifecycle.state, PackMLState.SUSPENDED)

        lifecycle.request(PackMLCommand.UNSUSPEND)
        lifecycle.begin_scan()
        self.assertEqual(lifecycle.state, PackMLState.UNSUSPENDING)
        self.finish_transition(lifecycle)
        self.assertEqual(lifecycle.state, PackMLState.EXECUTE)

    def test_complete_branch_uses_packml_semantics(self) -> None:
        lifecycle = self.lifecycle(PackMLState.COMPLETING, PackMLState.COMPLETE)
        self.to_execute(lifecycle)

        lifecycle.request(PackMLCommand.COMPLETE)
        lifecycle.begin_scan()
        self.assertEqual(lifecycle.state, PackMLState.COMPLETING)
        self.finish_transition(lifecycle)
        self.assertEqual(lifecycle.state, PackMLState.COMPLETE)

    def test_stop_uses_controlled_transition(self) -> None:
        lifecycle = self.lifecycle()
        self.to_execute(lifecycle)

        lifecycle.request(PackMLCommand.STOP)
        lifecycle.begin_scan()
        self.assertEqual(lifecycle.state, PackMLState.STOPPING)
        self.finish_transition(lifecycle)
        self.assertEqual(lifecycle.state, PackMLState.STOPPED)

    def test_hold_branch_uses_packml_semantics(self) -> None:
        lifecycle = self.lifecycle(
            PackMLState.HOLDING,
            PackMLState.HELD,
            PackMLState.UNHOLDING,
        )
        self.to_execute(lifecycle)

        lifecycle.request(PackMLCommand.HOLD)
        lifecycle.begin_scan()
        self.assertEqual(lifecycle.state, PackMLState.HOLDING)
        self.finish_transition(lifecycle)
        self.assertEqual(lifecycle.state, PackMLState.HELD)

        lifecycle.request(PackMLCommand.UNHOLD)
        lifecycle.begin_scan()
        self.assertEqual(lifecycle.state, PackMLState.UNHOLDING)
        self.finish_transition(lifecycle)
        self.assertEqual(lifecycle.state, PackMLState.EXECUTE)

    def test_unknown_restored_state_enters_aborted_with_fault(self) -> None:
        lifecycle = PackMLLifecycle(
            mode="AUTOMATIC",
            supported_states=REQUIRED_STATES,
            restored_state="UNKNOWN",
        )

        self.assertEqual(lifecycle.state, PackMLState.ABORTED)
        self.assertEqual(lifecycle.status.reason, "RESTORE_STATE_INVALID")
        self.assertTrue(lifecycle.status.conditions[0].fault)

    def test_known_but_unsafe_restored_state_enters_aborted(self) -> None:
        lifecycle = PackMLLifecycle(
            mode="AUTOMATIC",
            supported_states=REQUIRED_STATES,
            restored_state=PackMLState.EXECUTE,
        )

        self.assertEqual(lifecycle.state, PackMLState.ABORTED)
        self.assertEqual(lifecycle.status.reason, "RESTORE_STATE_INVALID")
        self.assertIn("unsafe restored state", lifecycle.status.conditions[0].message)

    def test_explicit_safe_restore_policy_can_restore_idle(self) -> None:
        lifecycle = PackMLLifecycle(
            mode="AUTOMATIC",
            supported_states=REQUIRED_STATES,
            restored_state=PackMLState.IDLE,
            restorable_states={
                PackMLState.STOPPED,
                PackMLState.IDLE,
                PackMLState.ABORTED,
            },
        )

        self.assertEqual(lifecycle.state, PackMLState.IDLE)
        self.assertIn(PackMLState.IDLE, lifecycle.status.restorable_states)

    def test_acting_state_cannot_be_declared_restorable(self) -> None:
        with self.assertRaisesRegex(ValueError, "acting states cannot be restored"):
            PackMLLifecycle(
                mode="AUTOMATIC",
                supported_states=REQUIRED_STATES | {PackMLState.RESETTING},
                restorable_states={PackMLState.RESETTING},
            )

    def test_status_exposes_mode_capabilities_and_conditions(self) -> None:
        lifecycle = self.lifecycle(PackMLState.COMPLETE)
        condition = LifecycleCondition("READY", "Unit is ready")
        lifecycle.set_conditions([condition])

        status = lifecycle.status

        self.assertEqual(status.mode, "AUTOMATIC")
        self.assertEqual(status.supported_modes, frozenset({"AUTOMATIC"}))
        self.assertEqual(
            status.restorable_states,
            frozenset({PackMLState.STOPPED, PackMLState.ABORTED}),
        )
        self.assertIn(PackMLState.STOPPED, status.supported_states)
        self.assertIn(PackMLCommand.COMPLETE, status.supported_commands)
        self.assertEqual(status.conditions, (condition,))


if __name__ == "__main__":
    unittest.main()
