# Current implementation state

This page is the short source-oriented index for the FarmPi alpha. It describes the checked-in implementation, not an aspirational roadmap. Detailed rationale, protocols, limitations, and diagrams remain in the linked documents.

## Implemented layers

| Layer | Current implementation | Primary source |
| --- | --- | --- |
| Telemetry | One ESP32 simulates 16 stable paddocks (A-P), posting a complete reading every 18.75 seconds; a complete round is five minutes. It uses FarmPi UTC, reports device-clock state, and retries through a transport-neutral HTTPS contract. | `firmware/esp32-sensor/esp32-sensor.ino`, `app/ingest_api.py`, `app/sensor_ingest.py` |
| Data authority | MariaDB stores stable paddock and sensor identities, readings, timestamp/clock metadata, protocol version, simulation provenance, sequence value, and rename audit entries. | `config/`, `app/database.py`, `app/farm_data.py`, `app/paddock_admin.py` |
| Interpretation | `QuestionRoute` selects deterministic farm actions when needed, while capability and ordinary learner language use curated/conversational learning context. It never extracts arbitrary prepositional phrases as paddock names and keeps only minimal explicit follow-up context. | `app/question_router.py` |
| Paddock identity | Current names, audited old names, letter forms, ordinal/numeric forms, and cautious close matching are resolved against the active configured paddock order. | `app/paddock_resolver.py` |
| Analytics and presentation | The backend calculates current values, rankings, min/max/average/total/range/change/trend/baseline anomaly, comparisons, charts, and bounded evidence. It returns detailed screen facts and a separate concise `spoken_answer` where appropriate. | `app/farm_data.py`, `app/analytics.py`, `app/measurements.py` |
| Educational grounding | Version-controlled concept cards provide Simple, Normal, and Technical explanations and limitations independently of telemetry, including an irrigation decision-factor card marked for future NZ source integration. | `app/education.py`, `app/learning.py`, `app/guidance.py` |
| Browser client | The built-in HTML page is a diagnostic/fallback client with typed questions, browser speech recognition, speech-normalisation display, suggestions, and browser TTS. It currently speaks `answer`. | `app/app.py` |
| Android client | The native Compose client has voice input, local learning preferences, suggestions, charts, evidence, a neutral FarmPi palette, and native TTS. It displays `answer` and speaks `spoken_answer`. | `clients/android/` |
| Local model boundary | Qwen may interpret normal learner phrasing and explain supplied approved material, but it does not choose a farm action, query MariaDB, calculate, resolve a paddock, rename, or make causal/agronomic claims. Direct deterministic answers do not need a model call. | `app/app.py`, `docs/grounding-and-guardrails.md` |

## Farm-wide list and recovery behaviour

Farm-wide inventory language is deliberately resolved before any paddock candidate is extracted. Supported examples include:

- `List the paddocks.`
- `Could you list the names of all of the paddocks?`
- `Show me the names of the active paddocks.`
- `What are the paddock names?`
- `What paddocks are being monitored?`
- `How many paddocks are there?`

These return active configured names or counts; they do not inherit a prior paddock conversation token. A named-paddock request uses recovery stages instead: exact current name, audited alias, numeric/word-number alias, one clearly high-confidence close match, `Did you mean ...?` for a medium-confidence match, and active-name examples for low confidence. An interpretation failure is never represented as missing telemetry.

## Screen, voice, and evidence

The authoritative data/evidence path retains full timestamp and provenance fields. Current screen text uses readable freshness such as `Updated 2 minutes ago` or `Last reading: 9:42 am`. The response contract can include precise evidence plus a `spoken_answer`, so Android avoids routine raw timestamp/provenance speech. The browser remains intentionally documented as an older diagnostic client and still speaks the detailed `answer`; changing that behavior is a separate client change rather than a documentation claim.

## Detailed documents and visuals

- [Telemetry time and idempotency](time-sync-telemetry.md) and [NZ simulation](nz-synthetic-simulation.md)
- [Ingest and database model](sensor-ingest.md), [database layer](database-layer.md), and [rename/audit](paddock-admin.md)
- [Structured requests](structured-requests.md), [guardrails](grounding-and-guardrails.md), and [analytics/evidence/charts](analytics-and-graphing.md)
- [Educational grounding](educational-grounding.md), [Flexible Learning](flexible-learning.md), and [testing/evaluation](testing-and-evaluation.md)
- [Android architecture and setup](android-client.md) and [editable Mermaid diagrams](diagrams/README.md)

## Deliberate boundaries

FarmPi does not implement LoRa, MQTT, cloud services, OTA, irrigation control, forecasts, agronomic recommendations, causal diagnosis, a full LMS, or arbitrary model-generated SQL/calculation. The existing telemetry contract is transport-neutral so a future transport can preserve the same acknowledgement and data semantics.

## Documentation maintenance rule

A major feature is not complete until the affected source-level description, learner-facing instructions, rationale/limitations, tests, and relevant Mermaid diagram source are updated together. Rendered diagram exports belong beside their `.mmd` source only when a formal document needs a fixed image.
