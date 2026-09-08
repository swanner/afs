# AFS

AFS is a specification-first project for documenting, validating, and evolving architecture decisions.

This repository contains the first version of the **AFS CLI**, a small command-line tool that helps manage ADRs and validate repository structure.

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
afs init /path/to/repository
afs validate /path/to/repository
afs adr new "Decision title"
```

## Commands

Initialize a minimal valid AFS repository:

```bash
afs init
```

Initialize another directory:

```bash
afs init /path/to/repository
```

Existing files are preserved.

Validate the current directory:

```bash
afs validate
```

Validate another repository without changing directory:

```bash
afs validate /path/to/repository
```

Validation checks required paths, ADR filenames and metadata, duplicate or missing ADR numbers, numbering from `ADR-0001`, and unexpected files in `specification/adr`.

Manage ADRs:

```bash
afs adr list
afs adr new "Decision title"
```

## Reference implementation

Run the current executable AFS reference implementation:

```bash
python -m reference.python.afs_reference
```

It demonstrates the declarative, component-based `PackMLMachine` as the
preferred current lifecycle runtime for new implementations. An Application
scans a Unit, which supplies immutable observations, and small pure components
return `SC`, alarms, and outputs. The machine alone owns transitions through the
explicit `_apply_state` switch.

The command-based `PackMLLifecycle` is retained under
`reference/python/afs_reference/legacy/` as the 0.1 compatibility adapter for
the published 0.1 examples, including Parent/Subunit composition. See
`reference/README.md` for the module map and safety contract.

## Development

```bash
make validate
make test
```
