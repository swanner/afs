# New AFS Project

This project was created with the Architecture File Standard (AFS).

It contains a runnable reference implementation that can be replaced with your own application while preserving the AFS architecture.

## Run the Reference Application

```bash
PYTHONPATH=src python -m afs_reference
```

Expected output:

```text
template-unit: state=COMPLETE value=3 alarm=none
```

## Architecture

AFS separates application orchestration, business logic and behaviour.

```text
Application
    │
    ▼
Unit
    │
    ▼
Sequencer
```

- The **Application** owns and executes Units.
- A **Unit** owns its **Sequencer** and interacts with the target platform.
- The **Sequencer** executes the Unit's behavior for the current application state.

## Project Structure

```
src/
    afs_reference/
specification/
    adr/
```

## Next Steps

1. Explore the reference implementation.
2. Create your own Units and Sequencers.
3. Record important architectural decisions in `specification/adr`.
4. Replace the reference application with your own logic.