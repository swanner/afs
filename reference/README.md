# AFS Reference Implementation

This directory contains the executable reference architecture for AFS.

The reference implementation is not a disposable demo. It is the living,
runnable example of how an AFS application is assembled:

```text
Application
└── Unit
    └── State Machine
```

The Application knows and executes Units. Each Unit owns its State Machine.
Registration is explicit; there is no automatic discovery or hidden framework
magic.

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
