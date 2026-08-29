# FarmPi architecture

## Purpose

FarmPi is an agricultural learning platform whose real-world vehicle is a local farm-monitoring system. The learning outcomes govern the architecture: deterministic software protects farm facts and actions, while the language model supports natural interpretation and teaching.

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
        |        +--> deterministic routing, analytics, learning and provenance
        |
        +--> MariaDB farm data and audit history

ESP32 simulator --> authenticated HTTPS ingest --> FastAPI --> MariaDB
```

- `app/main.py` composes the FastAPI application, installs the LLM compatibility adapter, and includes sensor-ingest routes.
- `app/app.py` owns the browser fallback, learner API, orchestration, timings, conversation tokens, and model call.
- `app/question_router.py` selects obvious deterministic operations; `app/semantic_interpreter.py` handles broad or varied language through a validated structured interpretation.
- `app/farm_data.py`, `app/analytics.py`, `app/measurements.py`, and `app/paddock_resolver.py` own farm facts, calculations, measurement metadata, and identity resolution.
- `app/knowledge_sources.py` stores the source hierarchy, curated NZ source metadata, and reviewed claims. It is not a live search engine.
- `app/llm_compat.py` combines system prompt fragments and optionally overrides the model identifier for stricter OpenAI-compatible chat servers such as LM Studio/Qwen3.5.
- `app/education.py`, `app/learning.py`, and `app/guidance.py` contain reviewed concepts, teach-by-doing activities, onboarding, and next-question prompts.
- `app/ingest_api.py` and `app/sensor_ingest.py` validate, authenticate, timestamp, deduplicate, and store telemetry.
- `clients/android` is the primary native learner client; the built-in HTML page is a diagnostic fallback.

## Ask/answer path

1. Typed text is used unchanged. Spoken text first passes through deterministic domain normalisation using measurement vocabulary and active paddock names.
2. The fast router handles clear actions and farm-data operations. Broader language may be classified by the configured model into a tightly validated semantic schema.
3. Application code resolves paddock identity, selects a reviewed operation, and retrieves or calculates the smallest relevant deterministic result.
4. Learning questions receive reviewed educational context, curated NZ source metadata/claims, or clearly labelled general model knowledge. Live retrieval is not currently configured.
5. Deterministic results that already form a complete answer bypass the wording model. Learning/explanation paths call the configured LLM.
6. The response returns answer text, concise speech text, route intent, timings, suggestions, optional chart/evidence, source category, evidence tier, provenance, and semantic interpretation diagnostics.

## Authority boundaries

Application-controlled and never invented:

- sensor readings and device state;
- paddock/sensor identity;
- historical values and timestamps;
- averages, rankings, totals, changes, trends, ranges, comparisons, anomaly flags, and daylight derivation;
- SQL selection and database mutation;
- controlled paddock rename and its audit trail.

Open but clearly scoped:

- agricultural explanations;
- source-oriented learning questions;
- paraphrases and unrelated questions a learner considers useful;
- explanation depth and guidance frequency;
- visual theme, contrast, and text-density preferences.

FarmPi does not infer a forecast, diagnosis, causal explanation, irrigation decision, or operational recommendation about this farm unless a future deterministic and evidenced feature explicitly establishes it.

## Language-model topology

The API reads:

- `FARMPI_LLAMA_URL` (default `http://127.0.0.1:8080`);
- `FARMPI_LLM_MODEL` (default `Qwen3-1.7B`).

The Pi systemd template starts Qwen3 1.7B Q4_K_M through `llama-server`, context 2048, reasoning off, one slot, localhost only. During development, the same Pi application can point to Qwen3.5-9B hosted by LM Studio on the development PC. The compatibility adapter preserves one prompt/grounding design across both servers.

## Security and trust boundaries

- Caddy is the only normal LAN-facing service and terminates HTTPS for `farmpi.local`.
- FastAPI and the checked-in Pi `llama-server` bind to localhost.
- MariaDB binds to `127.0.0.1` and uses a restricted application account.
- ESP32 ingest requires a bearer token from `/etc/farmpi/farmpi.env`.
- The Android client uses normal HTTPS validation and may trust a user-installed Caddy public root certificate; it does not install an insecure trust manager.
- The ESP32 alpha uses encrypted TLS with hostname/SNI but `setInsecure()` because it does not yet validate the private CA. This is a documented prototype limitation.

## Repository layout

```text
app/                    FastAPI, routing, data, learning, source and LLM integration
clients/android/        native Kotlin/Jetpack Compose client
config/                 Caddy, systemd, database schema and repeatable seed
docs/                   current architecture, deployment, learning and evaluation docs
firmware/esp32-sensor/  16-paddock synthetic telemetry firmware
scripts/                database and service installation helpers
tests/                  deterministic behavioural and integration-contract tests
update                  repeatable Pi update/validation entry point
```

See the maintained Mermaid sources in [diagrams](diagrams/README.md).
