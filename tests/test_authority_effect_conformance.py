from __future__ import annotations

from dataclasses import dataclass
import unittest

from reference.python.afs_reference.packml_machine import (
    PackMLMachine,
    PackMLSnapshot,
    PackMLState,
    component_result,
)


@dataclass(frozen=True)
class ActionContext:
    revision: int
    lifecycle: PackMLSnapshot
    operation_permitted: bool


class CanonicalActionPolicy:
    """One policy used by both projection and submission in the test authority."""

    def __init__(self) -> None:
        self.calls: list[ActionContext] = []

    def __call__(self, context: ActionContext) -> bool:
        self.calls.append(context)
        return context.operation_permitted


@dataclass(frozen=True)
class AuthorityPublication:
    revision: int
    lifecycle: PackMLSnapshot
    operation_available: bool
    action_executed: bool | None = None


@dataclass(frozen=True)
class SubmissionResult:
    accepted: bool
    reason: str | None
    revision: int
    lifecycle: PackMLSnapshot


class LifecycleAuthorityFixture:
    """Small authority boundary around the real PackMLMachine for conformance."""

    def __init__(self, policy: CanonicalActionPolicy) -> None:
        self._policy = policy
        self._operation_permitted = True
        self._revision = 0
        self.machine = PackMLMachine(unit_id="conformance-unit", now=0)
        self.machine.register_component(
            "waiting",
            lambda _context: component_result(SC=False),
        )

    def _context(self) -> ActionContext:
        return ActionContext(
            revision=self._revision,
            lifecycle=self.machine.snapshot(),
            operation_permitted=self._operation_permitted,
        )

    def publish(self) -> AuthorityPublication:
        context = self._context()
        return AuthorityPublication(
            revision=context.revision,
            lifecycle=context.lifecycle,
            operation_available=self._policy(context),
        )

    def set_operation_permitted(self, permitted: bool) -> None:
        self._operation_permitted = permitted
        self._revision += 1

    def submit_operation(self) -> SubmissionResult:
        context = self._context()
        if not self._policy(context):
            return SubmissionResult(
                accepted=False,
                reason="not available in current authoritative context",
                revision=self._revision,
                lifecycle=self.machine.snapshot(),
            )

        result = self.machine.scan(
            operation_requested=True,
            now=self._revision + 1,
        )
        self._revision += 1
        return SubmissionResult(
            accepted=True,
            reason=None,
            revision=self._revision,
            lifecycle=result.snapshot,
        )


@dataclass(frozen=True)
class EffectApplication:
    lifecycle: PackMLSnapshot
    persistence_succeeded: bool
    dispatched: bool
    physically_confirmed: bool
    reconciliation_required: bool
    events: tuple[str, ...]


def apply_effect_contract(
    lifecycle: PackMLSnapshot,
    *,
    fail_safe_required: bool,
    persistence_succeeds: bool,
    dispatch_succeeds: bool,
    observation_confirms: bool,
) -> EffectApplication:
    """Apply only the ordering rules needed by the conformance examples."""

    events: list[str] = []
    if persistence_succeeds:
        events.append("persistence_succeeded")
    else:
        events.append("persistence_failed")

    dispatched = False
    if persistence_succeeds or fail_safe_required:
        dispatched = dispatch_succeeds
        events.append("dispatch_succeeded" if dispatched else "dispatch_failed")

    return EffectApplication(
        lifecycle=lifecycle,
        persistence_succeeded=persistence_succeeds,
        dispatched=dispatched,
        physically_confirmed=observation_confirms,
        reconciliation_required=fail_safe_required and not persistence_succeeds,
        events=tuple(events),
    )


@dataclass
class ClientState:
    revision: int
    cached_state: PackMLState
    operation_available: bool
    pending: bool
    action_executed: bool | None

    def reconcile(self, publication: AuthorityPublication) -> None:
        if publication.revision < self.revision:
            return
        self.revision = publication.revision
        self.cached_state = publication.lifecycle.state
        self.operation_available = publication.operation_available
        self.action_executed = publication.action_executed
        if publication.action_executed is not None:
            self.pending = False

    def retry_allowed(self, *, idempotent: bool) -> bool:
        return idempotent or (
            self.action_executed is False and self.operation_available
        )


def confirmation_component(context):
    confirmed = context.input.get("effect_confirmed") is True
    return component_result(
        SC=confirmed,
        outputs={"effectRequested": True},
    )


