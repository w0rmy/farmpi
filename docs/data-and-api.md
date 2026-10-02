# FarmPi data, analytics, and API

## Measurement catalogue

`app/measurements.py` is the single reviewed catalogue for stored keys, labels, units, input ranges, natural-language aliases, permitted operations, explanatory concept metadata, preferred chart type, and legacy standard/add-on labels. These labels do not control per-node enablement.

### Standard physical node

FR01 requires these six physical measurements for final T01 acceptance. They are not mandatory fields in each node or telemetry payload:

| Measurement | Key | Unit | Accepted range |
|---|---|---:|---:|
| Soil moisture | `soil_moisture_pct` | % | 0-100 |
| Soil temperature | `soil_temperature_c` | °C | -10-60 |
| Air temperature | `air_temperature_c` | °C | -30-60 |
| Relative humidity | `relative_humidity_pct` | % | 0-100 |
| Light | `light_lux` | lux | 0-200,000 |
| Barometric pressure | `barometric_pressure_hpa` | hPa | 850-1,100 |

### Optional/add-on measurements

These measurements are supported by the application and simulator but are not required on the standard physical node:

| Measurement | Key | Unit | Accepted range |
|---|---|---:|---:|
| Soil pH | `soil_ph` | - | 0-14 |
| Soil electrical conductivity | `soil_ec_ms_cm` | mS/cm | 0-20 |
| Rainfall per interval | `rainfall_mm` | mm | 0-100 |
| Wind speed | `wind_speed_kmh` | km/h | 0-250 |
| Wind direction | `wind_direction_deg` | degrees | 0-360 |
| Pasture height | `pasture_height_cm` | cm | 0-300 |
| Leaf wetness | `leaf_wetness_pct` | % | 0-100 |

An omitted optional field means that node does not currently report that capability. FarmPi stores SQL `NULL`, omits the unavailable measurement from current summaries, and never invents a value to make a row appear complete. The simulator may continue to emit all optional fields because synthetic capabilities have no hardware cost.

The simulator does not fabricate N, P, or K values. EC is a raw chemistry-related proxy and is not a nutrient diagnosis.

## Storage model

- `paddocks` is retained as the internal table name for monitoring locations. It holds a stable numeric ID, active status and a farmer-editable display name.
- `sensor_nodes` holds the stable FarmPi node ID, immutable hardware UID, optional friendly node name, registration state, device credential hash, capabilities, desired/applied configuration, sync diagnostics and current location assignment.
- `readings` holds sparse measurements, the location ID captured on ingest, row-level compatibility provenance, per-measurement `measurement_modes_json`, clock metadata, sequence and protocol version.
- `paddock_admin_audit` records controlled display-name changes.

Hardware identity, FarmPi node identity and farmer location name are separate. A node can move between locations without changing its hardware UID or logical ID. A location may later contain more than one node. Historical readings retain the location ID captured when they were accepted.

The operational seed is intentionally empty. It no longer creates the old 16 synthetic paddocks or `test-moisture-a` through `test-moisture-p`. That simulator remains a deliberate test/demo tool under `firmware/esp32-sensor`, not normal operational state.

`scripts/reset-operational-database` is the explicit transition helper. It refuses to run without `--yes-really-reset`, archives the existing database with `mysqldump`, then recreates a clean database from the current schema. Running that helper is a separate deployment decision; applying this branch does not itself erase the live Pi database.

Measurement columns remain nullable so mixed sensor capabilities and sparse samples are valid. Explicit nulls, unknown fields, strings, booleans and non-finite measurement values are rejected.

## Telemetry ingest

`POST /api/ingest` retains `Authorization: Bearer <FARMPI_INGEST_TOKEN>` for legacy simulated nodes. Physical nodes use the registered hardware UID and per-device credential described in [S3 setup](s3-node-bringup.md). The following legacy simulator example may omit any measurements it does not produce:

