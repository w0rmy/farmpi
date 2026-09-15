# FarmPi

FarmPi is a local farm-monitoring application demonstrator built around a Raspberry Pi, MariaDB, a native Android client, simulated ESP32 telemetry, deterministic analytics, and an integrated language model.

The current capstone direction is **Advanced Application Development Concepts** plus **Artificial Intelligence and Data Science**. The project is therefore evaluated as an end-to-end application: requirements, architecture, integration, data handling, mobile usability, AI/data functionality, deployment, testing, debugging, and iterative refinement.

Earlier work on **Developing Flexible IT Courses** remains part of the project history, and some learning-oriented features still exist in the application, but embedded learning is no longer the primary capstone objective.

FarmPi currently combines:

- a Raspberry Pi FastAPI service, MariaDB, Caddy HTTPS, and an OpenAI-compatible language-model endpoint;
- one ESP32 simulator that generates 16 clearly labelled virtual paddocks for repeatable testing;
- deterministic current and historical farm facts, calculations, identity resolution, timestamps, chart data, and controlled mutations;
- a native Android client with text/voice interaction, text-to-speech, charts, evidence/provenance, settings, and local state;
- semantic interpretation and bounded conversation context for natural-language requests;
- curated source metadata and provenance rules for external/general information.

Synthetic telemetry is test evidence, not an agronomic model, forecast, or production-farm recommendation.

## Start here

- [Documentation index](docs/README.md)
- [Capstone direction and governance](docs/capstone-governance.md)
- [System architecture](docs/architecture.md)
- [Raspberry Pi installation and operations](docs/raspberry-pi-deployment.md)
- [Android client](docs/android-client.md)
- [ESP32 simulator and telemetry](firmware/esp32-sensor/README.md)
- [Data, analytics, and API contract](docs/data-and-api.md)
- [AI, grounding, and sources](docs/learning-and-sources.md)
- [Testing and evaluation](docs/testing-and-evaluation.md)
- [Development record](docs/development-record.md)

The earlier embedded-course design remains available as a historical document in [course-design.md](docs/course-design.md), but it is no longer a current capstone design authority.

## Current topology

```text
Android app or diagnostic browser
             |
             v
     Caddy HTTPS :443
             |
             v
 FastAPI / Uvicorn :8000 (localhost)
      |             |              |
      v             v              v
   MariaDB     deterministic    OpenAI-compatible
  farm data    application      language model
               functions        endpoint

ESP32 virtual nodes -- HTTPS POST /api/ingest --> FastAPI
```

The checked-in Pi service template starts Qwen3 1.7B through `llama-server`. The development/reference setup can instead point FarmPi at LM Studio or another OpenAI-compatible server with `FARMPI_LLAMA_URL` and `FARMPI_LLM_MODEL`; reference testing has also used Qwen3.5-9B on the development PC. Model choice is an implementation and evaluation variable rather than the application purpose.

## Quick installation on Raspberry Pi

Prerequisites are a Debian-family Raspberry Pi installation, a working `llama.cpp` checkout/build in the deployment user's home directory, Caddy, Git, Python 3 with `venv`, and local DNS or mDNS resolution for `farmpi.local`.

```bash
git clone git@github.com:w0rmy/farmpi.git ~/farmpi
cd ~/farmpi
./update
sudo bash ./scripts/setup-database
```

`./update` refuses a dirty checkout, performs a fast-forward pull, installs Python dependencies, compiles and runs the unit tests, installs both systemd units, reapplies the additive database schema/seed when configured, validates and reloads Caddy, and restarts the services.

After setup:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/api/status
sudo systemctl status farmpi.service farmpi-llm.service
```

Install Caddy's public local root certificate on the Android test device so `https://farmpi.local/` is trusted. Never copy the CA private key, database password, Wi-Fi password, or ingest token into the repository or app.

## Development checks

From the repository root:

```bash
.venv/bin/python -m compileall -q app tests
.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
```

For Android, open `clients/android` in Android Studio or run the Gradle wrapper with JDK 17 or newer and Android SDK Platform 37 installed.

## Functional authority

FarmPi is authoritative only for application-controlled facts and operations:

- validated current and historical FarmPi readings;
- deterministic calculations and chart values over those readings;
- active paddock/sensor identity and controlled rename history;
- timestamps, clock quality, deduplication state, and device-ingest state.

The language model never receives SQL access or authority to invent those facts. It supports natural-language interpretation, explanation, conversation, and general/source-oriented information. External or model knowledge must not be converted into an unsupported claim about this farm.

## Current scope

FarmPi is a prototype/concept demonstrator rather than a production farm-control product. LoRa/LoRaWAN, MQTT, OTA, cloud services, remote control, production security hardening, and agronomic certification are outside the current implementation unless a defined requirement makes them necessary.

Current work should prioritise a coherent functional application: mobile usability, reliable routing and recovery, data visualisation, AI/data integration, error handling, testing, deployment, and clear evidence of architectural decisions.
