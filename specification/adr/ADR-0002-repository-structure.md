# ADR-0002: Organize AFS by responsibility

- Status: Accepted
- Date: 2026-07-18

## Context

AFS needs a repository structure that separates normative specification content, explanatory documentation, examples, tooling, tests, and reference implementations.

Without clear boundaries, implementation details could unintentionally become normative and contributors could place content inconsistently.

## Decision

The repository is organized into these primary areas:

- `specification/` for normative and supporting specification material
- `reference/` for reference implementations and implementation-neutral reference material
- `tools/` for project tooling
- `tests/` for automated verification
- `examples/` for focused examples
- `docs/` for tutorials and explanatory documentation
- `.github/` for repository automation and contribution workflows

Within `specification/`, content is divided into `core`, `grammar`, `semantics`, `validation`, `extensions`, and `adr`.

## Consequences

The normative boundary is explicit.

Tools and reference implementations can evolve without silently redefining AFS.

The structure introduces more directories early, but each directory has a clear responsibility.

## Alternatives considered

A single `docs/` tree was rejected because it would blur the difference between normative specification content and explanatory documentation.

A monolithic root-level layout was rejected because it would become difficult to navigate as the project grows.
