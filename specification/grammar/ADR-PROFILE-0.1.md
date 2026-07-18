# AFS ADR Profile 0.1

- Status: Draft
- Version: 0.1.0
- Date: 2026-07-18

## 1. File name

An ADR file name MUST use this form:

```text
ADR-NNNN-slug.md
```

Where:

- `NNNN` is a four-digit decimal number;
- `slug` contains one or more lowercase ASCII letters, digits, or hyphens;
- the file extension is `.md`.

Example:

```text
ADR-0003-use-yaml-as-exchange-format.md
```

## 2. Heading

The first level-one heading MUST use this form:

```text
# ADR-NNNN: Title
```

The heading number MUST equal the number in the file name.

## 3. Metadata

The ADR MUST contain these metadata entries directly below the heading:

```text
- Status: Proposed
- Date: YYYY-MM-DD
```

`Status` MUST be one of:

- `Proposed`
- `Accepted`
- `Rejected`
- `Deprecated`
- `Superseded`

`Date` MUST use the ISO 8601 calendar-date form `YYYY-MM-DD`.

A superseded ADR SHOULD identify its replacement.

## 4. Required sections

An ADR MUST contain these level-two sections:

```text
## Context
## Decision
## Consequences
## Alternatives considered
```

Sections MAY contain additional subsections.

## 5. Immutability

An accepted ADR SHOULD NOT be rewritten to hide the original decision.

A later decision SHOULD supersede or amend it through a new ADR.
