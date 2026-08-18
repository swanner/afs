# ADR-0007: Compose AFS Units Hierarchically

- Status: Accepted
- Date: 2026-08-18

## Context

Some AFS applications contain independent Units that exchange information. Other
applications contain a real equipment or responsibility hierarchy in which a
parent coordinates several children. Treating both relationships alike would
either couple independent Units unnecessarily or leave parent and child
lifecycle behaviour undefined.

For example, a solar availability Unit and a charging Unit are independent even
when charging consumes the solar observation. In contrast, an alarm Zone Unit
may coordinate Room Units and depend on their lifecycle completion and
conditions.

PackML standardizes the lifecycle of an individual Unit but does not by itself
define the AFS ownership, registration, scanning, and aggregation rules for a
hierarchy of Units.

## Decision

AFS supports recursive Unit composition. A Subunit is a complete AFS Unit that
conforms to the same PackML Unit Contract as a top-level Unit. `Subunit` describes
its ownership position and does not define a weaker Unit type.

An Application explicitly registers top-level Units. A parent Unit explicitly
registers its direct Subunits. Automatic discovery is not permitted. A Unit MUST
have at most one parent, and Unit ownership MUST form an acyclic tree.

A parent coordinates lifecycle through requests and commands. It MUST NOT assign
or mirror a child's PackML state directly. Each Subunit evaluates its own
observations, guards, conditions, transitions, sequencers, and intents.

A parent MUST define an explicit aggregation policy that determines:

- which Subunits participate in each parent command;
- the deterministic scan order;
- which child states and state-complete indications permit the parent transition
  to complete;
- how child conditions, alarms, and faults affect the parent;
- whether degraded or partial operation is allowed.

A parent MUST NOT report a coordinated transition complete until every required
Subunit satisfies that transition's aggregation policy. A Subunit failure does
not automatically prescribe one universal parent state; the declared aggregation
policy determines whether the parent waits, aborts, or continues in a documented
degraded form.

Parent and Subunit status MUST remain independently observable. Aggregation MUST
NOT erase the child state or the originating condition.

Hierarchy is used only when the parent owns and coordinates the children's
lifecycle. A data dependency does not create a hierarchy. Independent Units
exchange information through Observations, Memory, Requests, Conditions, and
Intents as defined by their contracts; they MUST NOT call each other's internal
state machines.

A sensor, actuator, Provider, or Executor is not automatically a Subunit. It
becomes a Unit only when it has an independently meaningful responsibility,
lifecycle, conditions, and behaviour.

## Consequences

AFS can represent both flat applications and coordinated Unit hierarchies without
changing the Unit contract. Subunits can themselves own Subunits.

Parent state becomes a verified aggregate rather than a status copied to every
child. Transition delays, failures, and partial readiness remain visible and can
be tested deterministically.

Implementations must add explicit child registration, request propagation,
aggregation policies, cycle prevention, and hierarchical diagnostics.

Applications without lifecycle ownership relationships remain flat. In
particular, consuming another Unit's observation does not make the consumer its
parent.

The AFS reference implementation and conformance suite must demonstrate both
peer communication and Parent/Subunit coordination.

## Alternatives considered

Making every dependency a Parent/Subunit relationship was rejected because data
flow does not imply lifecycle ownership.

Making Subunits copy the parent state was rejected because it hides incomplete
transitions, child faults, and independent child evaluation.

Defining Subunits as partial objects without a PackML lifecycle was rejected
because it would create two incompatible kinds of AFS Unit and weaken common
diagnostics.

Allowing direct Unit-to-Unit state machine calls was rejected because it creates
hidden coupling and bypasses explicit AFS contracts.
