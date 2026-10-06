# ADR-0009: Adopt authority and effect contracts

- Status: Accepted
- Date: 2026-10-06

## Context

Production use has exposed several integration boundaries that are not fully
specified by lifecycle transitions alone.

A client can display an action as available using stale or independently
reimplemented rules even though the authoritative Unit would reject it. An
effect executor can mistake acceptance of an output request for evidence that
the requested physical condition exists. Safety-related effects can require a
stronger dispatch and confirmation policy than ordinary operating effects. A
client can also lose a response after submitting an action and be unable to
know whether execution occurred.

Resolving those concerns inside clients, transports, or effect adapters would
create additional lifecycle authorities. Resolving them by adding physical
feedback to PackML state would conflate operational lifecycle with process
observation. Neither approach preserves the existing AFS rule that the
`PackMLMachine` is the sole lifecycle authority and components contribute only
evidence.

## Decision

AFS adopts explicit authority, effect, and reconciliation contracts around the
authoritative PackML lifecycle.

The lifecycle authority derives an action-availability projection from the same
canonical context and policy used to validate actions. Clients MUST consume
that projection rather than reproduce transition policy. Because a projection
can become stale, the lifecycle authority MUST revalidate every submitted
action against its current context before accepting it.

An effect request expresses a desired external outcome; it is not evidence that
the outcome occurred. Effect executors report later authoritative observations,
and components use those observations to provide state-complete (`SC`), alarm,
and output evidence. Acting states MAY therefore span multiple scans. AFS does
not impose same-scan feedback as a general requirement.

Normal external effects derived from a successful authoritative lifecycle
decision require durable commitment before dispatch. A declared fail-safe
policy MAY instead require a safety-directed effect when normal durable
commitment cannot be completed. Persistence failure MUST NOT silently suppress
that required effect. The exceptional path MUST be explicit, observable,
testable, and reconcilable with the lifecycle authority. Dispatch remains
distinct from positive physical verification, and failure to dispatch or verify
prevents the applicable completion claim. This stricter policy does not make
immediate verification mandatory for ordinary operating effects.

When an action response is lost after submission, the outcome is ambiguous.
The client MUST reconcile against a demonstrably newer authoritative snapshot
before deciding whether another submission is safe. It MUST NOT blindly retry
an action that may already have executed. An explicitly idempotent action or
idempotency key MAY permit a safe retry. Transport and delivery mechanisms
remain outside `PackMLMachine`.

Human-machine interfaces, external clients, and adapters are participants in
and projections of these contracts. They MAY retain local pending and
presentation state, but MUST reconcile it to authoritative snapshots and MUST
NOT become lifecycle authorities.

These rules are defined normatively by
`AFS-AUTHORITY-EFFECT-CONTRACTS-0.1`.

## Consequences

Action presentation and action acceptance cannot drift into separate policy
implementations. A displayed capability is useful guidance, not a reservation
or guarantee, and stale submissions have an explicit rejection path.

Requested outputs, observed physical conditions, and PackML lifecycle state
remain distinct. Implementations can wait across scans for ordinary feedback
while applying stronger dispatch and verification rules where a declared
fail-safe policy requires them.

Distributed clients gain a deterministic reconciliation rule for ambiguous
outcomes. Authority revisions, action correlation, and idempotency may be
carried by an integration envelope without enlarging the `PackMLMachine` public
interface or embedding transport concerns in it.

Implementations must expose enough authoritative context to project available
actions and distinguish newer snapshots. Profiles and applications must define
their effect confirmation and fail-safe policies explicitly.

## Alternatives considered

Allowing each client to infer available actions from visible PackML state was
rejected because guards, modes, conditions, and intervening transitions can
make that inference incomplete or stale.

Treating successful effect-request dispatch as physical confirmation was
rejected because request delivery and physical outcome are different facts.

Requiring all effects to confirm in the same scan was rejected because normal
physical feedback can be asynchronous and PackML acting states already model
unfinished work.

Placing transport retries, client pending state, or physical feedback inside
`PackMLMachine` was rejected because those concerns do not own lifecycle
transition policy and would make the machine implementation-specific.
