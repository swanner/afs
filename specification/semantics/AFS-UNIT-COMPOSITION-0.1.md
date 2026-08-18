# AFS Unit Composition 0.1

- Status: Draft
- Version: 0.1.0
- Date: 2026-08-18
- Decision: `ADR-0007`
- Depends on: `AFS-PACKML-UNIT-PROFILE-0.1`

## 1. Scope

This specification defines how AFS Units form a deterministic ownership
hierarchy. It distinguishes Parent/Subunit lifecycle coordination from ordinary
data exchange between independent Units.

## 2. Conformance language

The key words **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, and **MAY**
indicate requirement levels.

## 3. Unit roles

An Application owns top-level Units. A Parent Unit owns direct Subunits. A
Subunit is a complete AFS Unit conforming to the same AFS PackML Unit Profile as
a top-level Unit.

`Parent` and `Subunit` describe ownership positions. They MUST NOT define weaker
or alternative Unit types. A Subunit MAY itself be a Parent.

A Provider, Executor, sensor, or actuator is not a Unit merely because it belongs
to a Unit. It becomes a Unit only when it has an independently meaningful
responsibility, lifecycle, Conditions, and behaviour.

## 4. Ownership tree

Top-level Units and Subunits MUST be registered explicitly. Automatic discovery
is not permitted.

Each Unit MUST have no more than one direct owner: either the Application or one
Parent Unit. The resulting ownership graph MUST be acyclic.

An implementation MUST reject:

- registration of a Unit under more than one owner;
- registration of a Unit as its own descendant;
- duplicate registration under the same owner;
- simultaneous top-level and Subunit registration of the same instance.

Registration order MUST be stable and observable for deterministic scanning.

## 5. Hierarchy criterion

A Parent/Subunit relationship exists only when the Parent owns and coordinates
the Subunit's lifecycle.

Consuming another Unit's Observation, Condition, Request, or Intent does not by
itself create hierarchy. Independent Units MUST remain peers when neither owns
the other's lifecycle.

For example, a Solar Unit and a Charging Unit are peers when charging consumes a
solar availability Observation. An alarm Zone Unit and its Room Units form a
hierarchy when the Zone coordinates the Room lifecycles.

## 6. Lifecycle coordination

A Parent coordinates Subunits through PackML commands and explicit AFS Requests.
It MUST NOT assign, mirror, or mutate a Subunit's lifecycle state.

Each Subunit MUST evaluate its own Observations, guards, transitions, domain
sequencers, Conditions, faults, and Intents.

For every coordinated Parent transition, the Parent MUST declare an aggregation
policy containing at least:

- participating Subunits;
- the request or command sent to each participant;
- the child-state and state-complete criteria for success;
- Condition and fault propagation behaviour;
- timeout behaviour;
- whether degraded or partial operation is permitted.

The Parent MUST NOT report a coordinated transition complete until every
required participant satisfies the declared success criteria.

A Subunit fault MUST remain attributable to its originating Subunit. The Parent
MUST apply its declared policy to wait, stop, abort, or continue in a documented
degraded form. No universal child-fault-to-parent-state mapping is implied.

## 7. Deterministic scan

A Parent scan that coordinates Subunits MUST use these logical phases:

1. evaluate the Parent's current Request, transition guards, and relevant
   Observations;
2. accept a valid command and enter or continue the Parent's applicable acting
   transition state;
3. derive and publish commands or Requests for participating Subunits;
4. scan direct Subunits once in explicit registration order;
5. aggregate Subunit status, Conditions, and faults;
6. evaluate the Parent's own state-complete condition and transition to the
   target wait state when complete;
7. publish Parent status and Intents.

An implementation MAY use bounded internal microsteps, but their ordering and
termination limit MUST be deterministic. Internal microsteps MUST NOT cause a
Subunit to receive conflicting commands within one logical scan.

A Subunit owned by a Parent MUST be scanned through that Parent and MUST NOT also
be scanned as a top-level Unit.

## 8. Request and state semantics

A Parent propagates a lifecycle request; a Subunit independently determines its
state. Parent and Subunit states therefore MAY differ while a coordinated
transition is in progress.

A pending Parent Request MAY remain blocked in the Parent's current state while
a guard is false. The Parent MUST NOT issue child commands until the applicable
guard and command-source rules permit the coordinated transition to begin.

The Parent MUST preserve its current acting state until its own state-complete
condition is satisfied. It MUST NOT claim completion solely because requests
were delivered.

Repeating the same outstanding request SHOULD be idempotent. A newer request MAY
replace an older request only according to an explicit priority policy. PackML
abort semantics take precedence where applicable.

## 9. Status and diagnostics

Parent and Subunit status MUST remain independently observable. Aggregation MUST
NOT erase:

- the Subunit's current PackML state and mode;
- its state-complete indication;
- its active Conditions and faults;
- the originating Unit identity;
- the request that caused the coordinated transition.

Parent diagnostics SHOULD expose participating, complete, waiting, degraded, and
failed Subunits for the current transition.

## 10. Peer communication

Peer Units MUST communicate through declared AFS contracts such as Observations,
Memory, Requests, Conditions, and Intents. A peer MUST NOT call or mutate another
peer's internal lifecycle or domain sequencer.

Execution order MUST NOT be used as an undocumented substitute for a declared
data contract.

## 11. Conformance

An implementation conforms to this specification only when automated tests
verify:

- explicit registration and stable order;
- rejection of cycles, duplicate ownership, and multiple parents;
- identical Unit contract for top-level Units and Subunits;
- command or Request propagation without direct state assignment;
- delayed Subunit completion and Parent waiting;
- deterministic scan phases and bounded microsteps;
- Condition and fault attribution and aggregation policies;
- degraded or partial operation when declared;
- independent Parent and Subunit diagnostics;
- distinction between peer data flow and lifecycle ownership.
