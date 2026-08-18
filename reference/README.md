# AFS Reference Implementation

This directory contains the executable reference architecture for AFS.

The reference implementation is not a disposable demo. It is the living,
runnable example of how an AFS application is assembled:

```text
Application
├── Unit
│   ├── PackML lifecycle
│   └── Domain State Machine
└── Parent Unit
    └── Subunit
        └── PackML lifecycle
```

The Application knows and executes top-level Units. Each Unit owns one
authoritative PackML lifecycle and may own domain State Machines. A Parent owns
and scans its Subunits. Registration is explicit; there is no automatic
discovery or hidden framework magic.

The generic runtime demonstrates:

- required PackML states, Requests, guards, commands, and observable transitions;
- abort precedence, explicit recovery, modes, status, Conditions, and reasons;
- explicit acyclic Unit ownership;
- deterministic Parent/Subunit command propagation and aggregation;
- independent peer Units that exchange data without lifecycle ownership.

## Run it

From the repository root:

```bash
python -m reference.python.afs_reference
```

Expected output:

```text
template-unit: state=COMPLETE value=3 alarm=none
```

Run all tests with:

```bash
python -m unittest discover -s tests -v
```

## Adapt it

Template API
============

The executable reference implementation exposes exactly two public template
identifiers.

Template 01
-----------
Identifier:
    AFS_TEMPLATE_01_UNIT

Purpose:
    Business Unit

Example replacement:
    ChargingUnit


Template 02
-----------
Identifier:
    AFS_TEMPLATE_02_STATE_MACHINE

Purpose:
    Business State Machine

Example replacement:
    ChargingStateMachine
