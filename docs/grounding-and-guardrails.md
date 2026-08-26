# FarmPi grounding, guardrails, and deterministic control

## Purpose

FarmPi does not rely on one prompt or one configuration file to keep the local language model factual. The control model is deliberately layered. Each layer has a narrow responsibility and prevents later layers from having to trust the LLM with work that can be done deterministically.

The central design principle is:

> Qwen is the language interface, not the factual authority.

The LLM does not query MariaDB directly, does not decide which SQL to run, does not calculate farm statistics, and is not allowed to invent measurements, causes, or recommendations.

## Layered control path

```text
ESP32 sensor telemetry
        ↓
1. HTTP/API validation
        ↓
2. sensor identity and ingest logic
        ↓
3. MariaDB schema and constraints
        ↓
4. deterministic question routing
        ↓
5. approved deterministic retrieval/calculation
        ↓
6. VERIFIED FACTS grounding context
        ↓
7. LLM system instructions
        ↓
Qwen natural-language response
        ↓
8. deterministic user guidance / suggested next questions
```

These layers together are what this project informally calls the guardrails. There is no single `guardrails.conf` file.

## 1. Incoming telemetry validation — `app/ingest_api.py`

`app/ingest_api.py` defines the accepted ESP32 JSON payload and validates the incoming values before they reach the database.

Current instantaneous fields are:

- `soil_moisture_pct` — 0 to 100%;
- `air_temperature_c` — -30 to 60°C;
- `relative_humidity_pct` — 0 to 100%;
- `soil_ph` — 0 to 14;
- `light_lux` — 0 to 200,000 lux;
- `simulated` — provenance flag for test telemetry.

The endpoint also applies the deliberately lightweight prototype bearer token. This prevents arbitrary unauthenticated posts while avoiding a full embedded-device PKI project.

## 2. Sensor identity and storage — `app/sensor_ingest.py`

`app/sensor_ingest.py` checks that the submitted `sensor` UID exists, is active, and belongs to an active paddock. Unknown or inactive sensor nodes are rejected.

FarmPi, rather than the ESP32, assigns the authoritative `recorded_at` timestamp in UTC. This was chosen so the prototype sensor node does not require its own real-time clock and so one time convention controls ordering of readings.

The timestamp decision became important during testing. An early fixed seed timestamp appeared newer than a genuinely later ingest value because the seed effectively used local time while ingest used UTC. That caused the deterministic latest-reading query to select the wrong row. The seed was corrected to an intentionally old UTC baseline.

## 3. Database constraints — `config/database/schema.sql`

MariaDB is another validation boundary, not merely storage. `config/database/schema.sql` defines:

- table relationships;
- sensor/paddock foreign keys;
- unique constraints;
- measurement columns;
- valid measurement ranges through `CHECK` constraints;
- the `simulated` provenance marker.

This means an invalid measurement should be rejected both by the API model and by the database constraint layer.

## 4. Deterministic question routing — `app/question_router.py`

`app/question_router.py` interprets the user's wording and selects an approved application operation before Qwen receives any farm facts.

The router currently recognises:

- help/onboarding requests;
- driest paddock;
- wettest paddock;
- average soil moisture;
- current named-paddock measurements;
- current measurement snapshots;
- broader soil-moisture questions using a safe deterministic fallback;
- unsupported questions.

It also maps natural-language measurement terms such as `temperature`, `humidity`, `pH`, and `lux` to explicit internal field names.

The router does **not** generate SQL and does not ask the LLM to decide which database function to execute.

A useful alpha failure occurred when the phrase `which paddock is driest` could fall through an earlier recogniser and the generic paddock regex interpreted the word `is` as a paddock identifier, producing `Paddock IS`. The router now contains paddock stop-words and regression tests so ordinary grammar cannot be treated as a paddock name.

## 5. Deterministic retrieval and calculation — `app/farm_data.py`

`app/farm_data.py` is the main factual-authority layer.

It retrieves the latest complete reading for active sensor nodes and produces the current environmental snapshot. For soil moisture it also performs approved deterministic calculations such as:

- driest paddock;
- wettest paddock;
- average soil moisture.

Current temperature, humidity, soil pH, and light are retrieved as measurements. Rankings or aggregates for those fields are not currently calculated, so questions such as `Which paddock is hottest?` remain unsupported until an explicit deterministic rule is implemented.

The measurement metadata and units are also defined here so the value handed to the LLM is already a complete fact such as:

```text
Paddock A air temperature: 16.50 °C.
```

Qwen is not asked to calculate or infer that value.

## 6. Grounding context — `app/farm_data.py`

The deterministic result is converted to a compact context headed:

```text
VERIFIED FACTS
```

Only the facts appropriate to the selected route are supplied to Qwen. This reduces prompt size and reduces the opportunity for the model to answer from unrelated information.

The provenance of synthetic telemetry is also carried through the grounding layer. If a result contains simulated data, Qwen is explicitly told that the result includes simulated test readings.

## 7. LLM instructions and orchestration — `app/app.py`

`app/app.py` orchestrates the full question path:

```text
question
→ route_question()
→ get_grounding_data()
→ format_grounding_context()
→ llama-server / Qwen
→ answer
```

Its system prompt tells Qwen to:

- use only `VERIFIED FACTS` supplied by FarmPi;
- never calculate or invent facts, causes, or recommendations;
- say information is unavailable when it is absent;
- explain FarmPi's capabilities helpfully when capability facts are supplied.

The prompt is therefore one guardrail, but it is deliberately the final guardrail rather than the only one.

## 8. User guidance — `app/guidance.py`

The first Flexible Learning scaffold is kept deterministic as well.

`app/guidance.py` contains:

- the onboarding welcome text;
- the verified capability facts used by the `help` route;
- initial example questions;
- context-sensitive suggested follow-up questions.

The browser can therefore prompt the user with useful next questions without allowing the LLM to invent capabilities or farm advice.

When the user taps **Guide me**, the request is routed through the normal grounded LLM path. Qwen may phrase the explanation naturally, but the list of what FarmPi can and cannot do is supplied by deterministic application facts.

## Behavioural contract — tests

`tests/test_question_router.py` and `tests/test_guidance.py` are part of the control architecture even though they do not run in production request handling.

They preserve behaviours such as:

- known questions route to approved operations;
- help requests route to deterministic capability facts;
- `Paddock IS` is not invented from grammar;
- unsupported aggregates remain unsupported;
- follow-up guidance stays within supported capabilities.

The `update` script runs the Python unit tests before restarting FarmPi, so routing-policy regressions should stop deployment.

## What remains deliberately unsupported

At this stage FarmPi does not deterministically establish:

- weather forecasts;
- irrigation decisions;
- agronomic recommendations;
- causal explanations such as why a pH value changed;
- hottest/coldest/humidest rankings;
- daylight hours.

`daylight_hours` is intentionally not an ingest field. It should later be derived deterministically from historical `light_lux` readings using a defined threshold and time window if that capability becomes useful.

## Why this matters to the capstone

The layered design demonstrates an important AI/Data Science distinction: a fluent LLM response is not itself evidence that the answer is correct. FarmPi therefore establishes provenance, validation, retrieval, calculation, and scope before the language model is allowed to phrase the result.

It also supports the Flexible Learning component because user guidance can become more adaptive without weakening factual controls. Explanation style, onboarding depth, repeated hints, and user preferences can change independently of the deterministic factual authority underneath them.
