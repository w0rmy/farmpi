# FarmPi

FarmPi is a local farm-monitoring application demonstrator built around a Raspberry Pi, MariaDB, a native Android client, managed ESP32-S3 physical nodes, explicitly simulated telemetry, deterministic analytics, and an integrated local language model.

The current capstone direction is **Advanced Application Development Concepts** plus **Artificial Intelligence and Data Science**. The project is therefore evaluated as an end-to-end application: requirements, architecture, integration, data handling, mobile usability, AI/data functionality, deployment, testing, debugging, and iterative refinement.

Earlier work on **Developing Flexible IT Courses** remains part of the project history. Some course-oriented code and UI still exist in the current revision, but they are legacy surfaces from the superseded elective and are being removed from the current product direction. Contextual explanation, natural-language help, provenance, and measurement interpretation remain in scope as FarmPi/AI functionality.

FarmPi currently combines:

- a Raspberry Pi FastAPI service, MariaDB, Caddy HTTPS, and a Pi-local OpenAI-compatible language-model endpoint;
- two managed ESP32-S3 physical nodes using discovery, explicit administrator registration, per-device credentials, and latest-state configuration fingerprints, with the sparse physical-telemetry contract ready for the acquisition drivers;
- an explicit 16-location simulator fixture available for repeatable demo/testing, but no longer loaded into the normal operational database automatically;
- a reviewed 13-measurement application catalogue, with firmware capabilities, per-node OFF/SIMULATED/LIVE configuration, LIVE-driver capability and actual reporting state kept separate;
- deterministic current and historical farm facts, calculations, identity resolution, timestamps, chart data, and controlled mutations;
- a native Android client with text/voice interaction, text-to-speech, charts, evidence/provenance, settings, local state, and managed-node administration;
- semantic interpretation and bounded conversation context for natural-language requests;
- curated source metadata and provenance rules for external/general information.

Synthetic telemetry is test evidence, not an agronomic model, forecast, or production-farm recommendation. The legacy simulator can emit a broad measurement set when explicitly loaded. Managed ESP32-S3 nodes can also generate SIMULATED values locally, so the real identity/configuration/network/ingest/database path can be tested before probes are fitted. Managed telemetry is sparse and source-labelled. The current S3 firmware advertises no LIVE probe driver yet and therefore does not claim physical acquisition. Final T01 evidence still requires six real physical measurements, but that acceptance requirement is not implemented as a mandatory six-field payload.

## Start here

- [Documentation index](docs/README.md)
- [Capstone direction and governance](docs/capstone-governance.md)
- [System architecture](docs/architecture.md)
- [Raspberry Pi installation and operations](docs/raspberry-pi-deployment.md)
- [Android client](docs/android-client.md)
- [Managed ESP32-S3 node bring-up](docs/s3-node-bringup.md)
- [ESP32 simulator and telemetry](firmware/esp32-sensor/README.md)
- [Data, analytics, and API contract](docs/data-and-api.md)
- [AI, grounding, and sources](docs/learning-and-sources.md)
- [Testing and evaluation](docs/testing-and-evaluation.md)
- [Development record](docs/development-record.md)

The earlier embedded-course design remains available as a historical document in [course-design.md](docs/course-design.md), but it is no longer a current capstone design authority.

## Current topology

```text
                       Home / management LAN
                               |
                     management Wi-Fi client
                               |
                        +--------------+
                        |   FarmPi Pi  |
Android on FarmLAN ---> | Caddy :443  | ---> FastAPI :8000 (localhost)
                        |              |          |        |
managed ESP32-S3 nodes  | FarmLAN AP   |          |        +--> Pi-local llama.cpp :8080
      |                 | 10.42.0.1/24 |          |               |
      +-- discovery ---->              |          |               +--> Qwen3 1.7B Q4_K_M
      +-- config sync -->              |          |
      +-- sparse managed ingest ----->|          +--> deterministic routing / analytics / provenance
                        |              |          |
simulated ESP32 --------+-- HTTPS ingest -------->|
                        |                         +--> MariaDB
                        +--------------+
```

The FarmLAN access-point role is bound to the intended Wi-Fi adapter by hardware MAC address rather than relying on a persistent `wlanN` name. The prototype continues to use `https://farmpi.local/` because the current Caddy certificate is issued for that DNS name.

The application above the ingest boundary is transport-neutral. Current managed nodes use Wi-Fi, while a future LoRa/LoRaWAN or Wi-Fi HaLow link could feed the same identity, time, sequence, validation, provenance, and database contracts without redesigning analytics, Android, or AI behaviour.

The current proof-of-concept inference path is local to the Raspberry Pi: `farmpi.service` uses the default `http://127.0.0.1:8080`, where `farmpi-llm.service` runs Qwen3 1.7B Q4_K_M through `llama-server`. A development/reference setup may still point FarmPi at another OpenAI-compatible endpoint with `FARMPI_LLAMA_URL` and `FARMPI_LLM_MODEL`, but the normal prototype does not depend on the development PC.

## Quick installation on Raspberry Pi

Prerequisites are a Debian-family Raspberry Pi installation, a working `llama.cpp` checkout/build in the deployment user's home directory, Caddy, Git, Python 3 with `venv`, and local DNS or mDNS resolution for `farmpi.local`.

```bash
git clone git@github.com:w0rmy/farmpi.git ~/farmpi
cd ~/farmpi
./update
sudo bash ./scripts/setup-database
```

`./update` refuses a dirty checkout, performs a fast-forward pull, installs Python dependencies, compiles and runs the unit tests, installs both systemd units, reapplies the additive database schema without loading demo data, validates and reloads Caddy, and restarts the services.

After setup:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/api/status
sudo systemctl status farmpi.service farmpi-llm.service
```

Install Caddy's public local root certificate on the Android test device so `https://farmpi.local/` is trusted. The managed ESP32-S3 target also uses the public root CA for TLS validation. Never copy the CA private key, database password, Wi-Fi password, administrator token, simulator ingest token, or per-device credentials into the repository.

## Development checks

From the repository root:

```bash
.venv/bin/python -m compileall -q app tests
.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
```

For Android, open `clients/android` in Android Studio or run the Gradle wrapper with JDK 17 or newer and Android SDK Platform 37 installed.

## Functional authority

FarmPi is authoritative only for application-controlled facts, identity/state, and operations:

- validated current and historical FarmPi readings and whether a measurement is actually available;
- deterministic calculations and chart values over those readings;
- stable hardware/logical node identity, farmer-defined location identity/names and controlled rename history;
- managed-node registration, location assignment, desired/applied configuration state, and capability availability;
- timestamps, clock quality, deduplication state, and device-ingest state.

The language model never receives SQL access or authority to invent those facts. It supports natural-language interpretation, explanation, conversation, and general/source-oriented information. External or model knowledge must not be converted into an unsupported claim about this farm.

## Current scope

FarmPi is a prototype/concept demonstrator rather than a production farm-control product. LoRa/LoRaWAN, MQTT, OTA, cloud services, remote control, production security hardening, and agronomic certification are outside the current implementation unless a defined requirement makes them necessary.

Current work should prioritise a coherent functional application: completing the physical sensing path, reshaping the Android client around monitoring/Ask/graphs/Nodes rather than the superseded course UI, reliable routing and recovery, data visualisation, AI/data integration, error handling, testing, deployment, and clear evidence of architectural decisions.
