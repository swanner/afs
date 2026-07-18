# AFS

AFS is a specification-first project for documenting, validating, and evolving architecture decisions.

This repository contains the first version of the **AFS CLI**, a small command-line tool that helps manage ADRs and validate the repository structure.

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
afs validate
afs adr new "Decision title"
```

## Commands

```bash
afs validate
afs adr list
afs adr new "Decision title"
```

## Development

```bash
python -m unittest discover -s tests
```
