# AFS Authority and Effect Contracts 0.1

- Status: Draft
- Version: 0.1.0
- Date: 2026-10-06
- Decision: `ADR-0009`
- Depends on: `AFS-PACKML-UNIT-PROFILE-0.1`

## 1. Scope

This specification defines the boundary between an AFS Unit's authoritative
PackML lifecycle, action-capability projections, effect requests, physical
observations, and participating clients or adapters.

It defines semantic contracts, not a wire protocol, user interface, transport,
or actuator API. It does not add physical feedback fields to PackML state and
does not change the transitions defined by the AFS PackML Unit Profile.

## 2. Conformance language

The key words **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, and **MAY**
indicate requirement levels.

## 3. Terms

**Lifecycle authority** is the Unit's sole owner of PackML state and transition
policy.

**Authoritative context** is the canonical input to an action decision. It
contains the current lifecycle snapshot and every current mode, supported-action
declaration, guard, condition, request, and policy value needed for that
decision.

**Authoritative snapshot** is an immutable publication of Unit facts from the
lifecycle authority. It contains the lifecycle snapshot and MAY contain
projections, observations, diagnostic data, and integration metadata such as an
authority revision.

**Control projection** is the lifecycle authority's derived statement of which
actions are currently available or unavailable, optionally with rejection or
blocking reasons.

**Effect request** is a requested external outcome derived from an authoritative
decision. Dispatch or acceptance of the request does not prove the outcome.

**Observation** is evidence acquired from outside the lifecycle authority and
presented to the Unit for evaluation. An observation can confirm or contradict
a requested effect without becoming PackML state.

**Client** means any external participant that presents or submits actions,
including a human-machine interface or adapter. A client is not a lifecycle
authority.

## 4. Single lifecycle authority

Each Unit MUST retain exactly one lifecycle authority as required by the AFS
PackML Unit Profile. Only that authority may validate lifecycle actions and
change PackML state.

Components MUST remain evidence providers. They MAY derive `SC`, alarms, and
effect-request outputs from the immutable lifecycle snapshot and observations,
but MUST NOT accept actions or assign lifecycle state.

Clients, effect executors, observation providers, and transports MUST NOT
duplicate transition policy or present their local state as authoritative Unit
state. They MAY keep pending, cached, optimistic, or presentation state, but
MUST distinguish it from the latest authoritative snapshot and reconcile it as
specified in section 9.

## 5. Authoritative control projection

The lifecycle authority MAY publish a control projection as part of, or
atomically associated with, an authoritative snapshot. When a client presents
action availability, that availability MUST come from such an authoritative
projection. For every action presented to a client, the projection SHOULD state
whether the action is currently available. It MAY include a stable reason when
an action is blocked or unavailable.

The lifecycle authority MUST derive the projection and action acceptance with
the same decision function and canonical authoritative-context construction.
Projection and acceptance can occur at different times and therefore use
different current instances of that context, but MUST NOT use separate
transition policies.

A client MUST use the control projection when deciding which actions to offer.
It MUST NOT infer legality solely from a visible PackML state or reproduce
guards, priorities, or transition tables locally.

A control projection describes the snapshot from which it was derived. It does
not reserve an action, authorize future execution, or guarantee acceptance. On
submission, the lifecycle authority MUST re-evaluate the action against the
current authoritative context. If the action is no longer valid, the lifecycle
authority MUST reject it explicitly without changing lifecycle state because of
that action.

Authorization of an actor, when required by an application, is an additional
acceptance condition and does not make the client a lifecycle authority.

## 6. Effect request and observation

The following facts MUST remain distinct:

1. the lifecycle authority accepted an action or made a transition;
2. a component emitted an effect request;
3. an executor accepted or dispatched that request;
4. a later authoritative observation confirmed the requested physical outcome.

An implementation MUST NOT treat facts 1, 2, or 3 as fact 4 unless its declared
effect contract proves that they are equivalent for that particular effect.
Command acknowledgement alone SHOULD NOT be used as physical confirmation.

An effect contract that requires confirmation MUST define:

- the requested outcome;
- the observation source and confirmation predicate;
- how contradictory, unavailable, or stale observations are handled;
- the applicable timeout or failure policy;
- whether the effect is an ordinary operating effect or a fail-safe effect.

Effect executors and observation providers operate outside the lifecycle state
machine. Their results enter the next applicable evaluation as observations,
conditions, or alarms. Physical feedback MUST NOT be encoded as a new PackML
state or as a client-owned lifecycle transition.

## 7. Completion across scans

Issuing an effect request MUST NOT by itself set `SC` true when the declared
completion criterion requires observed physical confirmation.

A PackML acting state MAY remain active across any number of scans permitted by
its timeout policy while awaiting that observation. Components evaluate the
latest authoritative observation on each scan and provide `SC`, alarms, and
outputs as evidence. The `PackMLMachine` remains the only component that applies
transition priorities and changes lifecycle state.

AFS does not require same-scan readback for ordinary effects. A profile or
application MAY permit immediate completion when no physical confirmation is
required, or when valid confirmation is already present in the authoritative
observations. It MUST document that completion predicate.

