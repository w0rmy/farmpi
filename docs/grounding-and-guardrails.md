# FarmPi grounding, guardrails, and deterministic control

## Purpose

FarmPi does not rely on one prompt or one configuration file to keep the local language model factual. The control model is deliberately layered. Each layer has a narrow responsibility and prevents later layers from having to trust the LLM with work that can be done deterministically.

The central design principle is:

> Qwen is the language interface, not the factual authority.

FarmPi grounds farm facts and actions deterministically; it does not attempt to enumerate every valid learner sentence. An earlier deny-by-default language router was too restrictive and could interpret ordinary grammar as a paddock name. This pass introduces a controlled conversational path: Qwen may interpret learner intent and explain approved learning material, while every farm measurement, paddock resolution, calculation, database query, mutation, confirmation, and operational decision boundary remains application-controlled.

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
4. deterministic speech/domain normalisation (spoken input only)
        ↓
5. deterministic action routing / conversational boundary
        ↓
6. approved deterministic retrieval/calculation
        ↓
7. VERIFIED FARM FACTS and/or APPROVED LEARNING MATERIAL grounding
        ↓
8. LLM system instructions
        ↓
Qwen natural-language response
        ↓
9. deterministic user guidance / suggested next questions
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

The 16-paddock expansion adds soil temperature, soil EC, rainfall per sample
interval, barometric pressure, wind speed/direction, pasture height, and leaf
wetness. Their aliases, ranges, units, and permitted operations are centrally
defined in `app/measurements.py`, avoiding separate regex/validation lists.

The endpoint also applies the deliberately lightweight prototype bearer token. This prevents arbitrary unauthenticated posts while avoiding a full embedded-device PKI project.

## 2. Sensor identity and storage — `app/sensor_ingest.py`

`app/sensor_ingest.py` checks that the submitted `sensor` UID exists, is active, and belongs to an active paddock. Unknown or inactive sensor nodes are rejected.

FarmPi is the authoritative UTC clock. It records both node `observed_at` and FarmPi `received_at`, checks a 30-second drift threshold, and owns all sync/deduplication rules. Qwen never participates in time synchronisation, SQL, calculation, retry handling, or mutations; [the telemetry contract](time-sync-telemetry.md) documents the detail.

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

## 4. Speech/domain normalisation — `app/speech_normalizer.py`

Browser speech recognition runs on the user's device and returns text to the FarmPi UI. For spoken input only, FarmPi asks the browser for up to five alternatives and sends them to `app/speech_normalizer.py` before the router sees the question. The module uses the reviewed aliases in `app/measurements.py`, plus current active paddock names fetched from MariaDB, as its small domain vocabulary.

It uses explainable scores rather than an LLM, a cloud speech provider, or a fuzzy-matching framework. An alternative must score strictly better than the browser's top result before it is selected; a tie stays unchanged. The explicit `Patek` → `paddock` correction is applied only when other farm context is present, so unrelated proper-name use such as a Patek watch is retained. The browser's phrase/context biasing support is inconsistent, which is why FarmPi treats this deterministic layer as the reliable correction boundary.

The response contains the raw and interpreted transcript when a change occurs, allowing the interface to display **Heard** and **Interpreted**. This records the observed `Patek`/`paddock` phone-dictation issue as an evaluation finding rather than hiding it.

Typed questions bypass this layer. Normalisation may make a spoken rename routeable, but it does not execute it: the normal deterministic confirmation boundary below still applies.

## 5. Deterministic question routing — `app/question_router.py`

`app/question_router.py` interprets the user's wording and selects an approved application operation before Qwen receives any farm facts.

The router currently recognises:

- help/onboarding requests;
- active paddock and sensor-node inventory counts;
- a latest-measurement paddock summary, including the supported measurement set;
- driest paddock;
- wettest paddock;
- average soil moisture;
- current named-paddock measurements;
- current measurement snapshots;
- broader soil-moisture questions using a safe deterministic fallback;
- unsupported questions.

It also maps natural-language measurement terms such as `temperature`, `humidity`, `pH`, `EC`, `how wet`, and `lux` to explicit internal field names. Plain `temperature` selects air temperature; `soil temperature` remains explicit.

