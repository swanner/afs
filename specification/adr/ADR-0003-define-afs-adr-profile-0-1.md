# ADR-0003: Define the AFS ADR Profile 0.1

- Status: Accepted
- Date: 2026-07-18

## Context

AFS currently validates a small set of repository and ADR conventions, but those conventions are not yet expressed as a versioned normative profile.

Without a documented profile, the CLI implementation could become the accidental source of truth.

## Decision

AFS 0.1 defines a Markdown-based Architecture Decision Record profile.

The profile standardizes the file name, heading, metadata, lifecycle status, and required sections of an ADR.

The validator implements explicit validation rule identifiers defined under `specification/validation/`.

## Consequences

AFS gains its first concrete, independently documented format.

Existing ADRs remain compatible with the profile.

Future syntax changes require a versioned specification change rather than an undocumented CLI modification.

## Alternatives considered

A custom language was rejected for version 0.1 because Markdown is readable, widely supported, and sufficient for establishing the initial semantics.

Unstructured Markdown was rejected because it cannot be validated consistently.
