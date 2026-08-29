# FarmPi grounding, guardrails, and deterministic control

## Purpose

FarmPi does not rely on one prompt or one configuration file to keep the local language model factual. The control model is deliberately layered. Each layer has a narrow responsibility and prevents later layers from having to trust the LLM with work that can be done deterministically.

The central design principle is:

> Qwen is the language interface, not the factual authority.

FarmPi grounds farm facts and actions deterministically; it does not attempt to enumerate every valid learner sentence. An earlier deny-by-default language router was too restrictive and could interpret ordinary grammar as a paddock name. The 27 August 2026 architecture correction makes the distinction explicit: the controls are for farm-specific facts, deterministic calculations and actions, not a command grammar for all learning conversation. Qwen may interpret learner intent, explain and support exploration, while every farm measurement, paddock resolution, calculation, database query, mutation, confirmation and operational decision boundary remains application-controlled.

The LLM does not query MariaDB directly, decide which SQL to run, calculate farm statistics, authorise an action, or present an invented measurement, cause, recommendation or diagnosis as a fact about this farm.

## Open learning, controlled claims

FarmPi is evolving toward an open conversational agricultural learning assistant. A learner should be able to explore dairy farming, cows, sheep, pasture, soils, irrigation, weather, effluent, animal health and related practical New Zealand agriculture in ordinary language. The application should choose the useful knowledge source rather than reject the question because it has no deterministic query route.

The corresponding rule is simple: **conversation, explanation, paraphrase tolerance, exploration and research can be open; actions and farm-specific factual claims remain controlled.** Responses must make their provenance clear: a FarmPi observation, deterministic calculation, reviewed authoritative guidance, external research, or general agricultural explanation. The current alpha supplies observations, calculations and version-controlled educational concepts. Curated NZ-source integration and external research are target capabilities, not claims of existing deployment.

## Evidence preference, not an answer-permission gate

FarmPi uses a five-level evidence hierarchy. It prefers the highest relevant available evidence; it does not use the hierarchy to refuse a useful question.

1. **First-class trusted evidence:** FarmPi deterministic data, Experience Edge, DairyNZ, and relevant `.govt.nz` sources. For New Zealand dairy and agricultural questions, prefer DairyNZ and the relevant New Zealand government source. This tier is a strong evidential preference, not a blanket claim of infallibility; current legislation text is an example of a source authoritative for its own content.
2. **Trusted primary sources:** an organisation speaking authoritatively about itself or its product, such as Fonterra about Fonterra or manufacturer documentation.
3. **Reputable general sources:** credible secondary material appropriate to the topic.
4. **General or unverified web:** material requiring clear qualification and never used as proof of a FarmPi fact or decision.
5. **Model knowledge:** a concise general explanation when no retrieved source is available, explicitly labelled as such.

Relevance determines which tier is sought and how much supporting detail is useful. It does not determine whether FarmPi is allowed to reply. If an unrelated question is asked in the farm app, FarmPi assumes the learner may see it as relevant and offers a short useful answer with suitable uncertainty. Farm-system facts - readings, history, timestamps, comparisons and device state - remain deterministic and are never invented.

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
5. interpret learner intent; route controlled actions/farm data deterministically
        ↓
6. approved deterministic retrieval/calculation
        ↓
7. select FarmPi facts/calculations and/or labelled educational source
        ↓
8. apply explicit provenance, uncertainty and farm-claim boundary
        ↓
Qwen natural-language response
        ↓
9. concise teaching and useful next learning direction
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

## 5. Deterministic action and farm-data routing — `app/question_router.py`

`app/question_router.py` interprets wording only where a controlled application operation or farm-data lookup is needed. It is intentionally not responsible for forcing every agricultural learning question into a deterministic operation.

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
- questions that have no current deterministic farm-data operation.

It also maps natural-language measurement terms such as `temperature`, `humidity`, `pH`, `EC`, `how wet`, and `lux` to explicit internal field names. Plain `temperature` selects air temperature; `soil temperature` remains explicit.

