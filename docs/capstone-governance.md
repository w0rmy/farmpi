# Capstone direction and governance

## Current direction

As of **2 September 2026**, the FarmPi capstone direction changed from **Developing Flexible IT Courses** to **Advanced Application Development Concepts**, alongside **Artificial Intelligence and Data Science**. The earlier learning-focused work remains part of the genuine project history and explains how the project evolved, but it no longer governs current scope or evaluation.

FarmPi is now treated as a **functional farm-monitoring application demonstrator**. The capstone evidence is the process of turning a real need into requirements, architecture, implementation, integration, deployment, testing, and evaluation. The project is a prototype/concept demonstrator, not a claim of production readiness or agronomic validation.

The current evidence chain is:

**need statement -> functional, architectural, and quality requirements -> hardware/software mapping -> architecture -> implementation and integration -> deployment -> testing and evaluation**

## Outcome gate

Before accepting a feature, architecture change, experiment, or evaluation activity, record which requirement, elective outcome, graduate-profile outcome, or essential enabling dependency it supports.

A change is in scope when it materially improves one or more of:

- functional completeness of the application;
- architectural quality or separation of responsibilities;
- Android/mobile usability;
- reliable data ingest, persistence, analytics, or graphing;
- AI/data integration and governed use of the language model;
- error handling, recovery, diagnostics, security, or provenance;
- repeatable deployment, testing, or evaluation evidence.

Work that does not improve the demonstrator or provide evidence for the current outcomes should be challenged as scope creep. This remains especially important for IoT expansion: additional radios, sensors, gateways, cloud services, or field hardware are not progress by themselves.

## Current application principle

FarmPi should operate as one coherent application rather than as a collection of demonstrations. A user should be able to obtain farm data, inspect history and comparisons, view graphs, use natural-language queries, receive useful recovery when wording is imperfect, and understand when data or a requested capability is unavailable.

The Android client, FastAPI service, MariaDB data model, simulator/ingest path, deterministic analytics, graphing, source/provenance handling, and LLM integration therefore form one end-to-end application architecture.

The language model is a component of the application, not the application itself. It may interpret ordinary language, explain results, and support broader information requests, but deterministic code retains authority over farm facts, calculations, identity, database access, mutations, and chart values.

## Elective evidence mapping

| Project evidence | Primary contribution |
|---|---|
| Native Android interface, state, voice/TTS, settings, charts, error states, and usability refinement | Advanced Application Development Concepts: client design, interaction design, state handling, resilience, and iterative application development |
| FastAPI service, REST contracts, Caddy, MariaDB, modular Python components, ingest pipeline, identity/audit logic | Advanced Application Development Concepts: architecture, integration, persistence, service boundaries, security, and maintainability |
| Deterministic analytics, graph payloads, farm-wide and paddock-specific aggregation | Artificial Intelligence and Data Science: governed data processing, descriptive analytics, and visualisation |
| Semantic interpretation, bounded conversation context, LLM compatibility layer, model evaluation, source/provenance model | Artificial Intelligence and Data Science: hybrid deterministic/LLM architecture, model constraints, explainability, and evaluation |
| Fault discovery and repair such as TTS `null`, graph routing, generic-paddock extraction, model thinking/token behaviour, and conversation continuity | Both electives: iterative debugging, integration testing, failure analysis, and evidence-led refinement |
| Raspberry Pi deployment, service health, update process, synthetic telemetry, and repeatable tests | Enabling evidence for an integrated working prototype |

## Historical learning-focused work

The embedded course, Learn tab, explanation-depth controls, presentation themes, and other learning-oriented features were implemented while **Developing Flexible IT Courses** was the selected elective. They are retained as legitimate development history and may remain useful application features, but they are no longer the primary reason for further development.

Do not delete or rewrite that history. Current documentation should, however, clearly distinguish **historical learning-design evidence** from **current application-development requirements**.

## Scope boundary

FarmPi is currently a concept demonstrator using synthetic/controlled telemetry where necessary. Production field hardening, agronomic certification, autonomous control, cloud-scale deployment, LoRaWAN infrastructure, OTA management, and a full LMS are outside scope unless a later requirement explicitly makes one necessary.

The governing question for new work is now:

> **Does this make the FarmPi application more functional, coherent, reliable, usable, testable, or technically defensible against the current capstone requirements?**
