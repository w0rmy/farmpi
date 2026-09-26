# Raspberry Pi deployment and operations

## Supported deployment shape

The checked-in deployment targets a Debian-family Raspberry Pi with:

- the FarmPi repository checked out by a normal service user;
- Python 3 and `venv`;
- MariaDB bound to localhost;
- Caddy serving `https://farmpi.local` with its internal CA;
- one normal management/home-LAN connection and one dedicated FarmPi wireless access-point profile, with the AP profile bound to the intended radio by MAC address rather than depending on a `wlanN` name;
- `farmpi.service` running Uvicorn on `127.0.0.1:8000`;
- `farmpi-llm.service` running Qwen3 1.7B through `llama-server` on `127.0.0.1:8080`.

The application can use a different OpenAI-compatible model server by setting `FARMPI_LLAMA_URL` and `FARMPI_LLM_MODEL`. If the model is hosted on another machine, permit only the required trusted LAN connection and do not expose the endpoint to the public Internet.

The current proof-of-concept deployment has been verified with no `FARMPI_LLAMA_URL` override, so the backend uses its default `http://127.0.0.1:8080`. The active Pi service runs `lmstudio-community/Qwen3-1.7B-GGUF:Q4_K_M` through `llama.cpp` with context 2048, reasoning disabled and one parallel slot. The development PC is therefore not required in the normal inference path.

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
3. creates `/etc/farmpi/farmpi.env` with generated database, ingest and administrator credentials;
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
FARMPI_ADMIN_TOKEN=<generated secret>
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

`FARMPI_ADMIN_TOKEN` is separate from the simulator ingest token and authorises physical-node registration/configuration through the administrator API. The Android Nodes screen should hold it only for the current administration session.

Never commit this file or copy its secrets into firmware source. Managed physical ESP32-S3 nodes use their own persisted per-device credential; do not reuse the administrator or shared simulator-ingest token as a device identity secret.

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

## FarmLAN wireless topology

The current proof-of-concept uses two Raspberry Pi Wi-Fi radios with separate roles:

- the management/home-LAN connection remains a normal Wi-Fi client connection;
- the dedicated FarmLAN profile is bound to the intended AP radio by its hardware MAC address so interface renaming does not change roles;
- the FarmLAN AP uses `10.42.0.1/24` on the Pi and NetworkManager shared mode provides local DHCP/DNS service;
- ESP32-S3 nodes and the Android test device join the FarmLAN;
- application clients continue to use `https://farmpi.local/` for the prototype because the current Caddy certificate contains the `farmpi.local` DNS SAN.

Using the fixed AP-side IP directly from firmware could remove mDNS from the node dependency chain, but doing so would also require the server certificate to contain that IP as a Subject Alternative Name. That hardening is deliberately deferred because it is unnecessary for the present proof of concept.

Do not document Wi-Fi passwords or device credentials in the repository. Interface names such as `wlan0`/`wlan1` may be useful diagnostics but are not the persistent role binding; the NetworkManager connection profile's MAC binding is authoritative.

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

**Language model unavailable.** Check `FARMPI_LLAMA_URL`, the model service, model identifier, and `/api/status`. Model-assisted informational/explanation requests should degrade clearly, while deterministic farm facts remain available when their dependencies are healthy.

From the Pi, verify an LM Studio connection and confirm the configured model identifier with `curl http://<development-pc-lan-ip>:1234/v1/models`. A successful response should list `qwen/qwen3.5-9b` for the current reference model.

**LM Studio/Qwen3.5 rejects the prompt.** Confirm FarmPi is launched through `app.main:app`; that composition root installs the compatibility adapter that combines system messages and applies `FARMPI_LLM_MODEL`.

**ESP32 TLS handshake fails.** Confirm mDNS resolution and that the client supplies `farmpi.local` as the TLS hostname/SNI even though it connects to the resolved IP.

**Phone cannot speak responses.** Use the Android settings diagnostics described in [Android client](android-client.md), confirm an English TTS voice is installed, and inspect Logcat with tag `FarmPiTTS`.

## Production limitations

This is a local prototype. Before production use, replace shared simulator bearer authentication and any remaining legacy insecure-client paths with a fully managed device-trust design, define certificate/token rotation and device-key recovery, establish monitored backups, test restore procedures, review network exposure, and remove synthetic seed behaviour that is inappropriate for real operations.
