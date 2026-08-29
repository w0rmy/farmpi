# Raspberry Pi deployment and operations

## Supported deployment shape

The checked-in deployment targets a Debian-family Raspberry Pi with:

- the FarmPi repository checked out by a normal service user;
- Python 3 and `venv`;
- MariaDB bound to localhost;
- Caddy serving `https://farmpi.local` with its internal CA;
- `farmpi.service` running Uvicorn on `127.0.0.1:8000`;
- `farmpi-llm.service` running Qwen3 1.7B through `llama-server` on `127.0.0.1:8080`.

The application can use a different OpenAI-compatible model server by setting `FARMPI_LLAMA_URL` and `FARMPI_LLM_MODEL`. If the model is hosted on another machine, permit only the required trusted LAN connection and do not expose the endpoint to the public Internet.

## Prerequisites

Install or prepare:

- Git and SSH access to the repository;
- Python 3, `python3-venv`, and build prerequisites needed by Python dependencies;
- Caddy;
- a built `llama.cpp` checkout at `~/llama.cpp` if using the checked-in local LLM service;
- working `farmpi.local` name resolution from Android and other clients.

The service template expects `~/llama.cpp/build/bin/llama-server`. Adjusting that path is a deployment change and should be reflected in `config/systemd/farmpi-llm.service.template`.

## First installation

Run the repository workflow as the intended service user, not root:

```bash
git clone git@github.com:w0rmy/farmpi.git ~/farmpi
cd ~/farmpi
./update
sudo bash ./scripts/setup-database
```

`scripts/setup-database` must be invoked through `sudo` by the normal FarmPi user. It:

1. installs MariaDB and OpenSSL;
2. binds MariaDB to `127.0.0.1`;
3. creates `/etc/farmpi/farmpi.env` with generated database and ingest credentials;
4. creates the `farmpi` database and restricted `farmpi@127.0.0.1` user;
5. applies the schema and repeatable 16-node seed;
6. restarts FarmPi if its service is installed.

The environment file is owned by root and the service user's group with mode `0640`.

## Environment variables

`/etc/farmpi/farmpi.env` normally contains:

```text
FARMPI_DB_HOST=127.0.0.1
FARMPI_DB_PORT=3306
FARMPI_DB_NAME=farmpi
FARMPI_DB_USER=farmpi
FARMPI_DB_PASSWORD=<generated secret>
FARMPI_INGEST_TOKEN=<generated secret>
```

Optional model overrides:

```text
FARMPI_LLAMA_URL=http://127.0.0.1:8080
FARMPI_LLM_MODEL=Qwen3-1.7B
```

For the Qwen3.5-9B development/reference setup hosted by LM Studio on the Windows PC, use the PC's current trusted-LAN address and LM Studio's advertised model identifier:

```text
FARMPI_LLAMA_URL=http://<development-pc-lan-ip>:1234
FARMPI_LLM_MODEL=qwen/qwen3.5-9b
```

Enable LM Studio's local-server network access only on a trusted LAN, allow the Pi to reach TCP port `1234`, and do not expose the server to the public Internet. FarmPi checks model-service readiness through the OpenAI-compatible `GET /v1/models` endpoint; LM Studio does not advertise `GET /health`.

Never commit this file or copy its secrets into firmware source. Only the ingest token is copied into the ignored ESP32 `config.h` on the development workstation.

## What `./update` does

The update command is deliberately conservative:

1. stops if the checkout has uncommitted changes or is detached;
2. performs `git pull --ff-only` for the current branch;
3. creates `.venv` when missing and installs `app/requirements.txt`;
4. compiles `app` and `tests`, then runs all `unittest` tests;
5. renders and verifies both systemd templates before installation;
6. reapplies the idempotent schema and repeatable seed when MariaDB is configured;
7. installs, validates, and reloads Caddy configuration when Caddy is present;
8. restarts the LLM and application services and checks their status.

The Pi checkout should therefore remain a deployment clone. Make changes in a development clone, publish them through GitHub, then use `./update` on the Pi.

## Service management

```bash
sudo systemctl status farmpi.service farmpi-llm.service
sudo systemctl restart farmpi-llm.service farmpi.service
sudo journalctl -u farmpi.service -u farmpi-llm.service -n 200 --no-pager
```

`farmpi.service` wants, but does not strictly require, the LLM unit. The API can remain reachable and report model unavailability instead of disappearing with the model process.

## Caddy and certificates

`config/Caddyfile` serves `farmpi.local`, uses Caddy's internal CA, enables compressed responses, and proxies to FastAPI on localhost.

Validate the active configuration:

```bash
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy.service
```

Install only Caddy's public root certificate on the Android device. The private CA key must remain on the Pi. If the Android app reports certificate trust failure, confirm:

- `farmpi.local` resolves to the Pi;
- Caddy is serving a certificate containing `farmpi.local`;
- the public Caddy root is installed and enabled for user certificates;
- the Android network-security configuration still permits the intended user trust anchor.

## Health checks

From the Pi:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/api/status
curl http://127.0.0.1:8080/health
```

From a trusted client:

```bash
curl https://farmpi.local/api/status
```

`/health` reports only that the application process is alive. `/api/status` separately reports application, database, and model state.

## Database maintenance and backup

Reapply migrations without a full update:

```bash
sudo bash ./scripts/apply-database-schema
```

Back up before material schema or identity changes:

```bash
sudo mariadb-dump --single-transaction farmpi > farmpi-backup.sql
```

Store backups outside the repository and protect them as operational data. Restoring a backup is an administrative operation and should be tested on a separate database before replacing an active prototype.

## Common failures

**Update stops because the checkout is dirty.** Inspect and commit or deliberately move the changes in the development environment. Do not force-reset a Pi that may contain unique work.

**`404 Unknown or inactive sensor node` for nodes E-P.** Reapply the database schema/seed; the ESP32 firmware is newer than the database registration.

**Database unavailable.** Check MariaDB, `/etc/farmpi/farmpi.env` ownership/permissions, and the `farmpi@127.0.0.1` credentials.

**Language model unavailable.** Check `FARMPI_LLAMA_URL`, the model service, model identifier, and `/api/status`. Learning questions return a limited useful fallback, while deterministic farm facts remain available when their dependencies are healthy.

From the Pi, verify an LM Studio connection and confirm the configured model identifier with `curl http://<development-pc-lan-ip>:1234/v1/models`. A successful response should list `qwen/qwen3.5-9b` for the current reference model.

**LM Studio/Qwen3.5 rejects the prompt.** Confirm FarmPi is launched through `app.main:app`; that composition root installs the compatibility adapter that combines system messages and applies `FARMPI_LLM_MODEL`.

**ESP32 TLS handshake fails.** Confirm mDNS resolution and that the client supplies `farmpi.local` as the TLS hostname/SNI even though it connects to the resolved IP.

**Phone cannot speak responses.** Use the Android settings diagnostics described in [Android client](android-client.md), confirm an English TTS voice is installed, and inspect Logcat with tag `FarmPiTTS`.

## Production limitations

This is a local prototype. Before production use, replace prototype bearer authentication and ESP32 `setInsecure()` with a managed device-trust design, define certificate/token rotation, establish monitored backups, test restore procedures, review network exposure, and remove synthetic seed behaviour that is inappropriate for real operations.
