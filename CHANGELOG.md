# Changelog

All notable changes to AFS will be documented in this file.

## Unreleased

### Added

- Authority and effect contracts for canonical action projections, current-state
  revalidation, asynchronous physical confirmation, stricter declared fail-safe
  policies, and ambiguous-outcome reconciliation.
- ADR-0009 documenting the single-authority boundary for clients, effect
  executors, observations, and transport concerns.
- Validation of an explicitly supplied repository path.
- Direct unit tests for individual validation rules.
- Hardened declarative `PackMLMachine` reference runtime with pure component
  aggregation and bounded internal microsteps.
- Canonical attributable alarms with deterministic ordering and explicit
  `ABORT`, `HOLD`, and `SUSPEND` responses.
- Fail-closed transient-state timeout handling through `SYSTEM_FAILURE`.
- Strict timestamped snapshot validation and deterministic acknowledged recovery.

### Changed

- The reference architecture documentation now distinguishes lifecycle
  authority, effect requests, physical observations, and client projections
  without changing `PackMLMachine` behavior.
- Validator logic is separated from terminal output.
- Tests no longer change the process working directory.
- Expected validation failures are no longer printed during the test suite.
- The declarative `PackMLMachine` is the current executable reference and is
  split into explicit state, model, validation, and scan-orchestration modules.
- The command-based `PackMLLifecycle` is retained under `legacy/` as the 0.1
  compatibility adapter for the published 0.1 examples. It currently hosts the
  executable Parent/Subunit composition reference.

## 0.1.0

- Initial AFS repository structure.
- Architecture Decision Record profile.
- Repository and ADR validator.
- ADR creation and listing commands.
- AFS Charter.
