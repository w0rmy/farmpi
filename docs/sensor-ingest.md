# Sensor ingest and synthetic-farm simulation

POST /api/ingest accepts one complete virtual-node sample over HTTPS. Authentication remains a single local alpha bearer token held only in /etc/farmpi/farmpi.env. FastAPI validates every value against app/measurements.py and assigns the UTC server timestamp; ESP32s do not need a real-time clock.

The required payload has sensor, simulated, and these instantaneous values: soil_moisture_pct (0–100), soil_temperature_c (-10–60°C), air_temperature_c (-30–60°C), relative_humidity_pct (0–100), soil_ph (0–14), soil_ec_ms_cm (0–20 mS/cm), light_lux (0–200,000), rainfall_mm (0–100 per sample interval), barometric_pressure_hpa (850–1100), wind_speed_kmh (0–250), wind_direction_deg (0–360), pasture_height_cm (0–300), and leaf_wetness_pct (0–100).

## One ESP32, 16 nodes

The sketch owns Paddocks A–P, using sensor UIDs test-moisture-a through test-moisture-p. It posts exactly one node every 18,750 ms and completes each node's sample cycle in five minutes. Failed posts are diagnosed on serial output and retried during that node's next round; they do not stop later nodes.

Existing four-node installations are expanded by the normal `./update` database migration. A `404 Unknown or inactive sensor node` response for test-moisture-e or later means the firmware is already running the 16-node loop but the server has not yet applied that migration. The repeatable seed keys this upgrade by stable sensor UID, preserving current paddock names and historical relationships.

The generator has shared weather and persistent per-paddock state. Rainfall events raise humidity, moisture, and leaf wetness; they reduce light and air temperature and bring pressure downward. Paddocks retain stable moisture, shade, temperature, pH, EC and growth differences. Pasture grows slowly and rarely drops sharply. The result is correlated synthetic test telemetry, not a prediction or agronomic model.

The global clock is advanced only immediately before Paddock A begins a new 16-post round. This avoids the earlier conceptual error of advancing an entire day after every HTTP request.

## TLS/SNI and timestamp lessons

The ESP32 resolves farmpi.local by mDNS, connects to that resolved IP, and explicitly supplies farmpi.local as the TLS hostname. This SNI detail matters because Caddy selects its HTTPS site by hostname; connecting only by IP caused the prior handshake failure. setInsecure() still encrypts traffic but does not validate Caddy's private CA, a bounded alpha compromise.

MariaDB DATETIME values are application-convention UTC. The repeatable seed is deliberately dated 2026-01-01 UTC, and removes the old 2026-08-26 local-looking seed timestamp, so accepted server-timestamped telemetry always becomes current.

Daylight hours are not ingested. They are derived from historical light_lux by deterministic application code.

## Validation

After flashing, expect HTTP 201 Created in serial output, then ask current, rain, height and EC questions. Confirm simulated provenance appears. Test an unavailable request such as irrigation advice to verify that FarmPi refuses to invent it.
