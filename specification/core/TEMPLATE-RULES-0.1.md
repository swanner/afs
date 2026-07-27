# TEMPLATE RULES 0.1

## Status

Draft

## Purpose

This document defines the rules governing the template surface of the AFS
Reference Implementation.

The objective is to provide a stable customization API while keeping the
reference implementation intentionally small.

---

## TR-001 — Minimal Template Surface

The reference implementation shall expose only the template identifiers required
for mandatory application customization.

Every additional template identifier shall be justified.

---

## TR-002 — Stable Template Identifiers

Template identifiers form part of the public customization API.

Once published, an identifier shall not be renamed.

---

## TR-003 — Stable Numbering

Template numbers shall:

- start at 01
- be unique
- never be reused
- remain stable across releases

Retired numbers shall remain retired.

---

## TR-004 — Self-Documenting Templates

Every template identifier shall be documented in the Reference README.

Documentation shall describe:

- purpose
- replacement intent
- example replacement

---

## TR-005 — Permanent Architecture Comments

Architecture comments marked

```
AFS TEMPLATE
```

and

```
AFS PATTERN
```

are permanent documentation.

They shall remain after customization.

---

## TR-006 — Temporary Work Markers

The markers

```
AFS REQUIRED ADAPTATION
```

and

```
AFS OPTIONAL
```

identify customization work.

They may be removed once the project has been adapted.

---

## TR-007 — Architecture Verification

The reference implementation shall contain automated tests verifying:

- template identifier syntax
- numbering
- documentation consistency
- template surface

---

## TR-008 — Specification Consistency

The specification, reference implementation and automated tests shall remain
consistent.

A change to one shall be reflected in the others.