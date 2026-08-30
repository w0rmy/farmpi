# FarmPi visual documentation

These Mermaid sources describe the current implementation. Render them in any Mermaid-capable Markdown viewer; do not commit exported images unless a formal deliverable requires a fixed rendition. When a component boundary, data flow, source rule, or learner interaction changes, update its `.mmd` source and the owning guide in the same change.

| Diagram | Owning subject |
|---|---|
| [System architecture](system-architecture.mmd) | Pi, ESP32, clients, data, sources, and model flow |
| [Layer boundaries](layered-boundaries.mmd) | responsibility and authority boundaries |
| [Open-learning architecture](open-learning-architecture.mmd) | semantic routing, evidence hierarchy, and useful-answer path |
| [Ask/answer](ask-answer.mmd) | learner request through response/evidence |
| [Grounding pipeline](grounding-pipeline.mmd) | deterministic farm facts versus tiered learning evidence |
| [Android architecture](android-architecture.mmd) | native Ask/Course client, HTTPS, local progress, settings, and voice boundary |
| [Flexible learning](flexible-learning.mmd) | course spine, adaptation, authentic Try, and reflection loop |
| [Ingest and time sync](ingest-time-sync.mmd) | telemetry UTC, drift, and idempotency |
| [Database ERD](database-erd.mmd) | persistent identities and relationships |
| [Graphing flow](graphing-flow.mmd) | verified analytics to client chart/evidence |
| [Rename audit](rename-audit.mmd) | confirmation and mutation boundary |
| [NZ simulation](nz-simulator.mmd) | explicitly synthetic telemetry model |
| [Repository structure](repository-structure.mmd) | component ownership |

The prose authorities are [Architecture](../architecture.md), [Data and API](../data-and-api.md), [Learning and sources](../learning-and-sources.md), and [Android client](../android-client.md).
