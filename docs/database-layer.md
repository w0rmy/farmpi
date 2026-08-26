# FarmPi deterministic MariaDB data layer

## Purpose

This layer replaces the hard-coded farm facts used by the first LLM proof of concept. MariaDB stores the prototype paddocks, sensor nodes, and readings. Python performs the deterministic calculations, and Qwen receives only verified results selected by the application plus the user question.

The LLM is not allowed to query MariaDB directly and is not responsible for calculating which paddock is driest, wettest, or average.

## Current data model

The first version intentionally uses only three tables:

- `paddocks` — logical farm areas;
- `sensor_nodes` — physical or simulated sensor nodes assigned to a paddock;
- `readings` — timestamped sensor values. The current schema contains soil moisture only.

The `readings` table also records whether a value is simulated. This allows seed data and synthetic ESP32 telemetry to remain clearly distinguishable from future physical sensor measurements.

The schema is in `config/database/schema.sql`.

## Current deterministic rule

For each active sensor node, FarmPi selects its latest valid soil-moisture reading. If a paddock has more than one active sensor, FarmPi averages those latest sensor values to produce the paddock's current moisture value.

From that snapshot Python can calculate:

- the driest paddock: lowest current paddock moisture value;
- the wettest paddock: highest current paddock moisture value;
- the farm average: arithmetic mean of the current paddock values;
- the current verified moisture value for a named paddock.

These calculations live in `app/farm_data.py`, including the explicit `get_driest_paddock()` function.

## Deterministic routing

`app/question_router.py` performs a small rule-based classification before any LLM context is constructed. It currently recognises requests for:

- driest paddock;
- wettest paddock;
- farm average soil moisture;
- one named paddock's moisture;
- unsupported measurement types;
- broader soil-moisture questions, which use a deterministic fallback snapshot.

The router selects approved application operations. It does not generate SQL and Qwen does not decide which database query to run.

## Grounding path

```text
ESP32 / seeded reading
      ↓
MariaDB readings
      ↓
app/database.py
      ↓
app/farm_data.py
      ↓
small verified result + simulated-data provenance
      ↓
FastAPI /api/ask
      ↓
llama-server / Qwen3 0.6B
      ↓
natural-language answer
```

This keeps factual authority in the deterministic application layer. Qwen is used as a language interface, not as the source of farm measurements or statistical conclusions.

For common questions FarmPi supplies only the minimum verified facts needed for the answer. A broader full-moisture snapshot is retained as a fallback where the deterministic router cannot safely narrow the request.

## Prototype seed data

`config/database/seed.sql` creates four prototype paddocks and one simulated moisture sensor per paddock:

| Paddock | Sensor UID | Soil moisture |
| --- | --- | ---: |
| Paddock A | `test-moisture-a` | 18% |
| Paddock B | `test-moisture-b` | 24% |
| Paddock C | `test-moisture-c` | 29% |
| Paddock D | `test-moisture-d` | 21% |

The seed is repeatable and uses a fixed timestamp so rerunning database setup does not create duplicate readings. These rows are test data and are marked as simulated.

## Sensor ingest

`POST /api/ingest` now accepts validated soil-moisture readings from registered ESP32 sensor nodes. The server timestamps each reading in UTC, stores the simulation flag, and rejects unknown sensors or moisture values outside 0–100%.

The endpoint uses a lightweight FarmPi-wide bearer token stored in `/etc/farmpi/farmpi.env`. This is intentionally sufficient for the alpha/test network without introducing per-device PKI or a full provisioning system.

The ingest design and ESP32 test path are documented in [sensor-ingest.md](sensor-ingest.md).

## Database credentials

The repository does not contain the MariaDB password or sensor-ingest token. `scripts/setup-database` generates both and writes the local service environment to `/etc/farmpi/farmpi.env` with restricted permissions. The FastAPI systemd service reads that file at startup.

## Performance instrumentation

During alpha testing `POST /api/ask` returns timing information for deterministic routing, MariaDB/data calculation, context construction, the local LLM request, and total request time. This allows the project to distinguish database/application overhead from Raspberry Pi model-inference latency.

The optimisation design and test method are documented in [latency-optimization.md](latency-optimization.md).

## Current scope

The current database-backed prototype supports soil moisture only. Temperature, pH, weather, irrigation decisions, and agronomic recommendations remain deliberately unavailable. A question requiring unsupported data should therefore result in an unavailable-information response rather than an invented value.

## Next database work

Once the synthetic ESP32 ingest path is proven end to end, additional farm-database features are not a priority for the capstone. Historical queries, sensor freshness rules, anomaly handling, and additional measurement types can be added only if they directly support the AI/Data Science or Flexible Learning outcomes. The main development emphasis should then move to the adaptive learning/user-profile layer.
