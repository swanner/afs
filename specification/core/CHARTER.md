# AFS Charter

- Status: Draft
- Date: 2026-07-18

## Purpose

AFS is an open specification for describing, validating, and exchanging architecture decisions.

AFS begins with Architecture Decision Records. Broader architecture knowledge may be considered later only when practical use justifies it.

## Goals

AFS aims to be:

- simple to understand;
- human-readable by default;
- machine-validatable;
- implementation-independent;
- explicitly versioned;
- stable enough for long-term use;
- small enough for lightweight tooling.

## Non-goals

AFS is not:

- a general-purpose modeling language;
- a diagram format;
- a programming language;
- a project-management system;
- a requirements-management platform;
- a replacement for engineering judgment.

## Principles

### Specification before implementation

Normative behavior is defined by the specification. Tools implement the specification but do not redefine it.

### Human-readable by default

A person should be able to read and review an AFS document without specialized software.

### Machine-validatable where practical

Rules should be precise enough for consistent automated validation.

### Small, stable core

The core should contain only concepts needed by most users.

### Backward compatibility

Compatible evolution is preferred whenever it does not preserve a clear design mistake.

### Explicit extensions

Extensions must not silently change core semantics.

### Pragmatism

AFS solves real engineering problems. Every feature must justify its existence.

## Normative and informative content

Documents under `specification/` are normative unless they explicitly state otherwise.

Documents under `docs/`, `examples/`, and similar supporting directories are informative. They may explain or demonstrate AFS but do not define conformance.

If informative content conflicts with a normative specification, the normative specification takes precedence.

## Initial scope

The initial scope of AFS is deliberately narrow:

- repository conventions;
- Architecture Decision Records;
- validation rules;
- a small reference CLI.

Features outside this scope should be deferred until the initial standard is useful, documented, and stable.
