# AFS Core Specification 0.1

- Status: Draft
- Version: 0.1.0
- Date: 2026-07-18

## 1. Scope

AFS is a specification-first format for documenting, validating, and evolving architecture decisions.

Version 0.1 defines the repository model and the Architecture Decision Record profile used by an AFS repository.

## 2. Conformance language

The key words **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, and **MAY** indicate requirement levels.

## 3. AFS repository

An AFS repository MUST contain:

- a root `README.md`;
- a root `LICENSE`;
- a root `pyproject.toml`;
- a `specification/adr/` directory.

An AFS repository MAY contain tools, examples, explanatory documentation, tests, and reference implementations.

Normative requirements belong under `specification/`.

## 4. Architecture Decision Records

Each architecture-significant decision MUST be represented by one ADR file under `specification/adr/`.

Each ADR MUST conform to the AFS ADR Profile 0.1.

ADR numbers MUST be unique within a repository.

## 5. Validation

A conforming validator MUST report violations of MUST and MUST NOT requirements as errors.

A validator MAY report additional warnings and informational findings.

A repository is valid when validation completes without errors.

## 6. Evolution

Normative changes MUST be versioned.

Architecture-significant changes to AFS itself SHOULD be documented through an ADR before implementation behavior is changed.
