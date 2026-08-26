# FarmPi

FarmPi is the local farm-monitoring service intended to run on the Raspberry Pi. It keeps application logic, deployment configuration, and project notes in one version-controlled place.

## Current starter service

The application currently provides a small FastAPI service with a health endpoint. It is deliberately minimal: this establishes a repeatable way to deploy and update the Pi before sensor, database, and local-LLM functionality is added.

| Endpoint | Purpose |
| --- | --- |
| `GET /` | Confirms that the FarmPi service is running. |
| `GET /health` | Health check for the service or a reverse proxy. |

## First-time installation on the Raspberry Pi

These commands assume Raspberry Pi OS Lite 64-bit, a clone in the `pi` user's home directory, and a working internet connection for Python dependencies.

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

## Optional web proxy

The service listens only on `127.0.0.1:8000`. To expose it on the local network through Caddy, install Caddy, copy `config/Caddyfile` to `/etc/caddy/Caddyfile`, and reload Caddy. The updater automatically validates and reloads that file when a `caddy.service` is already installed.

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

The Raspberry Pi findings are recorded in [docs/llm-testing.md](docs/llm-testing.md).
