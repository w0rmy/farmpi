# FarmPi deterministic MariaDB data layer

## Purpose

This layer replaces the hard-coded farm facts used by the first LLM proof of concept. MariaDB now stores the prototype paddocks, sensor nodes, and readings. Python performs the deterministic calculations, and Qwen receives only the verified results plus the user question.

The LLM is not allowed to query MariaDB directly and is not responsible for calculating which paddock is driest, wettest, or average.

## Current data model

The first version intentionally uses only three tables:

- `paddocks` — logical farm areas.
- `sensor_nodes` — physical or simulated sensor nodes assigned to a paddock.
- `readings` — timestamped sensor values. The current schema contains soil moisture only.

The schema is in `config/database/schema.sql`.

## Current deterministic rule

For each active sensor node, FarmPi selects its latest valid soil-moisture reading. If a paddock has more than one active sensor, FarmPi averages those latest sensor values to produce the paddock's current moisture value.

From that snapshot Python calculates:

- the driest paddock: lowest current paddock moisture value;
- the wettest paddock: highest current paddock moisture value;
- the farm average: arithmetic mean of the current paddock values.

These calculations live in `app/farm_data.py`, including the explicit `get_driest_paddock()` function.

## Grounding path

```text
MariaDB readings
      ↓
app/database.py
      ↓
app/farm_data.py deterministic functions
      ↓
verified compact context
      ↓
FastAPI /api/ask
      ↓
llama-server / Qwen3 0.6B
      ↓
natural-language answer
```

This keeps the factual authority in the deterministic application layer. Qwen is used as a language interface, not as the source of farm measurements or statistical conclusions.

## Prototype seed data

`config/database/seed.sql` creates four prototype paddocks and one simulated moisture sensor per paddock:

| Paddock | Soil moisture |
| --- | ---: |
| Paddock A | 18% |
| Paddock B | 24% |
| Paddock C | 29% |
| Paddock D | 21% |

The seed is repeatable and uses a fixed timestamp so rerunning database setup does not create duplicate readings. These rows are test data, not live sensor measurements.

## Database credentials

The repository does not contain the MariaDB password. `scripts/setup-database` generates a random password and writes the local service environment to `/etc/farmpi/farmpi.env` with restricted permissions. The FastAPI systemd service reads that file at startup.

## Current scope

The current database-backed prototype supports soil moisture only. Temperature, pH, weather, irrigation decisions, and agronomic recommendations remain deliberately unavailable. A question requiring unsupported data should therefore result in an unavailable-information response rather than an invented value.

## Next database work

The next logical step after validating this layer is to replace the seeded readings with a controlled sensor-ingest endpoint and then connect an ESP32 sensor node. Historical queries, sensor freshness rules, anomaly handling, and additional measurement types can be added after the basic ingest path is proven.