Paddock references pass through one database-backed resolver shared by every API client. It prioritises current display name, audited previous name, canonical letter, and then the active configured numeric/word-number order (`Paddock 2`, `Paddock two`, or `Paddock number 2`). The resolver returns a specific unknown, ambiguous, out-of-range, no-current-reading, or no-active-paddocks result rather than a generic unavailable answer. The API's short opaque conversation token can reuse the preceding approved current measurement for “What about Paddock 2?”; it does not provide free-form LLM memory.

The router does **not** generate SQL and does not ask the LLM to decide which database function to execute.

A useful alpha failure occurred when the phrase `which paddock is driest` could fall through an earlier recogniser and the generic paddock regex interpreted the word `is` as a paddock identifier, producing `Paddock IS`. The router now contains paddock stop-words and regression tests so ordinary grammar cannot be treated as a paddock name.

## 6. Deterministic retrieval and calculation — `app/farm_data.py`

`app/farm_data.py` is the main factual-authority layer.

It retrieves the latest complete reading for active sensor nodes and produces the current environmental snapshot. For soil moisture it also performs approved deterministic calculations such as:

- driest paddock;
- wettest paddock;
- average soil moisture.

Current temperature, humidity, soil pH, and light are retrieved as measurements. Rankings or aggregates for those fields are not currently calculated, so questions such as `Which paddock is hottest?` remain unsupported until an explicit deterministic rule is implemented.

The expanded layer now permits only catalogue-approved rankings and bounded
historical sum/min/max/average/change. Rainfall total, pasture-height change,
and daylight derived from five-minute light samples at or above 1,000 lux are
the initial useful operations. The LLM still performs none of this arithmetic.

The measurement metadata and units are also defined here so the value handed to the LLM is already a complete fact such as:

```text
Paddock A air temperature: 16.50 °C.
```

Qwen is not asked to calculate or infer that value.

## 7. Grounding context — `app/farm_data.py`

The deterministic result is converted to a compact context headed:

```text
VERIFIED FACTS
```

Only the facts appropriate to the selected route are supplied to Qwen. This reduces prompt size and reduces the opportunity for the model to answer from unrelated information.

The provenance of synthetic telemetry is carried through the grounding layer and retained in the evidence payload. It is shown as a visual label and under **Show evidence**; routine TTS uses the API's concise spoken answer, so it does not repeat simulated-test provenance unless it is relevant or explicitly requested.

## 8. LLM instructions and orchestration — `app/app.py`

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

## 9. User guidance — `app/guidance.py`

The first Flexible Learning scaffold is kept deterministic as well.

`app/guidance.py` contains:

- the onboarding welcome text;
- the verified capability facts used by the `help` route;
- initial example questions;
- context-sensitive suggested follow-up questions.

The browser can therefore prompt the user with useful next questions without allowing the LLM to invent capabilities or farm advice.

When the user taps **Guide me**, the request is routed through the normal grounded LLM path. Qwen may phrase the explanation naturally, but the list of what FarmPi can and cannot do is supplied by deterministic application facts.

## 9. Controlled rename

Rename wording is routed to a deterministic administrative action. FarmPi
resolves the active paddock by identity/name, validates a non-duplicate display
name, asks for an explicit five-minute confirmation, updates only
`paddocks.name`, and records `paddock_admin_audit`. Qwen neither authorises
nor executes it. Numeric relationships preserve all historical rows after the
name changes.

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
- rankings or summaries not enabled by the measurement catalogue.

`daylight_hours` is intentionally not an ingest field. It is now a documented deterministic historical derivation from `light_lux`, using a 1,000-lux threshold and five-minute sample interval.

## Why this matters to the capstone

The layered design demonstrates an important AI/Data Science distinction: a fluent LLM response is not itself evidence that the answer is correct. FarmPi therefore establishes provenance, validation, retrieval, calculation, and scope before the language model is allowed to phrase the result.

It also supports the Flexible Learning component because user guidance can become more adaptive without weakening factual controls. Explanation style, onboarding depth, repeated hints, and user preferences can change independently of the deterministic factual authority underneath them.
# Current implementation note

FarmPi now returns a labelled observational, educational, or combined source category, plus deterministic chart/evidence payloads when useful. Curated concepts are separate from MariaDB readings and Qwen still has no authority to calculate, query, mutate, or make causal/agronomic claims. See [educational grounding](educational-grounding.md), [structured requests](structured-requests.md), and [the grounding diagram](diagrams/grounding-pipeline.mmd).
