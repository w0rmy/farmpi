# FarmPi

FarmPi is the local farm-monitoring service used as the technical medium for the capstone. The project keeps Raspberry Pi application logic, deterministic farm-data processing, ESP32 firmware, deployment configuration, tests, and project documentation in one version-controlled repository.

The capstone focus remains **Artificial Intelligence and Data Science** plus **Developing Flexible IT Courses**. Farm monitoring is deliberately kept small enough to provide realistic data and interaction without becoming the primary engineering outcome.

## Known-good alpha milestone — 26 August 2026

FarmPi has reached a known-good local-AI proof-of-concept milestone on the Raspberry Pi 4. Android/browser access over Caddy HTTPS with its internal CA, FastAPI grounding and control, MariaDB-backed deterministic farm data, and Qwen3 0.6B through `llama-server` work together. Browser speech input (`en-NZ`) and text-to-speech output work, and unsupported information is rejected rather than invented.

The current development stage adds a real ESP32-over-Wi-Fi ingest path using **synthetic** soil-moisture data. This proves the device-to-database-to-grounded-AI path before any effort is spent on final physical sensor hardware.

## Current alpha architecture

```text
ESP32 synthetic sensor
        ↓ Wi-Fi / HTTPS
POST /api/ingest
        ↓
FastAPI validation + lightweight bearer token
        ↓
MariaDB 127.0.0.1:3306
        ↓
deterministic farm-data functions
        ↓
verified result + simulation provenance
        ↓
question router / grounding layer
        ↓
llama-server 127.0.0.1:8080
        ↓
Qwen3 0.6B
        ↓
Caddy HTTPS :443
        ↓
Phone / browser
```

Caddy is the application-facing HTTPS service. FastAPI, MariaDB, and llama-server remain local to the Raspberry Pi host.

| Endpoint | Purpose |
| --- | --- |
| `GET /` | Mobile-friendly FarmPi AI interface. |
| `GET /health` | Cheap FastAPI health check for systemd/Caddy. |
| `GET /api/status` | Shows FastAPI, MariaDB, and local LLM availability. |
| `POST /api/ask` | Answers a grounded question using deterministic MariaDB-derived facts and returns alpha timing measurements. |
| `POST /api/ingest` | Accepts one authenticated ESP32 sensor reading and stores it in MariaDB. |

## Deterministic grounding model

The LLM does not query MariaDB directly and does not calculate farm statistics. `app/database.py` provides the database boundary, `app/question_router.py` selects an approved deterministic operation, and `app/farm_data.py` provides functions such as:

- `get_moisture_snapshot()`
- `get_driest_paddock()`
- `get_wettest_paddock()`
- `get_average_soil_moisture()`
- `get_paddock_moisture()`

For common questions, Qwen receives only the verified facts required for that request. Broader soil-moisture questions retain a deterministic full-snapshot fallback. Qwen remains the language interface rather than the factual authority.

The `readings.simulated` flag is carried through the deterministic layer so synthetic ESP32 data is not silently presented as a real farm observation.

## Sensor ingest

The ESP32 sends a small JSON payload such as:

```json
{
  "sensor": "test-moisture-a",
  "soil_moisture_pct": 17.82,
  "simulated": true
}
```

FarmPi validates the sensor UID and moisture range, timestamps the reading in UTC, and stores it in MariaDB. The endpoint uses a deliberately simple FarmPi-wide bearer token for the alpha/test network.

The token is stored locally in `/etc/farmpi/farmpi.env` as `FARMPI_INGEST_TOKEN` and is never committed to GitHub.

See [docs/sensor-ingest.md](docs/sensor-ingest.md) and [firmware/esp32-sensor/README.md](firmware/esp32-sensor/README.md).

## ESP32 firmware

The project uses a monorepo. Embedded source lives under:

```text
firmware/esp32-sensor/
```

The current Arduino sketch joins Wi-Fi, resolves `farmpi.local` by mDNS, generates a small random-walk synthetic moisture value, and submits it approximately every 30 seconds.

Copy:

```text
firmware/esp32-sensor/config.example.h
```

to:

```text
firmware/esp32-sensor/config.h
```

and set the Wi-Fi credentials, sensor UID, and ingest token. `config.h` is ignored by Git.

For this prototype the ESP32 uses TLS with certificate validation disabled (`setInsecure()`). This avoids turning the capstone into an embedded certificate-provisioning project. The browser-facing FarmPi interface continues to use trusted HTTPS through Caddy's internal CA.

## Latency instrumentation

During alpha testing `POST /api/ask` returns:

- `routing_ms`
- `database_ms`
- `context_ms`
- `llm_ms`
- `total_ms`

The web page displays total response time and LLM time after each answer. The optimisation design is documented in [docs/latency-optimization.md](docs/latency-optimization.md).

## First-time installation on the Raspberry Pi

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip
git clone git@github.com:w0rmy/farmpi.git ~/farmpi
cd ~/farmpi
./update
sudo bash ./scripts/setup-database
```

The one-time database setup creates MariaDB, the restricted application account, the database password, the sensor-ingest token, the schema, and the repeatable prototype rows. Credentials are stored in `/etc/farmpi/farmpi.env` with restricted permissions.

## Updating an existing FarmPi

```bash
cd ~/farmpi
./update
```

The updater validates Python code and unit tests, updates the systemd configuration, reapplies the idempotent database schema when MariaDB is already configured, reloads Caddy, and restarts FarmPi.

If an existing installation predates the sensor-ingest token, run once after updating:

```bash
sudo bash ~/farmpi/scripts/setup-database
```

Then display the generated token with:

```bash
sudo grep '^FARMPI_INGEST_TOKEN=' /etc/farmpi/farmpi.env
```

## Prototype database data

The seed creates four test nodes:

| Paddock | Sensor UID | Initial soil moisture |
| --- | --- | ---: |
| Paddock A | `test-moisture-a` | 18% |
| Paddock B | `test-moisture-b` | 24% |
| Paddock C | `test-moisture-c` | 29% |
| Paddock D | `test-moisture-d` | 21% |

Useful validation questions include:

- `Which paddock is driest?`
- `Which paddock is wettest?`
- `What is Paddock B's soil moisture?`
- `What is Paddock B's soil temperature?` — this should report that the information is unavailable.

## HTTPS and speech

The repository Caddy configuration serves `https://farmpi.local` using Caddy's internal certificate authority. The Caddy root CA must be trusted by browser devices for normal trusted HTTPS. Browser speech recognition requires this secure context.

The root certificate is stored on FarmPi at:

```text
/var/lib/caddy/.local/share/caddy/pki/authorities/local/root.crt
```

## Project layout

```text
app/                     FastAPI, ingest API, DB access, routing, grounding logic
firmware/esp32-sensor/   ESP32 synthetic sensor firmware
config/Caddyfile          HTTPS reverse-proxy configuration
config/database/          MariaDB schema and repeatable prototype seed data
config/systemd/           FarmPi and llama-server service templates
docs/                     findings and design notes
tests/                    Python unit tests
scripts/                  deployment and database helpers
update                    single-command Raspberry Pi updater
```

## Local development

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r app/requirements.txt
uvicorn app.main:app --reload
```

A local development shell must provide the same `FARMPI_DB_*` and `FARMPI_INGEST_TOKEN` environment values used by the systemd service when exercising database-backed or ingest routes.

Key project notes are in:

- [docs/llm-testing.md](docs/llm-testing.md)
- [docs/database-layer.md](docs/database-layer.md)
- [docs/latency-optimization.md](docs/latency-optimization.md)
- [docs/sensor-ingest.md](docs/sensor-ingest.md)
