# FarmPi

FarmPi is an embedded agricultural learning platform built around a local farm-monitoring system. The monitoring data gives the tool a real reason to exist; the capstone is the learning experience that helps a person ask natural questions, inspect evidence, understand agricultural concepts, and adapt the presentation to their needs.

FarmPi combines:

- a Raspberry Pi FastAPI service, MariaDB, Caddy HTTPS, and an OpenAI-compatible language-model endpoint;
- one ESP32 that generates 16 clearly labelled virtual paddocks for repeatable testing;
- deterministic farm facts, calculations, identity resolution, timestamps, and controlled mutations;
- open agricultural learning answers with visible provenance and a five-level evidence hierarchy;
- a native Android client with voice input/output, charts, teach-by-doing activities, settings, themes, and text-size choices.

Synthetic telemetry is test evidence, not an agronomic model, forecast, or recommendation.

## Start here

- [Documentation index](docs/README.md)
- [System architecture](docs/architecture.md)
- [Raspberry Pi installation and operations](docs/raspberry-pi-deployment.md)
- [Android client](docs/android-client.md)
- [ESP32 simulator and telemetry](firmware/esp32-sensor/README.md)
- [Data, analytics, and API contract](docs/data-and-api.md)
- [Learning design, grounding, and sources](docs/learning-and-sources.md)
- [Testing and evaluation](docs/testing-and-evaluation.md)
- [Capstone outcome governance](docs/capstone-governance.md)
- [Development record](docs/development-record.md)

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

The checked-in Pi service template starts Qwen3 1.7B through `llama-server`. The development/reference setup can instead point FarmPi at LM Studio or another OpenAI-compatible server with `FARMPI_LLAMA_URL` and `FARMPI_LLM_MODEL`; current reference testing uses Qwen3.5-9B on the development PC. Model choice is a deployment constraint and evaluation variable, not the capstone thesis.

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

## Scope and authority

FarmPi is authoritative only for application-controlled facts and operations:

- validated current and historical FarmPi readings;
- deterministic calculations over those readings;
- active paddock/sensor identity and controlled rename history;
- timestamps, clock quality, deduplication state, and device-ingest state.

The language model never receives SQL access or authority to invent these facts. Agricultural explanations remain available, including unrelated learner questions, but their evidence tier and uncertainty must be clear. FarmPi does not turn general knowledge into a claim about this farm and does not provide unsupported forecasts, diagnoses, irrigation decisions, or automated control.

LoRa, MQTT, OTA, cloud services, remote farm control, and a full LMS are outside the current implementation. Add them only if they produce direct evidence for the defined AI and Data Sciences or Developing Flexible IT Courses outcomes.