```json
{
  "sensor": "test-moisture-a",
  "soil_moisture_pct": 18.0,
  "soil_temperature_c": 13.2,
  "air_temperature_c": 16.5,
  "relative_humidity_pct": 74.0,
  "light_lux": 12000,
  "barometric_pressure_hpa": 1015.2,
  "simulated": true,
  "protocol_version": 1,
  "device_time_unix": 1780000000,
  "clock_valid": true,
  "sample_seq": 123
}
```

A node with installed add-ons may include any supported optional fields in the same payload, for example:

```json
{
  "soil_ph": 6.2,
  "soil_ec_ms_cm": 0.42,
  "rainfall_mm": 0.0,
  "wind_speed_kmh": 9.0,
  "wind_direction_deg": 225,
  "pasture_height_cm": 10.5,
  "leaf_wetness_pct": 8.0
}
```

Success returns HTTP 201 with the stored reading ID, resolved location, the measurements actually supplied/stored, row-level simulated status, per-measurement `measurement_modes`, observed/received/recorded times, clock status, deduplication status, time-sync requirement, and authoritative server Unix time.

For a managed ESP32-S3, provenance comes from the acknowledged configuration. Each supported measurement is `OFF`, `SIMULATED`, or `LIVE`. OFF values are rejected. SIMULATED values are generated on the node and traverse the same authenticated ingest path as LIVE values. LIVE values require an advertised physical driver as well as an acknowledged LIVE configuration. The server checks the firmware declaration; it cannot independently prove a probe is connected. A node remains valid with every measurement OFF.

## Clock and retry contract

FarmPi is the UTC authority. Managed ESP32-S3 nodes receive authoritative `server_time` in every successful `POST /api/nodes/contact` response and use it to establish/correct their application clock when needed. `farmpi.local` is not an NTP service, and managed-node telemetry does not require Internet time.

- `received_at` is FarmPi receipt time for transport diagnostics; observation age remains separate.
- `observed_at` is device observation time when the node clock is valid.
- `created_at` is the database insertion/audit timestamp.
- `recorded_at` remains a compatibility alias during the alpha migration.

When device time is missing, invalid, or more than 30 seconds from FarmPi, the response sets `time_sync_required=true`. The row retains the clock-quality metadata; historical analytics use valid `observed_at`, otherwise `received_at`. A delayed valid physical observation keeps its original time even when arrival delay triggers a clock resynchronisation request. Physical submissions require a valid timestamp and reject times more than 30 seconds in the future. An invalid clock is never stored as a fabricated 1970 observation.

`sample_seq` is unique per sensor when present. Retrying the same sensor/sequence returns the original reading rather than inserting a duplicate. The acknowledgement semantics are transport-neutral so a future LoRa, LoRaWAN, or Wi-Fi HaLow transport can carry the same time and sequence contract without changing database/application authority.

## Structured monitoring overview

The Android dashboard no longer needs to ask the conversational endpoint to construct its main screen. `GET /api/monitoring/overview` returns structured application-owned monitoring state directly from the same validated database and analytics layer used elsewhere.

The endpoint deliberately separates **data availability** from connectivity. A location with a stored reading is reported as having data and includes its reading age; the endpoint does not label a node online merely because an older row exists. It returns configured locations even when they have no reading yet. Farm-level measurement cards use deterministic averages across locations that currently have that measurement, with simulated provenance retained if any contributing value is simulated.

The optional featured chart is the existing deterministic 24-hour soil-moisture trend payload. If no verified history exists, the field is null rather than synthesised.

The Compare screen uses `/api/monitoring/compare` rather than converting two selected locations back into natural-language text. Android passes the two stable location IDs, measurement key and bounded window. This prevents a farmer-defined display name from changing comparison semantics and ensures that selecting Bob's paddock and Fred's paddock compares only those two locations rather than every paddock in the database.

## Current values across mixed capabilities

A current paddock snapshot uses each active node’s latest observation at its current assigned location, ordered by observation time. It does not require six measurements. Only values present in that sample are included; a different sparse sample does not silently carry an older measurement forward. This means:

