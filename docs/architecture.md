# FarmPi architecture

## Purpose

FarmPi is a functional farm-monitoring application demonstrator. Its architecture is intended to show how a native mobile client, local API/service layer, persistent data store, deterministic analytics, simulated sensor ingest, and a constrained language model can be integrated into one coherent system.

The current capstone direction is **Advanced Application Development Concepts** plus **Artificial Intelligence and Data Science**. Earlier embedded-learning functionality remains implemented in places, but it no longer defines the architecture or current scope.

## Components

```text
Android client / diagnostic browser
              |
              v
        Caddy HTTPS gateway
              |
              v
       FastAPI composition root
        |        |         |
        |        |         +--> language-model compatibility adapter
        |        |                    |
        |        |                    v
        |        |          OpenAI-compatible LLM endpoint
        |        |
        |        +--> deterministic routing, analytics, graphing and provenance
        |
        +--> MariaDB farm data and audit history

sensor / simulator --> transport --> authenticated ingest --> FastAPI --> MariaDB
```

- `app/main.py` composes the FastAPI application, installs bounded conversation context and the LLM compatibility adapter, and includes sensor-ingest routes.
- `app/app.py` owns the primary application API, browser fallback, orchestration, timings, conversation tokens, optional legacy course context, and model call.
- `app/question_router.py` selects obvious deterministic operations; `app/semantic_interpreter.py` handles broad or varied language through a validated structured interpretation.
- `app/farm_data.py`, `app/analytics.py`, `app/measurements.py`, and `app/paddock_resolver.py` own farm facts, calculations, measurement metadata/capabilities, graph inputs, and identity resolution.
- `app/knowledge_sources.py` stores the source hierarchy, curated NZ source metadata, and reviewed claims. It is not a live search engine.
- `app/llm_compat.py` normalises OpenAI-compatible chat requests and preserves one integration contract across supported model servers.
- `app/education.py`, `app/learning.py`, and `app/guidance.py` are retained support/legacy modules from the earlier learning-focused direction. They remain functional where referenced but are not the current capstone architecture driver.
- `app/ingest_api.py` and `app/sensor_ingest.py` validate, authenticate, timestamp, deduplicate, and store telemetry.
- `clients/android` is the primary native user client. The built-in HTML page is a diagnostic fallback.

## Sensor capability model

The physical product model now distinguishes a **standard node** from optional add-on capabilities.

Every standard node reports:

- soil moisture;
- soil temperature;
- air temperature;
- relative humidity;
- ambient light;
- barometric pressure.

Optional add-ons can provide pH, EC, rainfall, wind speed/direction, pasture height, leaf wetness, and later other reviewed capabilities. The current ESP32 simulator may emit both baseline and optional measurements because it is deliberately demonstrating the broader application/data model.

This distinction is enforced at the application boundary rather than by fabricating values. New ingest samples must contain the six baseline measurements. Optional fields may be omitted and are stored as `NULL`. Current paddock snapshots require a valid baseline reading but include optional fields only when actually present. Farm-wide optional analytics use only paddocks that report the requested measurement.

The sensor/transport boundary remains deliberately separate from the application. Current Wi-Fi, a future LoRa/LoRaWAN gateway, or Wi-Fi HaLow can all feed the same transport-neutral ingest semantics without changing MariaDB, analytics, graphing, Android, or LLM authority.

## Ask/answer path

1. Typed text is used unchanged. Spoken text can first pass through deterministic domain normalisation using measurement vocabulary and active paddock names.
2. The fast router handles clear actions and farm-data operations. Broader language may be classified by the configured model into a tightly validated semantic schema.
3. Application code resolves paddock identity, selects a reviewed operation, and retrieves or calculates the smallest relevant deterministic result.
4. Measurement availability is checked against the actual paddock data/capability. Optional measurements that are not installed are reported as unavailable rather than invented.
5. Generic graph/time-series requests can operate over farm-wide data when no specific paddock is supplied. Explicit named-paddock and cross-paddock requests remain distinct.
6. Deterministic results that already form a complete answer can bypass the wording model. Requests needing explanation, semantic recovery, or broader information can call the configured LLM.
7. The response returns answer text, concise speech text, route intent, timings, suggestions, optional chart/evidence, source category, evidence tier, provenance, and semantic interpretation diagnostics where relevant.

## Authority boundaries

Application-controlled and never invented:

- sensor readings, reported capability, and device state;
- paddock/sensor identity;
- historical values and timestamps;
- averages, rankings, totals, changes, trends, ranges, comparisons, anomaly flags, and daylight derivation;
- SQL selection and database mutation;
- chart values supplied to the Android client;
- controlled paddock rename and its audit trail.

Model-assisted but application-constrained:

- natural-language interpretation;
- paraphrase and explanation;
- broader informational questions;
- conversational follow-up;
- source/provenance wording based on supplied evidence.

FarmPi does not infer a forecast, diagnosis, causal explanation, irrigation decision, uninstalled sensor value, or operational recommendation about this farm unless a future deterministic and evidenced feature explicitly establishes it.

## Capability discovery and recovery direction

The application should avoid dead-end generic refusals when a nearby supported capability exists. If a literal request cannot be executed, the system should use semantic interpretation and the measurement/operation catalogue to look for a valid alternative before asking for clarification or reporting a limitation.

This recovery behaviour is particularly important for graphs and optional sensors. The language model should not decide whether FarmPi can graph or measure something based on the model's own capabilities; application code should inspect the measurements, stored capability/data, and graph/analytics functions actually available.

## Language-model topology

The API reads:

- `FARMPI_LLAMA_URL` (default `http://127.0.0.1:8080`);
- `FARMPI_LLM_MODEL` (default `Qwen3-1.7B`).

The Pi systemd template starts Qwen3 1.7B Q4_K_M through `llama-server`, context 2048, reasoning off, one slot, localhost only. During development, the same Pi application can point to a larger reference model such as Qwen3.5-9B hosted by LM Studio on the development PC. The compatibility layer preserves the same application boundary across both topologies.

## Security and trust boundaries

- Caddy is the only normal LAN-facing service and terminates HTTPS for `farmpi.local`.
- FastAPI and the checked-in Pi `llama-server` bind to localhost.
- MariaDB binds to `127.0.0.1` and uses a restricted application account.
- ESP32 ingest requires a bearer token from `/etc/farmpi/farmpi.env`.
- The Android client uses normal HTTPS validation and may trust a user-installed Caddy public root certificate; it does not install an insecure trust manager.
- The ESP32 alpha uses encrypted TLS with hostname/SNI but `setInsecure()` because it does not yet validate the private CA. This is a documented prototype limitation.

## Repository layout

```text
app/                    FastAPI, routing, data, analytics, source and LLM integration
clients/android/        native Kotlin/Jetpack Compose client and device-local preferences
config/                 Caddy, systemd, database schema and repeatable seed
docs/                   current architecture, deployment, AI/data and evaluation docs
firmware/esp32-sensor/  16-paddock synthetic telemetry firmware
scripts/                database and service installation helpers
tests/                  deterministic behavioural and integration-contract tests
update                  repeatable Pi update/validation entry point
```

See the maintained Mermaid sources in [diagrams](diagrams/README.md).