Repeated scans MAY reproduce an outstanding effect request. The effect contract
MUST define whether requests are level-triggered, edge-triggered, deduplicated,
or idempotent so that repetition does not acquire accidental lifecycle meaning.

## 8. Fail-safe effect policy

A profile or application MAY classify an effect as fail-safe and impose a
stricter contract than it uses for ordinary operating effects.

Such a contract MAY require a safety-directed effect to be dispatched in the
same control cycle that selects the fail-safe outcome. If normal durable
commitment cannot be completed, the declared policy MAY still require dispatch.
Persistence failure MUST NOT silently suppress a required fail-safe effect. It
MAY also require positive physical verification before the Unit reports the
applicable transition complete or the requested safe condition achieved.
Immediate dispatch does not mean that observation must be available in the same
scan.

When positive verification is required:

- dispatch success MUST NOT be reported as physical success;
- `SC` MUST remain false until the confirmation predicate is satisfied;
- a missing, stale, or contradictory observation MUST follow the declared
  fail-closed timeout or fault policy;
- status MUST distinguish requested, dispatched, confirmed, and failed or
  unverified outcomes where those distinctions apply.

The fail-safe classification, dispatch deadline, confirmation predicate, and
failure response MUST be explicit and testable. A fail-safe path taken when
persistence fails MUST also be observable and reconcilable with the single
lifecycle authority. It MUST NOT assign or imply an uncommitted lifecycle state.
A strict fail-safe contract MUST NOT silently impose same-scan confirmation on
ordinary effects.

## 9. Client reconciliation and ambiguous outcomes

Authoritative snapshots published across an asynchronous client boundary MUST
be comparable as older, identical, or newer. A monotonically increasing
authority revision is the preferred mechanism. It belongs to the Unit's
publication or integration envelope; it need not be part of PackML state or the
`PackMLMachine` snapshot.

The lifecycle authority MUST advance that revision, or publish equivalent
ordered evidence, when accepting an action changes an authoritative request,
lifecycle, condition, or effect-reconciliation fact. This requirement applies
even when the externally visible PackML state later has the same value as before
the submission.

An action submission SHOULD carry a correlation identifier and the authority
revision on which the client acted. These values provide traceability and stale
context detection; they MUST NOT bypass current-context validation.

If delivery of the action result fails after submission, the client MUST treat
the outcome as ambiguous whenever the action may have reached the lifecycle
authority. It MUST NOT blindly issue the same action again.

The action contract MUST identify the authoritative fact that proves acceptance
or rejection. The client MUST obtain a snapshot newer than its pre-submission
snapshot and reconcile its pending state using one or more of:

- the action correlation recorded in authoritative status or history;
- authoritative lifecycle state, request, condition, or effect evidence that
  proves whether the action occurred.

A newer revision proves snapshot freshness, not action outcome by itself. A
changed state can be sufficient outcome evidence, but a state that appears
unchanged does not by itself prove non-execution. If the newer snapshot lacks
the fact required by the action contract, the outcome remains ambiguous. The
client MAY resubmit only when the lifecycle authority explicitly supports
idempotent handling for that submission, or when newer authoritative evidence
proves the earlier action did not execute and the current control projection
still makes it available.

Transport timeouts, delivery retries, correlation storage, and publication
mechanisms MUST remain outside `PackMLMachine`.

## 10. Snapshot and commit ordering

Normal external effects derived from a successful authoritative lifecycle
decision MUST follow commitment of the lifecycle result according to the
hardened runtime's snapshot contract. The publication of lifecycle state,
control projection, and authority revision SHOULD be atomic or otherwise
ordered so clients cannot mistake mismatched values for one authoritative
decision.

A declared fail-safe policy MAY require a safety-directed effect even when that
normal durable commitment cannot be completed. It MUST define when this
exception applies and how persistence, dispatch, and verification outcomes are
made observable and later reconciled with the lifecycle authority. The policy
MUST preserve a single lifecycle authority, MUST NOT silently suppress the
required effect because persistence failed, and MUST NOT report an uncommitted
or unverified outcome as completed. Dispatch success MUST NOT be reported as
physical confirmation.

## 11. Conformance

An implementation conforms to this specification only when automated tests or
equivalent conformance evidence verify:

- action availability and action acceptance use one authoritative policy and
  canonical context;
- every submitted action is revalidated against current authoritative state;
- clients do not reproduce lifecycle transition policy;
- effect-request dispatch is distinguishable from observed confirmation;
- an acting state can remain incomplete across multiple scans until feedback
  satisfies its declared predicate;
- ordinary effects are not subject to an undeclared same-scan readback rule;
- each declared fail-safe effect meets its dispatch, verification, timeout, and
  fail-closed policy;
- persistence failure does not silently suppress an effect required by a
  declared fail-safe policy, and the exceptional path remains observable,
  testable, and reconcilable;
- ambiguous action outcomes reconcile through newer authoritative evidence and
  are not blindly retried;
- local client state yields to the authoritative snapshot; and
- transport, presentation, and physical feedback do not become lifecycle
  authorities or PackML state.
