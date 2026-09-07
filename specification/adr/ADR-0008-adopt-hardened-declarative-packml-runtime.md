# ADR-0008: Adopt a Hardened Declarative PackML Runtime

- Status: Accepted
- Date: 2026-09-07

## Context

The first AFS PackML reference runtime modeled explicit requests, guards, and
commands. Production use in `swanner/afs-homey` exposed additional requirements
at process restart and failure boundaries: several pure concerns must contribute
to one lifecycle decision, alarms must remain attributable and deterministic,
unfinished transitions must not wait forever, and persisted transient state must
not be accepted without its safety context.

Application-specific lifecycle orchestration would create competing transition
logic outside the Unit. Lenient snapshot recovery would allow a corrupt or
semantically impossible state to influence actuators before the error is known.

## Decision

AFS adopts a declarative component-based PackML machine as the hardened runtime
profile. The Unit supplies an operation request, an acknowledgement request,
immutable observations, and an explicit scan timestamp. Registered pure
components receive the same immutable machine snapshot and observations for each
evaluation pass. They return only state-complete (`SC`), alarms, and outputs.

The machine alone owns PackML transitions. It aggregates `SC`, canonicalizes and
sorts attributable alarms, reconciles alarm changes before using outputs, and
executes bounded internal microsteps. External callers cannot submit private
PackML commands or assign state.

Alarm responses use the priority `ABORT`, `HOLD`, then `SUSPEND`. A transient
state whose aggregate `SC` remains false beyond the configured positive timeout
enters the AFS extension state `SYSTEM_FAILURE`. The machine records the failed
transient state and a canonical `PackMLMachine/SC_TIMEOUT` alarm. Recovery from
`SYSTEM_FAILURE` requires aggregate `SC` and explicit acknowledgement, and then
passes through `ABORTING` and `ABORTED` before clearing to `STOPPED`.

Persisted snapshots include Unit identity, state, state-entry timestamp,
canonical alarms, abort reason, and failed-from state. Restoration requires an
explicit current timestamp. Unknown states, future timestamps, malformed alarms,
or semantically impossible `SYSTEM_FAILURE` provenance fail closed before a Unit
scan.

`STOPPED`, `COMPLETE`, `ABORTED`, and `SYSTEM_FAILURE` are commit boundaries. A
scan may reach one of them through internal microsteps but must not traverse its
normal outgoing transition in the same scan. The explicitly acknowledged
`SYSTEM_FAILURE` recovery path is the documented exception required to reach a
safe cleared state deterministically.

The existing command-based `PackMLLifecycle` remains a compatibility adapter for
the 0.1 request/command examples and hierarchical composition. It cannot claim
the hardened snapshot or `SYSTEM_FAILURE` capabilities. A Unit chooses one
authoritative lifecycle runtime; it must never run both for the same Unit.

## Consequences

The Python reference now expresses the production-tested semantics independently
of Homey and JavaScript. Identical observations produce deterministic component,
alarm, transition, and snapshot results. Restart validation is strict enough to
reject impossible state before effects occur.

Implementations must persist a complete snapshot atomically or provide an
equivalent validated envelope. They must keep external effects outside pure
component evaluation and commit the resulting lifecycle state before acting on
it.

The AFS extension state does not claim to be a PackML state defined by
ISA-TR88.00.02. It is an explicit fail-closed runtime boundary around PackML
transient states.

## Alternatives considered

Reconstructing missing snapshot context from current observations was rejected
because it can silently change event identity and safety provenance.

Letting components issue transitions was rejected because registration order
would become lifecycle authority.

Treating a transition timeout as an ordinary `ABORT` was rejected because it
would hide whether the Unit completed the safety work required to reach
`ABORTED`.

Removing the command adapter immediately was rejected because it would break the
published 0.1 examples without improving the hardened runtime semantics.
