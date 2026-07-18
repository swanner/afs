# ADR-0004: Adopt the AFS Charter

- Status: Accepted
- Date: 2026-07-18

## Context

AFS has an initial specification, ADR profile, validator, and repository structure.

The project also needs a concise statement of purpose, scope, principles, and non-goals so that future changes can be evaluated consistently.

Without such a charter, AFS could expand into unrelated areas before its initial ADR-focused standard is mature.

## Decision

AFS adopts `specification/core/CHARTER.md` as the governing project charter.

The initial scope remains deliberately narrow: repository conventions, Architecture Decision Records, validation rules, and a small reference CLI.

Normative and informative documents are explicitly distinguished.

## Consequences

Future proposals can be evaluated against a stable set of goals and non-goals.

The project is less likely to accumulate premature features.

Expanding AFS beyond ADRs will require clear practical justification and an explicit specification decision.

## Alternatives considered

Relying only on the README was rejected because the README is introductory and may change frequently.

Deferring the charter was rejected because scope discipline is most valuable before significant expansion begins.
