# FarmPi documentation

This directory describes the current FarmPi implementation and capstone direction. The repository code and configuration remain the final technical authority; update the matching document whenever a component boundary, deployment command, API contract, user interaction, data rule, or architectural requirement changes.

The current electives are **Advanced Application Development Concepts** and **Artificial Intelligence and Data Science**. Earlier flexible-learning/course material is retained as historical development evidence but is no longer a current design authority.

## Current documentation

| Document | Purpose |
|---|---|
| [Capstone direction and governance](capstone-governance.md) | Current elective direction, requirements/evidence chain, scope gate, and application-development priorities. |
| [Architecture](architecture.md) | Components, request flow, authority boundaries, model integration, and repository structure. |
| [Raspberry Pi deployment](raspberry-pi-deployment.md) | Installation, configuration, systemd, Caddy, MariaDB, update process, backup, and troubleshooting. |
| [Android client](android-client.md) | Build requirements, HTTPS trust, mobile interaction, voice/TTS, charts, settings, state, and API consumption. |
| [Data and API](data-and-api.md) | Measurements, ingest contract, clocks, storage, analytics, chart data, response payloads, and rename operation. |
| [AI, grounding, and sources](learning-and-sources.md) | Semantic interpretation, deterministic/LLM boundaries, source hierarchy, provenance, recovery behaviour, and AI constraints. |
| [Testing and evaluation](testing-and-evaluation.md) | Automated checks, Android acceptance, integration/deployment validation, usability, performance, and capstone evidence collection. |
| [Development record](development-record.md) | Material design decisions, faults, fixes, direction changes, rationale, and verification. |
| [Visual documentation](diagrams/README.md) | Mermaid diagrams and their maintenance ownership. |

The ESP32-specific build and simulation guide lives beside the firmware in [firmware/esp32-sensor/README.md](../firmware/esp32-sensor/README.md).

## Historical documentation

| Document | Status |
|---|---|
| [Embedded flexible IT course design](course-design.md) | Superseded capstone direction retained to document the genuine earlier elective work. |
| [Local LLM evaluation history](history/local-llm-evaluation.md) | Historical Pi model measurements and later development/reference-model decisions. |

Historical material should not be silently rewritten to make it appear that the current direction existed from the beginning. Where a design has been superseded, add a clear status note and leave the original reasoning visible.

## Status language

Documentation uses these terms consistently:

- **Implemented** means present in the current repository.
- **Configured deployment** means enabled only when the required environment or external service is supplied.
- **Development/reference setup** means used to evaluate the architecture but not required by the checked-in Pi service template.
- **Planned** means design direction only and must not be described as deployed.
- **Historical** records a completed experiment or superseded decision and is retained as capstone evidence.

## Documentation maintenance rule

Do not add a second current-state document for a subject already owned by one of the files above. Extend the authoritative document and update its diagrams or links. Historical measurements and superseded design directions belong under `docs/history` or must be explicitly labelled historical if retained at their original path.
