# AFS Architecture

The Architecture Framework Standard (AFS) separates runtime concerns, application orchestration, and business behavior into distinct responsibilities.

## Overview

```text
Platform
    │
    ▼
Application
    │
    ▼
Unit
    │
    ▼
Sequencer
```

## Platform

The Platform provides the runtime environment for an AFS application.

Responsibilities:

- Starts the Application.
- Provides platform-specific services.
- Integrates the application with the underlying runtime.

Examples of target platforms include Homey, Raspberry Pi, Home Assistant, and PLC runtimes.

Platform is currently an architectural concept rather than a standardized interface or implementation.

## Application

The Application coordinates the business solution.

Responsibilities:

- Owns and executes Units.
- Coordinates application behavior.
- Keeps platform-specific concerns outside the application logic.

## Unit

A Unit encapsulates a business capability.

Responsibilities:

- Represents a focused part of the application.
- Owns its Sequencer.
- Interacts with the target platform where required.

## Sequencer

A Sequencer executes the behavior of its owning Unit.

Responsibilities:

- Implements the Unit's execution flow.
- Performs the work associated with the Unit.
- Keeps execution behavior separate from application orchestration.

## Current Scope

This document describes the current AFS architecture.

Concepts planned for future versions are documented separately and are not presented here as existing architecture.