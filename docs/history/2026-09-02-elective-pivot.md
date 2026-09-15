# 2 September 2026 - capstone elective pivot

## Decision

The FarmPi capstone changed from **Developing Flexible IT Courses** to **Advanced Application Development Concepts**, while retaining **Artificial Intelligence and Data Science**.

This was a genuine change of direction rather than a correction to the historical record. The earlier learning/course work remains valid evidence of the project process and should not be rewritten as though the application-development direction existed from the start.

## New framing

FarmPi is a **prototype/concept demonstrator** for a functional farm-monitoring application. It is not presented as a production-ready farm product.

The capstone work is now structured around the chain:

**need statement -> functional, architectural, and quality requirements -> hardware/software mapping -> architecture diagram -> implementation/integration -> deployment -> testing/evaluation evidence**

The farm-monitoring application itself is therefore central to the capstone evidence rather than being only a vehicle for an embedded learning experience.

## Advanced Application Development Concepts evidence

Relevant evidence includes:

- decomposition into Android client, FastAPI service, MariaDB persistence, ingest, analytics, source/provenance, and model-integration components;
- API contracts and separation of client/server responsibilities;
- native mobile interface design and refinement;
- state management, voice/TTS integration, graph rendering, and user-facing error handling;
- deterministic validation, identity, confirmation, audit, and database behaviour;
- service/deployment integration on Raspberry Pi;
- debugging and iterative repair of integration faults;
- automated and manual functional testing.

## Artificial Intelligence and Data Science evidence

Relevant evidence includes:

- deterministic analytics over stored telemetry;
- graphing and data visualisation;
- semantic interpretation of natural-language requests;
- bounded conversation context;
- local/OpenAI-compatible model integration and compatibility work;
- comparison of model sizes/configurations and their deployment trade-offs;
- provenance and source hierarchy;
- keeping model explanation separate from authoritative farm facts and calculations.

## Consequences for current scope

The earlier embedded course, Learn tab, learner-progress state, and flexible-learning rationale may remain in the code while useful, but they are no longer the primary driver for new work.

Current development should prioritise a coherent functional application: reliable farm-data access, clear mobile interaction, graphs, AI/data integration, recovery from unclear requests, useful error states, integration testing, and technically defensible architecture.

The current governing document is [capstone-governance.md](../capstone-governance.md).
