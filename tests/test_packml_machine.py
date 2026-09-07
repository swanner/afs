from __future__ import annotations

import unittest

from reference.python.afs_reference.packml import PackMLState
from reference.python.afs_reference.packml_machine import (
    AlarmResponse,
    ComponentAlarm,
    ComponentResult,
    PACKML_ALARM_SOURCE,
    PackMLMachine,
    component_result,
    legal_transition,
    validate_snapshot,
)


def ready(_context):
    return component_result()


class PackMLMachineTests(unittest.TestCase):
    def machine(self, **options) -> PackMLMachine:
        machine = PackMLMachine(now=0, **options)
        machine.register_component("ready", ready)
        return machine

    def test_machine_runs_internal_microsteps_to_terminal_boundary(self) -> None:
        result = self.machine().scan(operation_requested=True, now=1)

        self.assertEqual(result.previous_state, PackMLState.STOPPED)
        self.assertEqual(result.snapshot.state, PackMLState.COMPLETE)
        self.assertEqual(result.transitions, 6)
        self.assertTrue(result.SC)

    def test_terminal_boundary_prevents_outgoing_transition_in_same_scan(self) -> None:
        machine = self.machine(initial_state=PackMLState.COMPLETE)

        first = machine.scan(operation_requested=False, now=1)
        second = machine.scan(operation_requested=False, now=2)

        self.assertEqual(first.snapshot.state, PackMLState.STOPPED)
        self.assertEqual(first.transitions, 2)
        self.assertEqual(second.snapshot.state, PackMLState.STOPPED)
        self.assertFalse(second.transitioned)

    def test_components_share_one_frozen_snapshot_per_pass(self) -> None:
        seen: list[tuple[str, PackMLState]] = []
        machine = PackMLMachine(initial_state=PackMLState.EXECUTE, now=0)

        def first(context):
            seen.append(("first", context.machine.state))
            with self.assertRaises(TypeError):
                context.input["changed"] = True  # type: ignore[index]
            with self.assertRaises(TypeError):
                context.input["nested"]["changed"] = True  # type: ignore[index]
            return component_result(SC=False)

        def second(context):
            seen.append(("second", context.machine.state))
            return component_result(SC=True)

        machine.register_component("first", first)
        machine.register_component("second", second)
        result = machine.scan(
            operation_requested=True,
            input={"value": 1, "nested": {"changed": False}},
            now=1,
        )

        self.assertEqual(
            seen,
            [("first", PackMLState.EXECUTE), ("second", PackMLState.EXECUTE)],
        )
        self.assertFalse(result.SC)
        self.assertEqual(result.snapshot.state, PackMLState.EXECUTE)

    def test_alarm_reconciliation_re_evaluates_and_discards_stale_outputs(self) -> None:
        calls = 0
        machine = PackMLMachine(initial_state=PackMLState.EXECUTE, now=0)

        def component(context):
            nonlocal calls
            calls += 1
            if not context.machine.alarms:
                return component_result(
                    SC=False,
                    alarms=(ComponentAlarm("WAIT", AlarmResponse.SUSPEND),),
                    outputs={"pass": "stale"},
                )
            return component_result(
                SC=False,
                alarms=(ComponentAlarm("WAIT", AlarmResponse.SUSPEND),),
                outputs={"pass": "stable"},
            )

        machine.register_component("solar", component)
        result = machine.scan(operation_requested=True, now=1)

        self.assertGreaterEqual(calls, 3)
        self.assertEqual(result.snapshot.state, PackMLState.SUSPENDING)
        self.assertEqual(result.component_results[0].outputs["pass"], "stable")

    def test_alarms_are_canonical_and_sorted(self) -> None:
        machine = PackMLMachine(initial_state=PackMLState.EXECUTE, now=0)
        machine.register_component(
            "zeta",
            lambda _context: component_result(
                SC=False,
                alarms=(
                    {"code": "B", "response": None, "details": {"z": 1, "a": 2}},
                    {"code": "A", "response": None},
                ),
            ),
        )

        result = machine.scan(operation_requested=True, now=1)

        self.assertEqual([alarm.code for alarm in result.snapshot.alarms], ["A", "B"])
        self.assertEqual(result.snapshot.alarms[1].to_dict()["details"], {"a": 2, "z": 1})

    def test_abort_alarm_latches_reason_and_reaches_aborted(self) -> None:
        machine = PackMLMachine(initial_state=PackMLState.EXECUTE, now=0)
        machine.register_component(
            "fault",
            lambda _context: component_result(
                alarms=(
                    ComponentAlarm(
                        "CONTACTOR_FAULT",
                        AlarmResponse.ABORT,
                        {"reason": "relay mismatch"},
                    ),
                )
            ),
        )

        result = machine.scan(operation_requested=True, now=1)

        self.assertEqual(result.snapshot.state, PackMLState.ABORTED)
        self.assertEqual(result.snapshot.abort_reason, "relay mismatch")

    def test_hold_has_priority_over_suspend(self) -> None:
        machine = PackMLMachine(initial_state=PackMLState.EXECUTE, now=0)
        machine.register_component(
            "conditions",
            lambda _context: component_result(
                SC=False,
                alarms=(
                    ComponentAlarm("EXTERNAL", AlarmResponse.SUSPEND),
                    ComponentAlarm("INTERNAL", AlarmResponse.HOLD),
                ),
            ),
        )

        result = machine.scan(operation_requested=True, now=1)

        self.assertEqual(result.snapshot.state, PackMLState.HOLDING)

    def test_sc_timeout_enters_system_failure_with_framework_alarm(self) -> None:
        machine = PackMLMachine(
            initial_state=PackMLState.RESETTING,
            now=0,
            sc_timeout_ms=90_000,
        )
        machine.register_component(
            "blocked", lambda _context: component_result(SC=False)
        )

        result = machine.scan(operation_requested=True, now=90_000)

        self.assertEqual(result.snapshot.state, PackMLState.SYSTEM_FAILURE)
        self.assertEqual(result.snapshot.failed_from_state, PackMLState.RESETTING)
        self.assertEqual(result.snapshot.abort_reason, "SC_TIMEOUT")
        self.assertEqual(result.snapshot.alarms[0].source, PACKML_ALARM_SOURCE)
        self.assertEqual(
            result.snapshot.alarms[0].to_dict()["details"],
            {"state": "RESETTING", "timeoutMs": 90_000},
        )

    def test_acknowledged_system_failure_recovers_through_abort_path(self) -> None:
        snapshot = {
            "unitId": "unit-1",
            "state": "SYSTEM_FAILURE",
            "stateEnteredAt": 90_000,
            "alarms": [
                {
                    "source": PACKML_ALARM_SOURCE,
                    "code": "SC_TIMEOUT",
                    "response": None,
                    "details": {"state": "RESETTING", "timeoutMs": 90_000},
                }
            ],
            "abortReason": "SC_TIMEOUT",
            "failedFromState": "RESETTING",
        }
        machine = PackMLMachine(snapshot=snapshot, now=100_000)
        machine.register_component("ready", ready)

        result = machine.scan(acknowledge_requested=True, now=100_001)

        self.assertEqual(result.snapshot.state, PackMLState.STOPPED)
        self.assertIsNone(result.snapshot.abort_reason)
        self.assertIsNone(result.snapshot.failed_from_state)
        self.assertEqual(result.transitions, 4)

    def test_restoration_requires_explicit_now(self) -> None:
        with self.assertRaisesRegex(TypeError, "now is required"):
            PackMLMachine(
                snapshot={
                    "state": "STOPPED",
                    "stateEnteredAt": 0,
                    "alarms": [],
                    "abortReason": None,
                    "failedFromState": None,
                }
            )

    def test_future_snapshot_fails_closed(self) -> None:
        with self.assertRaisesRegex(TypeError, "must not be in the future"):
            validate_snapshot(
                {
                    "state": "STOPPED",
                    "stateEnteredAt": 101,
                    "alarms": [],
                    "abortReason": None,
                    "failedFromState": None,
                },
                now=100,
            )

    def test_snapshot_requires_explicit_abort_reason_field(self) -> None:
        with self.assertRaisesRegex(TypeError, "abortReason"):
            validate_snapshot(
                {
                    "state": "STOPPED",
                    "stateEnteredAt": 1,
                    "alarms": [],
                    "failedFromState": None,
                },
                now=2,
            )

    def test_impossible_system_failure_snapshot_fails_closed(self) -> None:
        with self.assertRaisesRegex(TypeError, "must be SC-timeout-capable"):
            validate_snapshot(
                {
                    "state": "SYSTEM_FAILURE",
                    "stateEnteredAt": 1,
                    "alarms": [
                        {
                            "source": PACKML_ALARM_SOURCE,
                            "code": "SC_TIMEOUT",
                            "response": None,
                            "details": {"state": "STOPPED", "timeoutMs": 90_000},
                        }
                    ],
                    "abortReason": "SC_TIMEOUT",
                    "failedFromState": "STOPPED",
                },
                now=2,
            )

    def test_malformed_alarm_and_cyclic_details_fail_closed(self) -> None:
        machine = PackMLMachine(initial_state=PackMLState.EXECUTE, now=0)
        machine.register_component(
            "invalid",
            lambda _context: component_result(
                alarms=({"code": "FAULT", "response": "IGNORE"},)
            ),
        )
        with self.assertRaisesRegex(TypeError, "Invalid alarm response"):
            machine.scan(operation_requested=True, now=1)

        cyclic: dict[str, object] = {}
        cyclic["self"] = cyclic
        machine = PackMLMachine(initial_state=PackMLState.EXECUTE, now=0)
        machine.register_component(
            "invalid",
            lambda _context: component_result(
                alarms=(
                    {"code": "FAULT", "response": None, "details": cyclic},
                )
            ),
        )
        with self.assertRaisesRegex(TypeError, "JSON-like"):
            machine.scan(operation_requested=True, now=1)

    def test_oscillating_alarms_hit_bounded_internal_step_limit(self) -> None:
        machine = PackMLMachine(initial_state=PackMLState.EXECUTE, now=0)

        def oscillating(context):
            if context.machine.alarms:
                return component_result(SC=False)
            return component_result(
                SC=False,
                alarms=(ComponentAlarm("OSCILLATING", None),),
            )

        machine.register_component("unstable", oscillating)
        with self.assertRaisesRegex(RuntimeError, r"maximum \(64\) exceeded"):
            machine.scan(operation_requested=True, now=1)

    def test_timeout_preserves_previously_latched_abort_reason(self) -> None:
        machine = PackMLMachine(
            snapshot={
                "unitId": "unit-1",
                "state": "ABORTING",
                "stateEnteredAt": 0,
                "alarms": [],
                "abortReason": "DEVICE_FAULT",
                "failedFromState": None,
            },
            now=1,
            sc_timeout_ms=10,
        )
        machine.register_component(
            "blocked", lambda _context: component_result(SC=False)
        )

        result = machine.scan(now=10)

        self.assertEqual(result.snapshot.state, PackMLState.SYSTEM_FAILURE)
        self.assertEqual(result.snapshot.failed_from_state, PackMLState.ABORTING)
        self.assertEqual(result.snapshot.abort_reason, "DEVICE_FAULT")
        self.assertEqual(
            validate_snapshot(result.snapshot, now=10),
            result.snapshot,
        )

    def test_every_state_has_a_total_scan_case(self) -> None:
        for state in PackMLState:
            with self.subTest(state=state):
                if state is PackMLState.SYSTEM_FAILURE:
                    snapshot = {
                        "unitId": None,
                        "state": "SYSTEM_FAILURE",
                        "stateEnteredAt": 0,
                        "alarms": [
                            {
                                "source": PACKML_ALARM_SOURCE,
                                "code": "SC_TIMEOUT",
                                "response": None,
                                "details": {
                                    "state": "RESETTING",
                                    "timeoutMs": 90_000,
                                },
                            }
                        ],
                        "abortReason": "SC_TIMEOUT",
                        "failedFromState": "RESETTING",
                    }
                    machine = PackMLMachine(snapshot=snapshot, now=1)
                else:
                    machine = PackMLMachine(initial_state=state, now=0)
                machine.register_component(
                    "blocked", lambda _context: component_result(SC=False)
                )
                result = machine.scan(operation_requested=True, now=1)
                self.assertIsInstance(result.snapshot.state, PackMLState)

    def test_reserved_component_name_and_duplicate_are_rejected(self) -> None:
        machine = PackMLMachine(now=0)
        with self.assertRaisesRegex(TypeError, "reserved"):
            machine.register_component(PACKML_ALARM_SOURCE, ready)
        machine.register_component("component", ready)
        with self.assertRaisesRegex(ValueError, "already registered"):
            machine.register_component("component", ready)

    def test_machine_requires_a_component(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "at least one"):
            PackMLMachine(now=0).scan(now=1)

    def test_component_result_contract_is_strict(self) -> None:
        with self.assertRaisesRegex(TypeError, "SC must be boolean"):
            ComponentResult(SC=1)  # type: ignore[arg-type]
        with self.assertRaisesRegex(TypeError, "outputs must be a mapping"):
            component_result(outputs=[])  # type: ignore[arg-type]

    def test_state_is_read_only(self) -> None:
        machine = self.machine()
        with self.assertRaises(AttributeError):
            machine.state = PackMLState.EXECUTE  # type: ignore[misc]

    def test_legal_transition_includes_failure_but_rejects_illegal_edges(self) -> None:
        self.assertTrue(
            legal_transition(PackMLState.RESETTING, PackMLState.SYSTEM_FAILURE)
        )
        self.assertTrue(
            legal_transition(PackMLState.SYSTEM_FAILURE, PackMLState.ABORTING)
        )
        self.assertFalse(legal_transition(PackMLState.STOPPED, PackMLState.EXECUTE))


if __name__ == "__main__":
    unittest.main()
