# FarmPi

FarmPi is the local farm-monitoring service intended to run on the Raspberry Pi. It keeps application logic, deployment configuration, and project notes in one version-controlled place.

## Known-good alpha milestone — 26 August 2026

FarmPi has reached a known-good alpha milestone: the complete local AI proof of concept is working on the Raspberry Pi 4. Android/browser access over Caddy HTTPS with its internal CA, FastAPI grounding and control, and Qwen3 0.6B through `llama-server` are working together. Both FarmPi and the LLM service are enabled through systemd; the lightweight `GET /health` and LLM status checks work; browser speech input (`en-NZ`) and text-to-speech output work; and supported, hard-coded prototype farm data is answered correctly while out-of-scope data is rejected rather than invented.

This milestone is deliberately an alpha proof of concept. The next architectural step is to replace the hard-coded data with a small deterministic MariaDB-backed data layer, beginning with tables such as paddocks, sensors, and readings, and a query function such as `get_driest_paddock()`.

## Current alpha architecture

The current prototype now includes the local AI interaction path:

```text
Phone / browser
    ↓
Caddy HTTPS :443
    ↓
FastAPI / Uvicorn 127.0.0.1:8000
    ↓
Grounding and application logic
    ↓
llama-server 127.0.0.1:8080
    ↓
Qwen3 0.6B
```

Caddy is the only application-facing service exposed to the local network. FastAPI and llama-server listen only on localhost.

The FastAPI application currently provides a mobile-friendly AI page, a grounded question API, lightweight health checks, and an LLM dependency status check.

| Endpoint | Purpose |
| --- | --- |
| `GET /` | Mobile-friendly FarmPi AI interface. |
| `GET /health` | Cheap FarmPi application health check. |
| `GET /api/status` | Shows FarmPi and local LLM availability. |
| `POST /api/ask` | Sends a grounded question to the local Qwen model. |

## Grounding model

The current proof of concept deliberately separates deterministic application data from language generation. The LLM is instructed to use only verified information supplied by FarmPi and to avoid inventing measurements, causes, recommendations, or conclusions.

For now, `app/app.py` contains hard-coded soil-moisture test data and verified results. This is temporary test data. The intended next stage is to replace it with deterministic MariaDB-backed retrieval and calculations while keeping the same application-to-LLM interface.

## Speech input and output

The web page supports browser speech recognition where the browser permits it and uses `en-NZ`. Because browser microphone APIs require a secure context, the production-facing local URL is HTTPS through Caddy.

If browser speech recognition is unavailable or denied, the user can use the microphone on the Android keyboard to dictate into the question field. Browser text-to-speech can read FarmPi responses aloud on the phone.

## First-time installation on the Raspberry Pi

These commands assume Raspberry Pi OS Lite 64-bit, a clone in the user's home directory, and a working internet connection for Python dependencies.

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip
git clone git@github.com:w0rmy/farmpi.git ~/farmpi
cd ~/farmpi
./update
```

`./update` creates or refreshes the Python environment, installs the FarmPi and Qwen3 0.6B systemd services, validates and enables them at boot, and restarts both services. The LLM listens only on `127.0.0.1:8080`. It will request the user's `sudo` password to apply the service configuration.

Thereafter, update the Pi from the project directory with:

```bash
cd ~/farmpi
./update
```

The updater intentionally stops if there are local uncommitted files. Commit or stash those changes before pulling an update so that remote changes cannot silently overwrite work done directly on the Pi.

## HTTPS and Caddy

The repository Caddy configuration serves `https://farmpi.local` using Caddy's internal certificate authority and reverse-proxies to FastAPI on `127.0.0.1:8000`.

The Caddy root CA must be trusted by client devices before browsers will consider the local HTTPS site fully trusted. For Android, install the Caddy root CA certificate from:

```text
/var/lib/caddy/.local/share/caddy/pki/authorities/local/root.crt
```

The updater automatically validates and reloads the repository Caddyfile when `caddy.service` is installed.

## Project layout

```text
app/                 FarmPi web service
config/              systemd and Caddy deployment configuration
docs/                project findings and design notes
scripts/             privileged deployment helpers
update               single-command Raspberry Pi updater
```

## Local development

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r app/requirements.txt
uvicorn app.app:app --reload
```

The Raspberry Pi LLM findings are recorded in [docs/llm-testing.md](docs/llm-testing.md).
