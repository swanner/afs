# ADR-0006: Require a PackML Lifecycle for Every AFS Unit

- Status: Accepted
- Date: 2026-08-18

## Context

AFS Units need a common operational model that makes otherwise different
applications understandable, diagnosable, and predictable. A Unit-specific
lifecycle vocabulary such as `DISABLED`, `WAITING`, `RUNNING`, or `DONE` creates
parallel meanings and forces every application to define basic operational
behaviour again.

PackML, currently specified by ISA-TR88.00.02-2022, already defines machine and
Unit states, commands, modes, and transition semantics. AFS previously
demonstrated PackML as an additional status alongside application state. That
does not gain the structural benefit of the standard and permits the application
lifecycle to remain authoritative.

Domain state is still necessary. For example, solar availability can move
through hysteresis states while the Unit that evaluates it remains operational.
AFS therefore needs a firm boundary between operational lifecycle and domain
sequencing.

## Decision

Every AFS Unit MUST own one authoritative PackML lifecycle. The lifecycle is the
authoritative representation of the Unit's operational state. AFS does not
prescribe whether an implementation represents that lifecycle internally as one
state machine or as several nested and mode-dependent state machines.

The AFS PackML Lifecycle Profile MUST require every Unit to support the stable
states `STOPPED`, `IDLE`, `EXECUTE`, and `ABORTED`. This is an AFS minimum profile
and is not a claim that those four states alone constitute complete PackML
conformance. A Unit MUST implement the PackML commands and transition states
needed by its supported behaviour. When a PackML branch such as hold, suspend,
complete, stop, or abort describes the Unit's behaviour, the Unit MUST use the
PackML states and transition semantics for that branch rather than introduce an
application-specific equivalent.

A Unit MAY declare PackML states unsupported when their semantics do not occur
in that Unit. Its supported state set, modes, commands, and transition guards
MUST be explicit and testable. Unsupported states MUST NOT be repurposed.

PackML state and domain state are separate dimensions:

- PackML state describes whether and how the Unit is operating.
- Domain sequencers describe process values or application-specific progression
  that PackML does not represent.

A domain sequencer MUST NOT duplicate an operational condition already expressed
by PackML. Internal guards and calculations MUST NOT be exposed as lifecycle
states merely to make evaluation steps visible.

PackML modes MUST retain operational meaning. An application strategy, override,
permission source, or configuration option MUST NOT be represented as a PackML
mode unless it actually changes how the Unit is operated in the PackML sense.

Conformance to the AFS PackML Lifecycle Profile does not by itself claim complete
PackML conformance. PackML interface elements outside the AFS lifecycle profile,
including its broader command, status, and administration data model, remain
outside the initial profile unless a later version explicitly adopts them.

Every Unit status MUST expose at least:

- current PackML state;
- current PackML mode;
- state-complete indication;
- active conditions and fault information;
- an optional reason that explains the current state without redefining it.

The Unit owns its lifecycle, guards, domain sequencers, conditions, and alarms.
The Application registers and scans Units but MUST NOT directly assign their
states.

## Consequences

All AFS Units share a recognizable lifecycle and can use common diagnostics,
visualization, command handling, persistence, and transition tests.

Applications will contain fewer parallel lifecycle state machines. Existing
application states must be classified as PackML state, domain state, guard,
observation, condition, or reason before migration.

Some simple Units will use only the required stable states. Other Units will use
additional PackML branches when those states carry real operational meaning.

Adopting PackML as the authoritative lifecycle increases implementation work and
requires precise transition semantics. This cost is accepted because PackML is
intended to structure every Unit, not merely demonstrate that PackML terminology
exists somewhere in an application.

This decision MUST be expressed by a versioned normative specification named
`AFS-PACKML-UNIT-PROFILE-0.1`. The AFS reference implementation and conformance
suite must be updated to verify that profile before application implementations
claim AFS PackML Lifecycle Profile conformance.

## Alternatives considered

Keeping PackML as an optional annotation was rejected because application state
would remain authoritative and Unit behaviour would not become more uniform.

Defining an AFS-specific lifecycle was rejected because it would duplicate a
mature industry standard and create new terminology for established semantics.

Requiring every PackML state in every Unit was rejected because PackML permits
state selection and many Units do not have meaningful hold, suspend, or complete
behaviour. States that are used must retain their standard meaning.

Claiming complete PackML conformance from lifecycle states alone was rejected
because PackML also defines interface and data-model requirements that the
initial AFS lifecycle profile does not adopt.
