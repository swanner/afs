# ADR-0001: AFS is a specification

- Status: Accepted
- Date: 2026-07-18

## Context

AFS needs a clear identity before implementation details are introduced. Without that boundary, the project could become a loosely connected collection of tools and conventions.

## Decision

AFS is primarily a specification.

Tools, reference implementations, validators, generators, and documentation sites support the specification but do not define it independently.

Normative behavior must be described in versioned specification documents. Tool behavior should be traceable back to those documents.

## Consequences

The project remains implementation-neutral. Changes to normative behavior require explicit specification changes and, where architecture-significant, an ADR. The CLI can evolve without silently redefining AFS.

## Alternatives considered

Treating AFS primarily as a CLI or framework was rejected because it would couple the project identity to one implementation and programming language.
