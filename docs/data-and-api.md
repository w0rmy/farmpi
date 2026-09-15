# FarmPi data, analytics, and API

## Measurement catalogue

`app/measurements.py` is the single reviewed catalogue for stored keys, labels, units, input ranges, natural-language aliases, permitted operations, explanatory concept metadata, preferred chart type, and whether a measurement is required on the standard FarmPi node.

### Standard physical node

Every standard node is expected to report these six baseline measurements:

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

- `paddocks` holds active status and the mutable display name.
- `sensor_nodes` holds a stable node UID and its paddock relationship.
- `readings` holds timestamped baseline measurements, nullable optional measurements, provenance, clock metadata, sequence, and protocol version.
- `paddock_admin_audit` records controlled display-name changes.

Relationships use numeric IDs. Renaming a paddock does not rewrite readings or move a sensor. The repeatable seed identifies virtual nodes by stable UIDs `test-moisture-a` through `test-moisture-p`, preserving an existing renamed paddock.

`config/database/schema.sql` is additive for older alpha databases. Measurement columns remain nullable at the database layer so historical alpha rows and mixed sensor capabilities can coexist; the ingest application contract requires all six standard-node fields for new samples and range-validates every supplied optional field.

## Telemetry ingest

`POST /api/ingest` requires `Authorization: Bearer <FARMPI_INGEST_TOKEN>`. A standard-node payload needs only the six baseline measurements plus sensor/transport metadata:

```json
{
  "sensor": "test-moisture-a",
  "soil_moisture_pct": 18.0,
  "soil_temperature_c": 13.2,
  "air_temperature_c": 16.5,
  "relative_humidity_pct": 74.0,
  "light_lux": 12000,
  "barometric_pressure_hpa": 1015.2,
  "simulated": false,
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

Success returns HTTP 201 with the stored reading ID, resolved paddock, the measurements actually supplied/stored, simulated status, observed/received/recorded times, clock status, deduplication status, time-sync requirement, and authoritative server Unix time.

## Clock and retry contract

FarmPi is the UTC authority.

- `received_at` is FarmPi receipt time and owns current-value freshness and transport diagnostics.
- `observed_at` is device observation time when the node clock is valid.
- `created_at` is the database insertion/audit timestamp.
- `recorded_at` remains a compatibility alias during the alpha migration.

When device time is missing, invalid, or more than 30 seconds from FarmPi, the response sets `time_sync_required=true`. The row retains the clock-quality metadata; historical analytics use valid in-tolerance `observed_at`, otherwise `received_at`. An invalid clock is never stored as a fabricated 1970 observation.

`sample_seq` is unique per sensor when present. Retrying the same sensor/sequence returns the original reading rather than inserting a duplicate. The acknowledgement semantics are transport-neutral so a future LoRa, LoRaWAN, or Wi-Fi HaLow transport can carry the same time and sequence contract without changing database/application authority.

## Current values across mixed capabilities

A current paddock snapshot is considered valid when its latest node reading contains the six standard measurements. Optional fields are included only when present on the latest relevant reading. This means:

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
| `/api/status` | GET | Application, MariaDB, and configured LLM status. |
| `/api/guidance` | GET | Reviewed onboarding text and suggestions; accepts `guidance_level`. |
| `/api/speech/normalize` | POST | Deterministic spoken-domain correction. |
| `/api/ask` | POST | Main conversational/data-query contract for Android/browser clients. |
| `/api/ingest` | POST | Authenticated sensor telemetry ingest. |

Legacy endpoints retained from the earlier flexible-course direction:

| Endpoint | Method | Status |
|---|---|---|
| `/api/learning/course` | GET | Implemented legacy course payload; no longer a primary capstone requirement. |
| `/api/learning/activities` | GET | Backwards-compatible legacy activity catalogue. |

`POST /api/ask` accepts a question, optional confirmation/conversation token, optional speech alternatives, presentation preferences, and an optional legacy `course_module_id`. If supplied, the module id is limited to the server-controlled definition in `app/learning.py`; clients cannot submit arbitrary course or system prompt text.

Course context applies only to the request that supplies `course_module_id`; it is not stored as a conversation setting. Android ordinary typed, spoken, and suggested questions omit it, while explicit course activities and course quick actions supply it. Saved course progress and return location remain available.

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

## Paddock identity and rename

Paddock references resolve in this order: current display name, audited former name, canonical letter, then active configured numeric/word-number order. Close matches can produce a cautious suggestion; ambiguous or out-of-range references return specific recovery guidance.

`Rename Paddock A to North Flat` creates a validated five-minute proposal. Only `confirm` or `yes` with the matching opaque token applies the update. The model does not authorise or execute the mutation. The application updates only `paddocks.name` and writes `paddock_admin_audit`; historical rows remain linked by numeric ID.