- a baseline-only node remains a fully valid FarmPi monitoring node;
- a pH/EC/rain/wind/pasture/leaf-wetness query can return data only for paddocks that actually report that capability;
- farm-wide optional averages/rankings use reporting paddocks rather than treating absent capabilities as zero;
- paddock summaries omit unavailable optional measurements rather than fabricating or carrying stale values forward.

## Deterministic analytics and graph data

The application permits only catalogue-listed operations, including current values, farm-wide average, supported rankings/extrema, minimum, maximum, average, rainfall total, first-to-last change/trend, range, simple two-standard-deviation anomaly flagging, paddock comparison, compact summary, and daylight derivation where supported.

Historical queries already require the selected measurement to be non-null, so analytics and charts naturally operate only on records that actually contain that capability. Historical windows are currently bounded from five minutes to seven days. `today` and `this morning` use Pacific/Auckland calendar boundaries converted to UTC before querying. Derived daylight counts five-minute `light_lux` samples at or above 1,000 lux; it is an approximation, not an ingest field or LLM estimate.

The backend supplies verified chart payloads; the Android client may render the same data as line, area/day-profile, bars, or dots depending on the dataset. Display mode is presentation only and must never change the values.

Generic historical graph requests without a named paddock should use a valid farm-wide aggregation where the operation supports it. Named-paddock graphs and explicit cross-paddock comparisons remain separate meanings.

Evidence items preserve paddock, sensor UID where available, timestamp, value, and simulated provenance.

## Application API

| Endpoint | Method | Purpose |
|---|---|---|
| `/` | GET | Diagnostic browser client. |
| `/health` | GET | Application-process liveness. |
| `/api/status` | GET | Application, MariaDB, configured LLM, and monitoring-API capability status. |
| `/api/monitoring/overview` | GET | Deterministic Android dashboard snapshot: configured locations, latest stored measurements, provenance/age metadata, farm summary values and a verified 24-hour soil-moisture chart when history is available. No LLM is involved. |
| `/api/monitoring/compare` | GET | Deterministic comparison of two explicitly selected active locations over a bounded history window. Uses location IDs, application analytics and verified evidence; no LLM is involved. |
| `/api/guidance` | GET | Reviewed onboarding text and suggestions; accepts `guidance_level`. |
| `/api/speech/normalize` | POST | Deterministic spoken-domain correction. |
| `/api/ask` | POST | Main conversational/data-query contract for Android/browser clients. |
| `/api/ingest` | POST | Authenticated sensor telemetry ingest. |

