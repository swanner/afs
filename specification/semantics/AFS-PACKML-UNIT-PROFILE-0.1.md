# AFS PackML Unit Profile 0.1

- Status: Draft
- Version: 0.1.0
- Date: 2026-08-18
- Decision: `ADR-0006`
- Normative basis: `ISA-TR88.00.02-2022`

## 1. Scope

This profile defines the operational lifecycle required of every AFS Unit. It
adopts PackML state, mode, command, and transition semantics so that Units use a
common and recognizable lifecycle.

Conformance to this profile is **AFS PackML Unit Profile conformance**. It does
not by itself claim complete PackML conformance. PackML interface elements not
defined here, including its broader command, status, and administration data
model, are outside version 0.1.

## 2. Conformance language

The key words **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, and **MAY**
indicate requirement levels.

## 3. Lifecycle authority

Every AFS Unit MUST expose one authoritative PackML lifecycle. An implementation
MAY represent that lifecycle with one state machine or with nested and
mode-dependent state machines.

The Application MAY request lifecycle changes and scan Units. It MUST NOT assign
a Unit's lifecycle state directly. The Unit owns its state, transition guards,
conditions, alarms, and domain sequencers.

Only the authoritative lifecycle may describe whether the Unit is stopped,
ready, executing, suspended, complete, or aborted. Domain state MUST NOT create a
parallel operational lifecycle.

## 4. Initialization and recovery

A newly created Unit that has no restored lifecycle state MUST initialize in
`STOPPED`, unless a detected fault requires initialization in `ABORTED`.

A valid persisted state MAY be restored only under an explicit recovery policy
that proves the state remains safe and consistent with current Observations. An
unknown, unsupported, or unsafe restored state MUST NOT be treated as valid. The
Unit MUST expose a fault and enter a documented safe recovery path.

Automatic startup policy MAY create lifecycle Requests. It MUST NOT bypass the
required PackML commands or assign the startup target state directly.

## 5. Required state profile

Every Unit MUST support these PackML states in every operational mode declared
conformant to this profile:

| State | AFS profile meaning |
|---|---|
| `STOPPED` | The Unit is stopped and cannot start until reset. |
| `IDLE` | Reset is complete and the Unit is ready to receive a start request. |
| `EXECUTE` | The Unit performs the behaviour defined by its current mode. |
| `ABORTED` | A fault or abort has brought the Unit to a rapid safe stop; explicit recovery is required. |

These four states are the AFS minimum profile. Their presence alone does not
constitute complete PackML conformance.

## 6. Requests, guards, and commands

An AFS lifecycle Request expresses a desired lifecycle outcome and MAY remain
pending while a transition guard is false. A PackML command is the discrete
action that initiates a PackML transition from a valid source state.

A Unit MUST evaluate the applicable guard before issuing or accepting a command.
While a Request is pending and blocked, the Unit MUST remain in its current
PackML state and SHOULD expose the blocking reason. It MUST issue the command
when the guard becomes true unless the Request has been withdrawn or superseded
according to an explicit priority policy.

For example, a Charging Unit may expose `START_REQUESTED` while remaining in
`IDLE` with reason `SOLAR_UNAVAILABLE`. The Unit issues `START` only after solar
availability satisfies the start guard.

## 7. Required commands and minimum transitions

Every Unit MUST implement the following PackML commands and source-state
semantics:

- `RESET` is valid in `STOPPED` and requests transition toward `IDLE`;
- `START` is valid in `IDLE` and requests transition toward `EXECUTE`;
- `STOP` is valid in `IDLE`, `EXECUTE`, and every supported non-abort branch
  from which PackML permits a controlled stop, and requests transition toward
  `STOPPED`;
- `ABORT` takes precedence in every state other than `ABORTING` and `ABORTED`
  and requests a rapid safe transition toward `ABORTED`;