class AuthorityEffectConformanceTests(unittest.TestCase):
    def confirmation_machine(self) -> PackMLMachine:
        machine = PackMLMachine(initial_state=PackMLState.COMPLETING, now=0)
        machine.register_component("confirmation", confirmation_component)
        return machine

    def test_projection_and_acceptance_share_canonical_policy(self) -> None:
        policy = CanonicalActionPolicy()
        authority = LifecycleAuthorityFixture(policy)

        projection = authority.publish()
        submission = authority.submit_operation()

        self.assertTrue(projection.operation_available)
        self.assertTrue(submission.accepted)
        self.assertEqual(submission.lifecycle.state, PackMLState.RESETTING)
        self.assertEqual(len(policy.calls), 2)
        self.assertEqual(policy.calls[0], policy.calls[1])

    def test_stale_projection_is_revalidated_without_transition(self) -> None:
        policy = CanonicalActionPolicy()
        authority = LifecycleAuthorityFixture(policy)
        original = authority.machine.snapshot()

        stale = authority.publish()
        authority.set_operation_permitted(False)
        submission = authority.submit_operation()

        self.assertTrue(stale.operation_available)
        self.assertFalse(submission.accepted)
        self.assertEqual(
            submission.reason,
            "not available in current authoritative context",
        )
        self.assertEqual(submission.lifecycle, original)
        self.assertEqual(authority.machine.state, PackMLState.STOPPED)
        self.assertEqual([call.revision for call in policy.calls], [0, 1])

    def test_effect_request_and_dispatch_are_not_confirmation(self) -> None:
        machine = self.confirmation_machine()
        dispatched: list[object] = []

        def dispatch(request: object) -> bool:
            dispatched.append(request)
            return True

        requested = machine.scan(input={"effect_confirmed": False}, now=1)
        request = requested.component_results[0].outputs["effectRequested"]
        dispatch_accepted = dispatch(request)
        after_dispatch = machine.scan(input={"effect_confirmed": False}, now=2)

        self.assertEqual(dispatched, [True])
        self.assertTrue(dispatch_accepted)
        self.assertFalse(after_dispatch.SC)
        self.assertEqual(after_dispatch.snapshot.state, PackMLState.COMPLETING)

    def test_acting_state_remains_incomplete_across_scans(self) -> None:
        machine = self.confirmation_machine()

        results = [
            machine.scan(input={"effect_confirmed": False}, now=now)
            for now in (1, 2, 3)
        ]

        self.assertTrue(all(not result.SC for result in results))
        self.assertTrue(
            all(result.snapshot.state is PackMLState.COMPLETING for result in results)
        )

    def test_ordinary_effect_allows_delayed_confirmation(self) -> None:
        machine = self.confirmation_machine()

        awaiting = machine.scan(input={"effect_confirmed": False}, now=1)
        confirmed = machine.scan(input={"effect_confirmed": True}, now=2)

        self.assertFalse(awaiting.SC)
        self.assertEqual(awaiting.snapshot.state, PackMLState.COMPLETING)
        self.assertTrue(confirmed.SC)
        self.assertEqual(confirmed.snapshot.state, PackMLState.COMPLETE)

    def test_fail_safe_effect_survives_persistence_failure(self) -> None:
        machine = PackMLMachine(now=0)
        lifecycle = machine.snapshot()

        ordinary = apply_effect_contract(
            lifecycle,
            fail_safe_required=False,
            persistence_succeeds=False,
            dispatch_succeeds=True,
            observation_confirms=False,
        )
        fail_safe = apply_effect_contract(
            lifecycle,
            fail_safe_required=True,
            persistence_succeeds=False,
            dispatch_succeeds=True,
            observation_confirms=False,
        )

        self.assertFalse(ordinary.dispatched)
        self.assertTrue(fail_safe.dispatched)
        self.assertFalse(fail_safe.persistence_succeeded)
        self.assertFalse(fail_safe.physically_confirmed)
        self.assertTrue(fail_safe.reconciliation_required)
        self.assertEqual(
            fail_safe.events,
            ("persistence_failed", "dispatch_succeeded"),
        )
        self.assertIs(fail_safe.lifecycle, lifecycle)
        self.assertEqual(machine.snapshot(), lifecycle)

    def test_newer_snapshot_proves_freshness_not_action_outcome(self) -> None:
        machine = PackMLMachine(now=0)
        lifecycle = machine.snapshot()
        client = ClientState(
            revision=1,
            cached_state=lifecycle.state,
            operation_available=True,
            pending=True,
            action_executed=None,
        )
        newer = AuthorityPublication(
            revision=2,
            lifecycle=lifecycle,
            operation_available=True,
            action_executed=None,
        )

        client.reconcile(newer)

        self.assertEqual(client.revision, 2)
        self.assertEqual(client.cached_state, lifecycle.state)
        self.assertIsNone(client.action_executed)
        self.assertTrue(client.pending)
        self.assertFalse(client.retry_allowed(idempotent=False))

    def test_retry_requires_idempotency_or_authoritative_non_execution(self) -> None:
        cases = (
            (None, False, True, False),
            (None, True, True, True),
            (False, False, True, True),
            (False, False, False, False),
            (True, False, True, False),
        )

        for executed, idempotent, available, expected in cases:
            with self.subTest(
                executed=executed,
                idempotent=idempotent,
                available=available,
            ):
                client = ClientState(
                    revision=1,
                    cached_state=PackMLState.STOPPED,
                    operation_available=available,
                    pending=True,
                    action_executed=executed,
                )
                self.assertEqual(
                    client.retry_allowed(idempotent=idempotent),
                    expected,
                )

    def test_client_state_yields_to_authoritative_snapshot(self) -> None:
        machine = PackMLMachine(now=0)
        publication = AuthorityPublication(
            revision=2,
            lifecycle=machine.snapshot(),
            operation_available=False,
            action_executed=False,
        )
        client = ClientState(
            revision=1,
            cached_state=PackMLState.EXECUTE,
            operation_available=True,
            pending=True,
            action_executed=None,
        )

        client.reconcile(publication)

        self.assertEqual(client.cached_state, publication.lifecycle.state)
        self.assertEqual(
            client.operation_available,
            publication.operation_available,
        )
        self.assertFalse(client.pending)
        self.assertFalse(hasattr(client, "policy"))
        self.assertFalse(hasattr(client, "machine"))
        self.assertEqual(machine.state, PackMLState.STOPPED)


if __name__ == "__main__":
    unittest.main()
