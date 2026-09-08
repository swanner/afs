# AFS Reference Implementation

This directory contains the living executable reference for AFS. The current
reference is the declarative, component-based `PackMLMachine`; it is the
preferred current lifecycle runtime for new implementations.

## Current architecture

```text
Application
└── Unit
    ├── PackMLMachine (authoritative lifecycle)
    └── pure components
        └── ComponentResult(SC, alarms, outputs)
```

The Application scans explicitly registered Units in order. Each Unit owns one
`PackMLMachine`, acquires observations, and passes them into `scan()`. Registered
components are small pure functions: each receives the same immutable snapshot,
input mapping, and timestamp for an evaluation pass. Components report evidence;
they never assign PackML state or issue private transition commands.

The machine aggregates `SC`, canonicalizes attributable alarms, preserves the
`ABORT` → `HOLD` → `SUSPEND` priority, enforces bounded internal microsteps and
timeouts, and validates complete persisted snapshots before scanning. Callers
that apply effects should atomically persist `result.snapshot` first.

## Current module map

- `packml_states.py` — `PackMLState`, explicit legal edges, and state groups;
- `packml_models.py` — frozen snapshots, contexts, alarms, and component results;
- `packml_validation.py` — alarm normalization and strict snapshot validation;
- `packml_orchestration.py` — `scan()` and the central explicit `_apply_state`
  switch that handles every PackML state;
- `packml_machine.py` — stable public imports for the current runtime;
- `unit.py` — the executable Unit and pure component adaptation example.

The legal transition graph is deliberately literal. No generated transition
table dispatches behavior: `_apply_state` remains the readable source of
transition priorities and state-specific conditions.

Minimal use:

```python
from reference.python.afs_reference import PackMLMachine, component_result


def work(context):
    return component_result(
        SC=context.input.get("complete", False),
        outputs={"state": context.machine.state.value},
    )


machine = PackMLMachine(unit_id="example", now=0)
machine.register_component("work", work)
result = machine.scan(
    operation_requested=True,
    input={"complete": False},
    now=1,
)

# Persist before applying effects derived from component outputs.
persist(result.snapshot.to_dict())
```

## 0.1 compatibility adapter under `legacy/`

`reference/python/afs_reference/legacy/` retains the command-based
`PackMLLifecycle` as the 0.1 compatibility adapter for the published 0.1
examples. Its Unit, State Machine, and Parent/Subunit examples remain executable,
and their conformance and scenario tests continue to verify request, guard,
command, mode, and composition behavior.

Parent/Subunit composition remains part of the accepted AFS direction and the
draft AFS Unit Composition specification. Its executable reference currently
remains in the command-based compatibility adapter; `PackMLMachine` does not yet
provide a declarative Parent/Subunit adapter.

The compatibility adapter is not the preferred runtime for new implementations.
It does not provide hardened snapshots or `SYSTEM_FAILURE`, and a Unit must
never use it alongside `PackMLMachine` as a second lifecycle authority. Accepted
ADRs and draft specifications remain unchanged.

## Run it

From the repository root, run the current reference:

```bash
python -m reference.python.afs_reference
```

Expected output:

```text
template-unit: state=COMPLETE value=3 alarm=none
```

The command-based compatibility example remains executable separately:

```bash
python -m reference.python.afs_reference.legacy
```

Run all current and legacy tests with:

```bash
python -m unittest discover -s tests -v
```

## Adapt it

The current executable reference exposes two template identifiers:

- `AFS_TEMPLATE_01_UNIT` — replace with the business Unit name, such as
  `ChargingUnit`;
- `AFS_TEMPLATE_02_COMPONENT` — replace with the pure business component name,
  such as `charging_component`.

After replacing those identifiers, review every `AFS REQUIRED ADAPTATION`,
`AFS OPTIONAL`, and `AFS PATTERN` marker in the current top-level reference
package.
