# Changelog

All notable changes to AFS will be documented in this file.

## Unreleased

### Added

- Validation of an explicitly supplied repository path.
- Direct unit tests for individual validation rules.
- Hardened declarative `PackMLMachine` reference runtime with pure component
  aggregation and bounded internal microsteps.
- Canonical attributable alarms with deterministic ordering and explicit
  `ABORT`, `HOLD`, and `SUSPEND` responses.
- Fail-closed transient-state timeout handling through `SYSTEM_FAILURE`.
- Strict timestamped snapshot validation and deterministic acknowledged recovery.

### Changed

- Validator logic is separated from terminal output.
- Tests no longer change the process working directory.
- Expected validation failures are no longer printed during the test suite.

## 0.1.0

- Initial AFS repository structure.
- Architecture Decision Record profile.
- Repository and ADR validator.
- ADR creation and listing commands.
- AFS Charter.
