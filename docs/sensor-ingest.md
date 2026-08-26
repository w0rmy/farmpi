# FarmPi ESP32 sensor ingest

## Purpose

This stage proves the device-to-database path using a real ESP32 over Wi-Fi while deliberately using synthetic sensor values. The aim is to validate the FarmPi data architecture without expanding the capstone into a physical-sensor engineering project.

The ESP32 behaves as though it were a real field sensor node:

```text
ESP32
  ↓ synthetic soil-moisture value
Wi-Fi
  ↓ HTTPS POST /api/ingest
FastAPI validation and lightweight bearer-token authentication
  ↓
MariaDB readings
  ↓
deterministic farm-data functions
  ↓
minimal verified grounding context
  ↓
Qwen3 0.6B
  ↓
natural-language answer
```

Only the source of the measurement is synthetic. The networking, server validation, database insertion, deterministic calculation, grounding, and LLM response path are the same path intended for later real sensor readings.

## API

`POST /api/ingest`

Example body:

```json
{
  "sensor": "test-moisture-a",
  "soil_moisture_pct": 17.82,
  "simulated": true
}
```

The `sensor` value must match an active `sensor_nodes.node_uid`. Soil moisture is validated as a numeric value from 0 through 100 inclusive. FarmPi timestamps the reading on the server in UTC so the prototype ESP32 does not need a real-time clock.

A successful submission returns HTTP `201 Created` with the stored reading id, sensor, paddock, value, simulation flag, and timestamp.

## Timestamp convention

FarmPi stores application-generated `readings.recorded_at` values as UTC in the MariaDB `DATETIME(6)` column. The value is timezone-naive in MariaDB, so the application convention is important: all new readings written through `/api/ingest` are UTC.

An early alpha seed used `2026-08-26 18:00:00` as a fixed baseline timestamp. Because that seed looked like local New Zealand time while ingest values were stored as UTC, the seed could sort later than a newly ingested reading on the same date. This caused the deterministic "latest reading" query to keep selecting the seed value even though the ingest endpoint had accepted a newer measurement.

The seed has been corrected to an intentionally old UTC baseline timestamp (`2026-01-01 00:00:00`) and the seed script removes the original `2026-08-26 18:00:00` rows on existing alpha installations. This preserves the intended rule: any subsequently ingested sensor reading supersedes the baseline seed.

## Prototype authentication

The endpoint uses one FarmPi-wide bearer token:

```text
Authorization: Bearer <token>
```

`scripts/setup-database` generates the token and stores it in `/etc/farmpi/farmpi.env` as `FARMPI_INGEST_TOKEN`. The token is deliberately lightweight authentication for the local alpha/test network. Per-device credentials, certificate provisioning, key rotation, and device PKI are outside the current capstone scope.

Display the token on FarmPi with:

```bash
sudo grep '^FARMPI_INGEST_TOKEN=' /etc/farmpi/farmpi.env
```

## Simulation provenance

The `readings` table includes a `simulated` boolean. Seed readings and synthetic ESP32 readings are stored with `simulated = TRUE`.

The deterministic grounding layer carries that provenance forward. When a result uses a simulated latest reading, the facts supplied to Qwen explicitly state that the result includes simulated test data. This avoids presenting synthetic measurements as real farm observations.

## Firmware

The firmware lives in the same repository under:

```text
firmware/esp32-sensor/
```

This keeps the capstone as one monorepo while preserving a clear boundary between Raspberry Pi application code and embedded firmware.

The test firmware:

- joins Wi-Fi;
- resolves `farmpi.local` using mDNS;
- produces a small random-walk moisture value;
- sends every 30 seconds;
- marks the value as simulated;
- retries after Wi-Fi or server failure;
- prints status information over serial.

The random walk is intentionally more realistic than an unrelated random value on every sample. Its purpose is only to generate changing telemetry for the data path.

## TLS scope

The ESP32 uses TLS but calls `WiFiClientSecure::setInsecure()`, so it does not validate Caddy's private-CA certificate. This is a deliberate prototype simplification. The user-facing browser path continues to use trusted HTTPS through Caddy's internal CA.

The first ESP32 integration attempt successfully resolved `farmpi.local` through mDNS but then opened TLS using only the resolved IP address. Caddy serves the HTTPS site as `farmpi.local`, so the TLS handshake also needs that hostname as Server Name Indication (SNI). Disabling certificate validation with `setInsecure()` bypasses certificate verification, but it does not remove Caddy's need to know which hostname/site the client is requesting.

The firmware now connects to the mDNS-resolved IP while explicitly supplying `farmpi.local` as the TLS hostname/SNI value. It also reports the underlying TLS error on the serial console if a handshake still fails. This preserves the current HTTPS architecture without introducing certificate provisioning on the ESP32.

For this capstone stage, certificate provisioning on embedded nodes would add engineering work without materially improving demonstration of the two target elective areas.

## Validation sequence

After deploying the server changes and flashing the ESP32:

1. Confirm the serial console reports HTTP `201 Created`.
2. Confirm a new row appears in MariaDB with `simulated = 1`.
3. Confirm the new row has a later UTC `recorded_at` value than the baseline seed.
4. Ask FarmPi for the named paddock's current soil moisture.
5. Ask `Which paddock is driest?` and verify the answer changes when the synthetic reading changes enough to alter the deterministic result.
6. Confirm unsupported questions still return unavailable information rather than fabricated values.

This demonstrates a complete chain from a physical networked device to a grounded AI response while keeping the farm functionality deliberately minimal.

## Scope boundary

Once this path is proven, FarmPi does not need additional farm-device sophistication for the capstone. The next major development focus should shift to the Flexible Learning component: user profiles, explanation depth, onboarding, guidance, presentation preferences, and evaluation with a nontechnical user.
