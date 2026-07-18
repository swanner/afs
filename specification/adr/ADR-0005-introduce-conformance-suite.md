# ADR-0005: Introduce the Conformance Suite

- Status: Accepted
- Date: 2026-07-18

## Context

AFS should be implementable in multiple programming languages.

## Decision

Introduce a language-independent conformance suite containing valid and invalid examples together with expected outcomes.

## Consequences

Reference implementations and third-party implementations can verify identical behaviour.

## Alternatives considered

Relying only on unit tests was rejected because unit tests are implementation-specific.
