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

Open `python/afs_reference/unit.py` first. Its `AFS TEMPLATE WORKFLOW` comment
explains the complete copy, Search & Replace, adaptation, optional-code cleanup,
and test workflow directly in the source code.

The template surface is intentionally small. RC-004 contains exactly two unique
application placeholders:

```text
AFS_TEMPLATE_UNIT
AFS_TEMPLATE_STATE_MACHINE
```

Every additional placeholder must be justified. Prefer simplifying the
architecture over expanding the template surface.

Reference code follows the specification and must not silently redefine it.