Paddock references pass through one database-backed resolver shared by every API client. It prioritises current display name, audited previous name, canonical letter, and then the active configured numeric/word-number order (`Paddock 2`, `Paddock two`, or `Paddock number 2`). The resolver returns a specific unknown, ambiguous, out-of-range, no-current-reading, or no-active-paddocks result rather than a generic unavailable answer. The API's short opaque conversation token can reuse the preceding approved current measurement for “What about Paddock 2?”; it does not provide free-form LLM memory.

The router does **not** generate SQL and does not ask the LLM to decide which database function to execute. A question without a deterministic farm-data route is an educational-source selection problem, not permission to invent an implied lookup.

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

## 7. Grounding and source context — `app/farm_data.py`

The deterministic result is converted to a compact context headed:

```text
VERIFIED FACTS
```

Only the facts appropriate to the selected route are supplied to Qwen. This reduces prompt size and reduces the opportunity for the model to answer from unrelated information. For a learning response, the equivalent discipline is to supply or identify the selected source category rather than silently treating guidance or model background knowledge as a FarmPi fact.

The provenance of synthetic telemetry is carried through the grounding layer and retained in the evidence payload. It is shown as a visual label and under **Show evidence**; routine TTS uses the API's concise spoken answer, so it does not repeat simulated-test provenance unless it is relevant or explicitly requested. The target source model extends this label to reviewed New Zealand guidance, research and general agricultural explanation; it does not replace observational evidence with a single generic "source" label.

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

For deterministic farm-data routes, its system prompt tells Qwen to:

- use only `VERIFIED FACTS` supplied by FarmPi for farm-specific assertions;
- never calculate or invent facts, causes, or recommendations;
- say a farm-specific fact or decision is unavailable when the evidence is absent;
- explain FarmPi's capabilities helpfully when capability facts are supplied.

For open-learning routes, the target instruction set must instead require an identified source category, clear uncertainty and a boundary between general guidance and the learner's farm. The prompt is therefore one guardrail, but it is deliberately the final guardrail rather than the only one.

## 9. User guidance — `app/guidance.py`

The first Flexible Learning scaffold is kept deterministic as well.

`app/guidance.py` contains:

- the onboarding welcome text;
- the verified capability facts used by the `help` route;
- initial example questions;
- context-sensitive suggested follow-up questions.

The browser can therefore prompt the user with useful next questions without allowing the LLM to invent capabilities or farm advice. As the knowledge model broadens, suggestions should include safe exploration of agricultural concepts and sources, not merely a catalogue of supported database questions.

When the user taps **Guide me**, the request is routed through the normal grounded LLM path. Qwen may phrase the explanation naturally, but the list of what FarmPi can and cannot do is supplied by deterministic application facts.

## 10. Controlled rename

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

## What remains deliberately unsupported as FarmPi-specific authority

At this stage FarmPi does not deterministically establish:

- weather forecasts;
- irrigation decisions;
- agronomic recommendations for this farm;
- causal explanations such as why this farm's pH value changed;
- rankings or summaries not enabled by the measurement catalogue.

This does not mean FarmPi must refuse to explain these subjects. It can teach the relevant general concepts or identify trusted guidance/research, provided it does not turn them into an unsupported claim or decision about the learner's farm.

`daylight_hours` is intentionally not an ingest field. It is now a documented deterministic historical derivation from `light_lux`, using a 1,000-lux threshold and five-minute sample interval.

## Why this matters to the capstone

The layered design demonstrates an important AI/Data Science distinction: a fluent LLM response is not itself evidence that the answer is correct. FarmPi therefore establishes provenance, validation, retrieval, calculation, and scope before the language model is allowed to phrase the result.

It also supports the Flexible Learning component because user guidance can become more adaptive and more open without weakening factual controls. Explanation style, onboarding depth, repeated hints, user preferences, research and next learning directions can change independently of the deterministic factual authority underneath them.
# Current implementation note

FarmPi currently returns a labelled observational, educational, or combined source category, plus deterministic chart/evidence payloads when useful. Curated concepts are separate from MariaDB readings and Qwen still has no authority to calculate, query, mutate, or make causal/agronomic claims about this farm. The next source categories - curated authoritative NZ guidance, external research and general agricultural explanation - are documented targets, not present API claims. See [educational grounding](educational-grounding.md), [structured requests](structured-requests.md), and [the grounding diagram](diagrams/grounding-pipeline.mmd).
