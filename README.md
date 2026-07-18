# AFS

AFS is a specification-first project for documenting, validating, and evolving architecture decisions.

This repository contains the first version of the **AFS CLI**, a small command-line tool that helps manage ADRs and validate repository structure.

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
afs validate
afs adr new "Decision title"
```

## Commands

Validate the current directory:

```bash
afs validate
```

Validate another repository without changing directory:

```bash
afs validate /path/to/repository
```

Manage ADRs:

```bash
afs adr list
afs adr new "Decision title"
```

## Development

```bash
make validate
make test
```
