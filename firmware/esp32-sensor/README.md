# ESP32 synthetic telemetry generator

The current firmware is a development and evaluation generator, not a deployed agronomic sensor product. One ESP32 represents 16 stable virtual paddock nodes and sends coherent, explicitly simulated telemetry to FarmPi. Its purpose is to provide repeatable data for the learning platform, analytics, provenance, and UI evaluation without implying that fabricated measurements came from physical sensors.

## Behaviour

- node UIDs are `test-moisture-a` through `test-moisture-p`;
- one node is sent every 18.75 seconds, making a five-minute 16-node round;
- values share a New Zealand seasonal/daylight/weather state plus stable paddock differences;
- every payload sets `simulated=true`;
- FarmPi supplies authoritative UTC in the ingest acknowledgement;
- `sample_seq` permits safe retry/deduplication;
- Wi-Fi, mDNS, HTTPS bearer authentication, retries, and serial diagnostics are retained.

The generated measurement fields and time/sequence rules are documented in [Data and API](../../docs/data-and-api.md). The implementation is in `esp32-sensor.ino`; that file is the authority for exact simulation formulae and timing.

## Configure

Copy `config.example.h` to `config.h`. The resulting file is ignored by Git. Set at least:

```c
#define WIFI_SSID "your network"
#define WIFI_PASSWORD "your password"
#define DEVICE_HOSTNAME "farmpi-sensor-a"
#define FARMPI_INGEST_TOKEN "value from /etc/farmpi/farmpi.env"
#define VIRTUAL_PADDOCK_COUNT 16
#define SIMULATION_ROUND_MS 300000UL
#define NZ_SIMULATION_LATITUDE -37.7870f
#define NZ_SIMULATION_LONGITUDE 175.2793f
```

Never commit `config.h`, credentials, bearer tokens, private keys, or exported serial logs containing secrets. The token must match `FARMPI_INGEST_TOKEN` on the Pi.

## Prepare FarmPi

Install/update the Pi application, apply `config/database/schema.sql`, and run `config/database/seed.sql` before the first firmware upload. The seed creates the expected virtual node identities. Re-running it preserves an existing paddock display-name change because relationships use numeric IDs and stable node UIDs.

Confirm the phone/PC can reach `https://farmpi.local/health` and that the ESP32 network can resolve `farmpi.local` before troubleshooting firmware.

## Build and upload

Open `esp32-sensor.ino` in Arduino IDE with ESP32 board support installed, select the actual board and serial port, then compile and upload. The sketch uses ESP32 core libraries (`WiFi.h`, `WiFiClientSecure.h`, `ESPmDNS.h`) and does not currently have a repository CI build.

After restart, inspect serial output for Wi-Fi connection, FarmPi address resolution, HTTP status, accepted/deduplicated state, and clock synchronisation. Check `/api/status` and query the latest value through FarmPi rather than assuming that a successful HTTP request created the expected database row.

## HTTPS prototype boundary

The sketch resolves the Pi address but presents `farmpi.local` as the TLS hostname so Caddy receives the correct SNI value. The current `setInsecure()` use accepts the private development certificate without validating its chain. That is a documented prototype compromise on a trusted local network, not production TLS practice. A deployment beyond the controlled prototype must install/pin an appropriate CA or server identity.

## Scope control

LoRa, physical sensor calibration, enclosures, battery management, and production fleet management are not implemented. Add them only when they materially support a defined learning/elective/graduate-profile outcome. More IoT hardware is not capstone progress by itself; see [Capstone outcome governance](../../docs/capstone-governance.md).
