# FarmPi documentation

This directory describes the current FarmPi implementation. The repository code and configuration remain the final technical authority; update the matching document whenever a component boundary, deployment command, API contract, learner interaction, or evidence rule changes.

## Current documentation

| Document | Purpose |
|---|---|
| [Architecture](architecture.md) | Components, request flow, authority boundaries, model integration, and repository structure. |
| [Raspberry Pi deployment](raspberry-pi-deployment.md) | Installation, configuration, systemd, Caddy, MariaDB, update process, backup, and troubleshooting. |
| [Android client](android-client.md) | Build requirements, HTTPS trust, UI, voice behaviour, settings, themes, and API consumption. |
| [Data and API](data-and-api.md) | Measurements, ingest contract, clocks, storage, analytics, response payloads, and rename operation. |
| [Learning and sources](learning-and-sources.md) | Flexible-learning design, grounding, semantic routing, source hierarchy, provenance, and safety. |
| [Testing and evaluation](testing-and-evaluation.md) | Automated checks, deployment validation, usability evaluation, and capstone evidence collection. |
| [Capstone governance](capstone-governance.md) | Immutable outcome focus and IoT scope-control gate. |
| [Development record](development-record.md) | Material design decisions, rationale, scope controls, evidence mapping, and verification. |
| [Local LLM evaluation history](history/local-llm-evaluation.md) | Historical Pi model measurements and the later development/reference-model decision. |
| [Visual documentation](diagrams/README.md) | Mermaid diagrams and their maintenance ownership. |

The ESP32-specific build and simulation guide lives beside the firmware in [firmware/esp32-sensor/README.md](../firmware/esp32-sensor/README.md).

## Status language

Documentation uses these terms consistently:

- **Implemented** means present in the current repository.
- **Configured deployment** means enabled only when the required environment or external service is supplied.
- **Development/reference setup** means used to evaluate the architecture but not required by the checked-in Pi service template.
- **Planned** means design direction only and must not be described as deployed.
- **Historical** records a completed experiment or superseded decision and is retained as capstone evidence.

## Documentation maintenance rule

Do not add a second document for a subject already owned by one of the files above. Extend the authoritative document and update its diagrams or links. Historical measurements belong under `docs/history`; obsolete setup steps and superseded current-state summaries should be removed rather than left beside the active instructions.
