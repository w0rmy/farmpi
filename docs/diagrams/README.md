# FarmPi visual documentation

These Mermaid sources describe the implementation and its development history. Render them in any Mermaid-capable Markdown viewer; do not commit exported images unless a formal deliverable requires a fixed rendition. When a component boundary, data flow, source rule, or user interaction changes, update its `.mmd` source and the owning guide in the same change.

## Current diagrams

| Diagram | Owning subject |
|---|---|
| [System architecture](system-architecture.mmd) | Pi, ESP32, clients, data, sources, and model flow |
| [Layer boundaries](layered-boundaries.mmd) | responsibility and authority boundaries |
| [Open-learning architecture](open-learning-architecture.mmd) | semantic routing, evidence hierarchy, and useful-answer path; filename retained from earlier direction |
| [Ask/answer](ask-answer.mmd) | user request through response/evidence |
| [Grounding pipeline](grounding-pipeline.mmd) | deterministic farm facts versus tiered external/model evidence |
| [Android architecture](android-architecture.mmd) | native client, HTTPS, local state, settings, charts, and voice boundary |
| [Ingest and time sync](ingest-time-sync.mmd) | telemetry UTC, drift, and idempotency |
| [Database ERD](database-erd.mmd) | persistent identities and relationships |
| [Graphing flow](graphing-flow.mmd) | verified analytics to client chart/evidence |
| [Rename audit](rename-audit.mmd) | confirmation and mutation boundary |
| [NZ simulation](nz-simulator.mmd) | explicitly synthetic telemetry model |
| [Repository structure](repository-structure.mmd) | component ownership |

## Historical diagram

| Diagram | Status |
|---|---|
| [Flexible learning](flexible-learning.mmd) | Historical evidence from the superseded Developing Flexible IT Courses direction. Do not use it as a current architecture driver. |

The current prose authorities are [Capstone direction and governance](../capstone-governance.md), [Architecture](../architecture.md), [Data and API](../data-and-api.md), [AI, grounding, and sources](../learning-and-sources.md), and [Android client](../android-client.md).
