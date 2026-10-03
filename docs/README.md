# FarmPi documentation

This directory describes the current FarmPi implementation and capstone direction. Repository code and configuration remain the final technical authority; update the matching document whenever a component boundary, deployment command, API contract, user interaction, data rule, or architectural requirement changes.

The current electives are **Advanced Application Development Concepts** and **Artificial Intelligence and Data Science**. Earlier flexible-learning/course material is retained as historical development evidence but is no longer a current design authority.

## Current documentation

| Document | Purpose |
|---|---|
| [Capstone direction and governance](capstone-governance.md) | Current elective direction, requirements/evidence chain, scope gate, and application-development priorities. |
| [Architecture](architecture.md) | Components, request flow, authority boundaries, model integration, and repository structure. |
| [Raspberry Pi deployment](raspberry-pi-deployment.md) | Installation, configuration, systemd, Caddy, MariaDB, update process, backup, and troubleshooting. |
| [Android client](android-client.md) | Build requirements, HTTPS trust, mobile interaction, voice/TTS, charts, settings, state, and node administration. |
| [Data and API](data-and-api.md) | Measurements, ingest contract, clocks, storage, analytics, chart data, response payloads, and managed-node provenance. |
| [AI, grounding, and sources](learning-and-sources.md) | Semantic interpretation, deterministic/LLM boundaries, source authority, provenance, recovery behaviour, and AI constraints. |
| [Testing and evaluation](testing-and-evaluation.md) | Automated checks, Android acceptance, integration/deployment validation, usability, performance, and capstone evidence collection. |
| [Development record](development-record.md) | Material design decisions, faults, fixes, direction changes, rationale, and verification. |
| [ESP32-S3 node bring-up](s3-node-bringup.md) | Current managed-node registration, configuration synchronisation, sparse telemetry, LIVE capability and hardware status. |
| [Visual documentation](diagrams/README.md) | Current Mermaid diagrams and their maintenance ownership. |

The legacy synthetic ESP32 generator remains documented beside its firmware in [firmware/esp32-sensor/README.md](../firmware/esp32-sensor/README.md). The managed ESP32-S3 path is documented in [s3-node-bringup.md](s3-node-bringup.md).

## Evidence records

| Evidence | What it demonstrates |
|---|---|
| [Capstone acceptance consolidation — 3 October 2026](evidence/capstone-acceptance-consolidation-2026-10-03.md) | Current T01–T07 acceptance state, T05 closure, T02/T03/T07 operator-confirmed passes, stakeholder-test boundary, and repository freeze rule. |
| [T05 analysis and AI grounding acceptance](evidence/t05-analysis-ai-grounding-2026-10-02.md) | Deterministic facts, semantic interpretation, LLM boundaries, source/provenance and final T05 closure evidence. |
| [XC4604 LIVE soil-moisture acceptance](evidence/s3/soil-moisture-live-acceptance-2026-10-02.md) | Physical XC4604 response through FP-001, managed ingest, LIVE per-measurement provenance, MariaDB and Android. |
| [S3 live bring-up](evidence/s3/live-bringup-2026-09-26.md) | Two-board discovery/registration and bring-up fault isolation. |
| [S3 Pi backend validation](evidence/s3/pi-backend-validation-2026-09-26.md) | Raspberry Pi backend test result on the deployed host. |
| [Android UX v0.1 validation](evidence/android-ux-v01-validation.md) | Earlier Android refactor/build/device acceptance checkpoint. |

Evidence records document observed tests. They do not silently upgrade unmet requirements to PASS.

## Historical and transition documentation

These records remain useful because they show genuine design evolution, but they are not current-state authorities.

| Document | Status |
|---|---|
| [2 September 2026 elective pivot](history/2026-09-02-elective-pivot.md) | Records the confirmed switch from Developing Flexible IT Courses to Advanced Application Development Concepts. |
| [Embedded flexible IT course design](course-design.md) | Superseded capstone direction retained as genuine earlier work. |
| [Local LLM evaluation history](history/local-llm-evaluation.md) | Historical Pi model measurements and model-selection reasoning. |
| [ESP32-S3 implementation plan](s3-implementation-plan.md) | Historical design/acceptance rationale written before the current LIVE driver and Android mode administration. |
| [Android UI retirement audit](android-ui-refactor-2026-09-26.md) | Historical refactor checkpoint. |
| [Android UX v0.1 refactor map](android-ux-v01-refactor-map.md) | Historical implementation map leading to the current Android structure. |
| [Database transition and PR reconciliation, 27 September](database-transition-2026-09-27.md) | Historical database/branch reconciliation and migration record. |

Historical material should not be silently rewritten to make it appear that the current direction existed from the beginning. Where an old document remains at its original path, its status must be explicit and current guides must point to the current authority.

## Current capstone acceptance status

The consolidated pre-stakeholder state is:

- T01 — **PARTIAL (1/6)**;
- T02 — **PASS**;
- T03 — **PASS**;
- T04 — **DEFERRED / future release**;
- T05 — **PASS / CLOSED**;
- T06 — **PASS in developer/operator testing**;
- T07 — **PASS** after successful reinstall onto a new Raspberry Pi SD card.

Human stakeholder/comparative usability evidence remains separate and open.

## Current physical evidence status

The managed S3 firmware supports all 13 catalogue measurements in SIMULATED mode and currently advertises one physical LIVE capability: `soil_moisture_pct`. The XC4604 path on FP-001 / HW 33C0 has been demonstrated end to end. The other five FR01 physical measurements have not been physically demonstrated. T01 therefore remains **PARTIAL (1/6 physical measurements)**.

## Status language

Documentation uses these terms consistently:

- **Implemented** means present in the current repository.
- **Configured deployment** means enabled only when the required environment or external service is supplied.
- **Development/reference setup** means used to evaluate the architecture but not required by the checked-in Pi service template.
- **Planned** means design direction only and must not be described as deployed.
- **Historical** records a completed experiment or superseded decision and is retained as capstone evidence.
- **PASS / PARTIAL / MISSING / NOT TESTED / OUT OF SCOPE** describe evidence state; implementation alone is not a PASS.

## Documentation maintenance rule

Do not add a second current-state document for a subject already owned by one of the guides above. Extend the authoritative guide and update its diagrams or links. Put dated implementation history in the development record or clearly mark a retained transition document as historical.