- `CLEAR` is valid in `ABORTED` and requests recovery toward `STOPPED`.

A valid command MUST initiate its defined transition. A command that is invalid
in the current state MUST produce an explicit rejection while leaving the
current state unchanged. A Unit MUST NOT silently ignore or reinterpret an
invalid command.

Repeated delivery of the active request SHOULD be idempotent. A Unit MUST NOT
report a target state before the conditions required by that state are true.

## 8. Transition states

A Unit MUST use the applicable PackML transition state when entering or leaving
a required or optional wait state requires observable work, external
confirmation, or more than one scan.

The standard transition states include:

- `RESETTING`, `STARTING`, `STOPPING`, `ABORTING`, and `CLEARING`;
- `HOLDING` and `UNHOLDING`;
- `SUSPENDING` and `UNSUSPENDING`;
- `COMPLETING`.

A Unit MAY omit a transition state when that state is declared unsupported and
the corresponding transition is immediate. It MUST NOT omit a transition state
to hide unfinished work or missing confirmation.

An acting transition state MUST remain active until its state-complete condition
is true or another valid PackML transition, such as abort, takes precedence.

## 9. Optional PackML branches

A Unit MUST declare which optional states and commands it supports. When the
following semantics occur, the corresponding PackML branch MUST be used instead
of an application-specific lifecycle state:

| Branch | Required use |
|---|---|
| `HOLDING` → `HELD` → `UNHOLDING` | An internal Unit condition interrupts execution and operator or internal recovery is required. |
| `SUSPENDING` → `SUSPENDED` → `UNSUSPENDING` | An external process condition interrupts execution and execution resumes when that condition clears. |
| `COMPLETING` → `COMPLETE` | The process associated with the current mode reaches its defined end. |

Unsupported states MUST NOT be renamed, repurposed, or used with different
semantics.

## 10. Modes

Every Unit MUST declare at least one PackML mode and its supported states and
commands. The current mode MUST be observable.

A mode changes the operational strategy of the Unit. A permission source,
override, configuration option, or domain value MUST NOT be represented as a mode
unless it actually changes that operational strategy.

A mode change MUST follow an explicit, documented policy. It MUST NOT silently
invalidate the current state.

## 11. Domain sequencers

A Unit MAY own zero or more domain sequencers. A domain sequencer represents
process values or application progression that PackML does not represent.

For example, a Solar Unit may remain in `EXECUTE` while a solar availability
sequencer moves through `BELOW`, `WAIT_ABOVE`, `ABOVE`, and `WAIT_BELOW`.

An implementation MUST classify every state-like value as one of:

- PackML lifecycle state;
- domain sequencer state;
- transition guard;
- Observation;
- Condition or fault;
- diagnostic reason.

A guard or calculation MUST NOT be exposed as a lifecycle state merely to make
an evaluation step visible.

## 12. Status contract

Every Unit MUST expose at least:

- Unit identity;
- current PackML state;
- current PackML mode;
- state-complete indication;
- supported states, commands, and modes;
- active lifecycle request or command, when present;
- active Conditions and fault information;
- an optional diagnostic reason.

A diagnostic reason MAY explain why a Unit is `IDLE`, `SUSPENDED`, or another
state. It MUST NOT redefine the meaning of that state.

## 13. Conformance

An implementation conforms to this profile only when automated tests verify:

- ownership and direct-assignment prohibition;
- initialization and restored-state recovery;
- all required states and commands;
- distinction between pending Requests, transition guards, and commands;
- valid and invalid minimum transitions;
- state-complete behaviour across multiple scans;
- abort precedence and explicit clear recovery;
- declaration and semantics of every optional branch used;
- mode and supported-state reporting;
- separation of PackML lifecycle from domain sequencers;
- status, Condition, fault, and reason exposure;
- safe handling of an unknown restored state.

Claims of complete PackML conformance require independent verification against
the complete applicable PackML specification and are outside this profile.
