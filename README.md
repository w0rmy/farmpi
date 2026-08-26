# FarmPi

FarmPi is the local farm-monitoring service intended to run on the Raspberry Pi. It keeps application logic, deployment configuration, deterministic farm-data processing, and project notes in one version-controlled place.

## Known-good alpha milestone — 26 August 2026

FarmPi has reached a known-good local-AI proof-of-concept milestone on the Raspberry Pi 4. Android/browser access over Caddy HTTPS with its internal CA, FastAPI grounding and control, and Qwen3 0.6B through `llama-server` work together. Both FarmPi and the LLM run through systemd; browser speech input (`en-NZ`) and text-to-speech output work; and unsupported information is rejected rather than invented.

The next milestone is now being implemented: the original hard-coded moisture facts are being replaced by a deterministic MariaDB-backed data layer.

## Current alpha architecture

```text
Phone / browser
    ↓
Caddy HTTPS :443
    ↓
FastAPI / Uvicorn 127.0.0.1:8000
    ↓
Grounding and application logic
    ├──→ MariaDB 127.0.0.1:3306
    │      ↓
    │   deterministic farm-data functions
    │      ↓
    │   verified compact context
    │
    └──→ llama-server 127.0.0.1:8080
              ↓
           Qwen3 0.6B
```

Caddy is the only application-facing service exposed to the local network. FastAPI, MariaDB, and llama-server remain local to the FarmPi host.

| Endpoint | Purpose |
| --- | --- |
| `GET /` | Mobile-friendly FarmPi AI interface. |
| `GET /health` | Cheap FastAPI health check for systemd/Caddy. |
| `GET /api/status` | Shows FastAPI, MariaDB, and local LLM availability. |
| `POST /api/ask` | Answers a grounded question using deterministic MariaDB-derived facts. |

## Deterministic grounding model

The LLM does not query MariaDB directly and does not calculate farm statistics. `app/database.py` provides the small database access layer and `app/farm_data.py` provides deterministic functions such as:

- `get_moisture_snapshot()`
- `get_driest_paddock()`
- `get_wettest_paddock()`
- `get_average_soil_moisture()`

The current rule selects the latest valid moisture reading from each active sensor. If a paddock has multiple active sensors, their latest values are averaged to produce the paddock's current moisture value. Python then determines the driest paddock, wettest paddock, and farm average before anything is sent to Qwen.

Qwen receives only this compact verified context plus the user question. It remains the language interface rather than the factual authority.

The current MariaDB rows are repeatable prototype seed data. They are not live sensor readings yet. See [docs/database-layer.md](docs/database-layer.md).

## First-time installation on the Raspberry Pi

These commands assume Raspberry Pi OS Lite 64-bit, a clone in the user's home directory, and a working internet connection for package installation.

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip
git clone git@github.com:w0rmy/farmpi.git ~/farmpi
cd ~/farmpi
./update
sudo bash ./scripts/setup-database
```

`./update` creates or refreshes the Python environment, installs the FarmPi and Qwen3 0.6B systemd services, applies Caddy configuration when Caddy is installed, and restarts the services.

The one-time `setup-database` helper:

- installs and enables MariaDB;
- creates the `farmpi` database;
- creates a restricted `farmpi@127.0.0.1` application user;
- generates a random database password;
- stores the local credentials in `/etc/farmpi/farmpi.env` with restricted permissions;
- applies `config/database/schema.sql`;
- loads the repeatable prototype rows from `config/database/seed.sql`;
- restarts the FastAPI service so it reads the new environment.

The database password is never committed to GitHub.

## Updating an existing FarmPi

```bash
cd ~/farmpi
./update
```

If the MariaDB layer has not yet been configured, the updater prints the one-time setup command:

```bash
sudo bash ~/farmpi/scripts/setup-database
```

The updater intentionally stops if there are local uncommitted files. Commit or stash those changes before pulling so remote changes cannot silently overwrite work done directly on the Pi.

## Prototype database data

The current seed contains:

| Paddock | Soil moisture |
| --- | ---: |
| Paddock A | 18% |
| Paddock B | 24% |
| Paddock C | 29% |
| Paddock D | 21% |

Useful validation questions are:

- `Which paddock is driest?`
- `Which paddock is wettest?`
- `What is Paddock B's soil moisture?`
- `What is Paddock B's soil temperature?` — this should report that the information is unavailable.

## Speech input and output

The web page supports browser speech recognition where the browser permits it and uses `en-NZ`. Because browser microphone APIs require a secure context, the local application URL is HTTPS through Caddy.

If browser speech recognition is unavailable or denied, the user can use the microphone on the Android keyboard to dictate into the question field. Browser text-to-speech can read FarmPi responses aloud on the phone.

## HTTPS and Caddy

The repository Caddy configuration serves `https://farmpi.local` using Caddy's internal certificate authority and reverse-proxies to FastAPI on `127.0.0.1:8000`.

The Caddy root CA must be trusted by client devices before browsers consider the local HTTPS site fully trusted. The root certificate is stored on FarmPi at:

```text
/var/lib/caddy/.local/share/caddy/pki/authorities/local/root.crt
```

The updater automatically validates and reloads the repository Caddyfile when `caddy.service` is installed.

## Project layout

```text
app/                     FastAPI service, DB access, deterministic farm logic
config/Caddyfile          HTTPS reverse-proxy configuration
config/database/          MariaDB schema and repeatable prototype seed data
config/systemd/           FarmPi and llama-server service templates
docs/                     findings and design notes
scripts/install-service   systemd deployment helper
scripts/setup-database    one-time MariaDB setup helper
update                    single-command Raspberry Pi updater
```

## Local development

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r app/requirements.txt
uvicorn app.app:app --reload
```

A local development shell must provide the same `FARMPI_DB_*` environment variables used by the service if database-backed routes are to be exercised.

The Raspberry Pi LLM findings are recorded in [docs/llm-testing.md](docs/llm-testing.md), and the database design is described in [docs/database-layer.md](docs/database-layer.md).
