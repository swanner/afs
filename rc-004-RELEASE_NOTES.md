# RC-004 — Executable reference implementation

Conventional commit:

```text
feat(reference): add executable AFS reference architecture
```

## Included

- Adds a runnable Python reference implementation under `reference/python/afs_reference/`.
- Establishes the explicit `Application → Unit → State Machine` ownership model.
- Keeps Unit registration visible through `app.add_unit(...)`; no decorators, reflection, automatic discovery, or generator workflow is introduced.
- Adds the self-contained `AFS TEMPLATE WORKFLOW` source comment explaining copying, project-wide Search & Replace, required adaptations, optional code, architecture patterns, and testing.
- Limits the executable template surface to exactly two unique identifiers:
  - `AFS_TEMPLATE_UNIT`
  - `AFS_TEMPLATE_STATE_MACHINE`
- Demonstrates parameters, deterministic scans, state transitions, Unit-owned alarm creation, status exposure, and explicit integration.
- Adds six reference implementation tests and preserves all existing CLI tests.
- Updates the root and reference README files with execution and adaptation instructions.

## Verification

```text
PYTHONPATH=src python -m unittest discover -s tests -v
    -> 24 tests passed

python -m reference.python.afs_reference
    -> template-unit: state=COMPLETE value=3 alarm=none

git diff --check
    -> passed

git apply --check rc-004-reference-implementation.patch
    -> passed
```

## Template surface

```text
Unique AFS_TEMPLATE_* identifiers: 2
```

The test suite treats an expanding template surface as a design concern. New template identifiers should be introduced only when the adaptation cannot reasonably be removed through a simpler architecture.