Managed physical-node endpoints:

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/nodes` | GET | Administrator view of discovered/registered physical nodes, locations, sync state and per-sensor runtime state. |
| `/api/nodes/contact` | POST | Device discovery/heartbeat with hardware UID, device credential, firmware/profile, capabilities and optional applied fingerprint. |
| `/api/nodes/configuration` | POST | Authenticated device fetch of the latest complete desired configuration. |
| `/api/nodes/ack` | POST | Device acknowledgement or failure report for an attempted configuration fingerprint. |
| `/api/nodes/locations` | POST | Administrator creation of a farmer-named monitoring location. |
| `/api/nodes/{id}/approve` | POST | Administrator approval/registration of a discovered node and assignment of initial identity/location. |
| `/api/nodes/{id}/configuration` | PUT | Administrator update of friendly node name, location and per-measurement OFF/SIMULATED/LIVE modes with optimistic fingerprint checking. |

Administrator endpoints require `Authorization: Bearer <FARMPI_ADMIN_TOKEN>`. Device contact/configuration/acknowledgement use the per-device credential generated and persisted by the ESP32-S3; hardware UID is identification, not authentication. Registration begins with every firmware-supported measurement in `OFF` mode.

Legacy endpoints retained from the earlier flexible-course direction:

| Endpoint | Method | Status |
|---|---|---|
| `/api/learning/course` | GET | Implemented legacy course payload; no longer a primary capstone requirement. |
| `/api/learning/activities` | GET | Backwards-compatible legacy activity catalogue. |

`POST /api/ask` accepts a question, optional confirmation/conversation token, optional speech alternatives, presentation preferences, and, while the legacy course code remains, an optional `course_module_id`. If supplied, the module id is limited to the server-controlled definition in `app/learning.py`; clients cannot submit arbitrary course or system prompt text.

Course context applies only to the request that supplies `course_module_id`; it is not stored as a conversation setting. The current Android reshape target removes the course/module/progress surfaces. Until that refactor is complete, ordinary typed, spoken and suggested questions omit course context. The legacy API should be removed only after no current client path consumes it.

Compatibility identifiers such as the interpreter's `learning` intent, response intents `agriculture-learning` and `education`, `education_key`, source category `educational`, and provenance kind `curated-learning` remain unchanged. They identify existing information/reference routes and do not require ordinary questions to be agricultural or course-related.

Its response can contain:

- `answer` and concise `spoken_answer`;
- selected `intent` and optional structured semantic interpretation;
- per-stage timings;
- confirmation and conversation tokens;
- next-question suggestions;
- speech-normalisation diagnostics;
- chart and bounded evidence;
- source category, evidence tier, and provenance.

The server guarantees that a null/blank `spoken_answer` falls back to the displayed answer so client TTS does not receive the literal string `null`.

## Capability lookup and unsupported requests

The measurement catalogue is the application source of truth for what can be measured, calculated, compared, and graphed. It also distinguishes the six standard-node capabilities from optional add-ons. When a user requests an optional measurement that a particular paddock does not report, FarmPi should say so directly rather than present an invented value or generic model limitation.

When a user asks for a graph or analytic that does not map directly to a supported key, the application should inspect aliases and nearby capabilities before returning a limitation. The model's own ability to draw or not draw a graph is irrelevant: FarmPi graph capability is determined by the application catalogue, stored data, analytics functions, and Android renderer.

## Location identity and rename

The database keeps the historical internal term `paddocks`, but the user-facing concept is a monitoring location. The farmer supplies the display name. Names can be ordinary property language such as `Bob's`, `Back Hill` or `Down by the Trough`.

Location references resolve by current display name first, with audited former names and older alpha letter/number aliases retained for compatibility. Renaming a location changes only its display name and audit record. It does not rewrite historical readings or change a node's hardware/FarmPi identity.

## Managed node configuration

See [S3 node bring-up](s3-node-bringup.md) for registration, SHA-256 canonical configuration, administrator access, NVS persistence and the two-board acceptance checklist.

The current canonical configuration is schema version 2 and contains exactly `modes`, `node_uid`, and `schema_version`. `modes` contains one OFF/SIMULATED/LIVE value for every capability advertised by that firmware. FarmPi fills omitted administrator choices with OFF before fingerprinting, so the device always receives one complete latest state rather than a patch.

The managed ESP32-S3 profile advertises all 13 catalogue keys as configurable/simulatable capabilities and currently advertises `soil_moisture_pct` in `live_capabilities`. The current physical driver reads the XC4604 analogue probe on GPIO4 and uses an explicitly uncalibrated proof-of-concept electrical scale. Configuration, acknowledgement and ingest reject LIVE for measurements outside the advertised list. Older firmware omitting this field is treated as having no advertised LIVE drivers.

The logical ID uses `FP-xxx` and remains stable when the user changes the friendly node name or assigned location. End-to-end physical acceptance of `soil_moisture_pct` on FP-001 / HW 33C0 is retained in [the XC4604 LIVE evidence record](evidence/s3/soil-moisture-live-acceptance-2026-10-02.md).

Android omits `modes` on metadata-only updates, preserving the stored configuration exactly. The console helper submits all supported modes with the expected fingerprint. When a mode map is supplied, omitted keys become OFF. Demo data lives in `config/database/demo-seed.sql` and is loaded only by `scripts/load-demo-data`; the operational seed remains empty.
