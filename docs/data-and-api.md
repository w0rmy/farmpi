# FarmPi data, analytics, and API

## Measurement catalogue

`app/measurements.py` is the single reviewed catalogue for stored keys, labels, units, input ranges, natural-language aliases, permitted operations, educational concepts, and chart type.

| Measurement | Key | Unit | Accepted range |
|---|---|---:|---:|
| Soil moisture | `soil_moisture_pct` | % | 0-100 |
| Soil temperature | `soil_temperature_c` | °C | -10-60 |
| Air temperature | `air_temperature_c` | °C | -30-60 |
| Relative humidity | `relative_humidity_pct` | % | 0-100 |
| Soil pH | `soil_ph` | - | 0-14 |
| Soil electrical conductivity | `soil_ec_ms_cm` | mS/cm | 0-20 |
| Light | `light_lux` | lux | 0-200,000 |
| Rainfall per interval | `rainfall_mm` | mm | 0-100 |
| Barometric pressure | `barometric_pressure_hpa` | hPa | 850-1,100 |
| Wind speed | `wind_speed_kmh` | km/h | 0-250 |
| Wind direction | `wind_direction_deg` | degrees | 0-360 |
| Pasture height | `pasture_height_cm` | cm | 0-300 |
| Leaf wetness | `leaf_wetness_pct` | % | 0-100 |

The simulator does not fabricate N, P, or K values. EC is a raw chemistry-related proxy and is not a nutrient diagnosis.

## Storage model

- `paddocks` holds active status and the mutable display name.
- `sensor_nodes` holds a stable node UID and its paddock relationship.
- `readings` holds complete timestamped measurement rows, provenance, clock metadata, sequence, and protocol version.
- `paddock_admin_audit` records controlled display-name changes.

Relationships use numeric IDs. Renaming a paddock does not rewrite readings or move a sensor. The repeatable seed identifies virtual nodes by stable UIDs `test-moisture-a` through `test-moisture-p`, preserving an existing renamed paddock.

`config/database/schema.sql` is additive for older alpha databases. New columns are nullable where necessary to preserve earlier rows; current ingest writes complete records. Range checks exist in the API, application catalogue, and database.

## Telemetry ingest

`POST /api/ingest` requires `Authorization: Bearer <FARMPI_INGEST_TOKEN>` and a complete JSON payload:

```json
{
  "sensor": "test-moisture-a",
  "soil_moisture_pct": 18.0,
  "soil_temperature_c": 13.2,
  "air_temperature_c": 16.5,
  "relative_humidity_pct": 74.0,
  "soil_ph": 6.2,
  "soil_ec_ms_cm": 0.42,
  "light_lux": 12000,
  "rainfall_mm": 0.0,
  "barometric_pressure_hpa": 1015.2,
  "wind_speed_kmh": 9.0,
  "wind_direction_deg": 225,
  "pasture_height_cm": 10.5,
  "leaf_wetness_pct": 8.0,
  "simulated": true,
  "protocol_version": 1,
  "device_time_unix": 1780000000,
  "clock_valid": true,
  "sample_seq": 123
}
```

Success returns HTTP 201 with the stored reading ID, resolved paddock, validated values, observed/received/recorded times, clock status, deduplication status, time-sync requirement, and authoritative server Unix time.

## Clock and retry contract

FarmPi is the UTC authority.

- `received_at` is FarmPi receipt time and owns current-value freshness and transport diagnostics.
- `observed_at` is device observation time when the node clock is valid.
- `created_at` is the database insertion/audit timestamp.
- `recorded_at` remains a compatibility alias during the alpha migration.

When device time is missing, invalid, or more than 30 seconds from FarmPi, the response sets `time_sync_required=true`. The row retains the clock-quality metadata; historical analytics use valid in-tolerance `observed_at`, otherwise `received_at`. An invalid clock is never stored as a fabricated 1970 observation.

`sample_seq` is unique per sensor when present. Retrying the same sensor/sequence returns the original reading rather than inserting a duplicate. The acknowledgement semantics are transport-neutral so a future LoRa transport could carry the same time and sequence contract without changing the database authority.

## Deterministic analytics

The application permits only catalogue-listed operations, including current values, farm-wide average, supported rankings/extrema, minimum, maximum, average, rainfall total, first-to-last change/trend, range, simple two-standard-deviation anomaly flagging, paddock comparison, and compact summary.

Historical windows are bounded from five minutes to seven days. `today` and `this morning` use Pacific/Auckland calendar boundaries converted to UTC before querying. Derived daylight counts five-minute `light_lux` samples at or above 1,000 lux; it is an approximation, not an ingest field or LLM estimate.

Charts are backend-supplied bar or line payloads. The Android client renders them but does not calculate their values. Evidence items preserve paddock, sensor UID where available, timestamp, value, and simulated provenance.

## Learner API

| Endpoint | Method | Purpose |
|---|---|---|
| `/` | GET | Diagnostic browser client. |
| `/health` | GET | Application-process liveness. |
| `/api/status` | GET | Application, MariaDB, and configured LLM status. |
| `/api/guidance` | GET | Reviewed onboarding text and suggestions; accepts `guidance_level`. |
| `/api/learning/course` | GET | Canonical deterministic course: aim, four outcomes, five modules, Try/Ask/Check/Continue metadata, and response-intent mappings. |
| `/api/learning/activities` | GET | Backwards-compatible concise activity catalogue projected from/alongside the course. |
| `/api/speech/normalize` | POST | Deterministic spoken-domain correction. |
| `/api/ask` | POST | Single conversational contract for Android/browser clients. |
| `/api/ingest` | POST | Authenticated sensor telemetry ingest. |

`POST /api/ask` accepts a question, optional confirmation/conversation token, optional `course_module_id`, optional speech alternatives, and presentation preferences. `course_module_id` is limited to an identifier in `app/learning.py`; an unknown id returns HTTP 422. The client cannot submit arbitrary course or system prompt text. When a valid module contributes to a model-assisted answer, the response provenance includes a `reviewed-course-module` entry.

Its response can contain:

- `answer` and concise `spoken_answer`;
- selected `intent` and optional structured semantic interpretation;
- per-stage timings;
- confirmation and conversation tokens;
- next-question suggestions;
- speech-normalisation diagnostics;
- chart and bounded evidence;
- source category, evidence tier, and provenance.

`/api/learning/course` is controlled and versioned in application source. It is not generated by the configured model. Its module payload exposes only learner-facing material: id, title, linked outcome ids, Learn content, Try metadata (including real success intents), AI quick prompts, a lightweight understanding check, next-module id, and response-intent mapping. Reviewed prompt context remains server-only.

## Paddock identity and rename

Paddock references resolve in this order: current display name, audited former name, canonical letter, then active configured numeric/word-number order. Close matches can produce a cautious suggestion; ambiguous or out-of-range references return specific recovery guidance.

`Rename Paddock A to North Flat` creates a validated five-minute proposal. Only `confirm` or `yes` with the matching opaque token applies the update. The model does not authorise or execute the mutation. The application updates only `paddocks.name` and writes `paddock_admin_audit`; historical rows remain linked by numeric ID.
