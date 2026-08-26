# FarmPi

FarmPi is a local farm-monitoring alpha and capstone technical medium for Artificial Intelligence/Data Science and Flexible Learning. It deliberately produces a rich, believable **synthetic** dataset while keeping factual queries, calculations, and administration deterministic.

## Alpha stage: 16 virtual paddocks

One physical ESP32 now simulates Paddocks A–P. Each has its own registered sensor UID (test-moisture-a … test-moisture-p) and persistent per-paddock characteristics. It sends one complete node sample every 18.75 seconds; after 16 staggered HTTPS posts, one five-minute simulation round has elapsed. The synthetic day/weather model advances once per round, never once per post.

The generator includes a shared light/day cycle, rainfall events, pressure and wind, plus stable paddock differences (wetter/drier, warmer/cooler, shade, pH/EC, and pasture growth). Rain affects humidity, soil moisture, light, air temperature, leaf wetness, and pressure. Occasional pasture drops simulate grazing/cutting. This is useful test telemetry, **not an agronomic model** and not farming advice.

## Architecture and guardrails

```text
ESP32 virtual nodes → HTTPS ingest → FastAPI range validation → MariaDB
                                                     ↓
question/action router → reviewed deterministic operation → verified facts
                                                     ↓
                                          Qwen: concise language only
```

Qwen never receives database access, SQL, raw calculation responsibility, or authority to rename a paddock. It is a language interface, not the factual authority.

app/measurements.py is the reviewed measurement catalogue: canonical keys, labels, units, aliases, ranges, and permitted operations. The fields are:

- soil moisture; soil and air temperature; relative humidity; soil pH; soil EC;
- light; rainfall per sample interval; barometric pressure; wind speed/direction;
- pasture height; and leaf wetness.

No fabricated N/P/K values are used; soil EC is the practical raw soil-chemistry proxy.

## Supported deterministic interactions

- Current values for any supported measurement, including renamed paddocks: “What is the pasture height in North Flat?”
- Current moisture: driest, wettest, and farm average.
- Safe current rankings where listed in the catalogue, for example: “Which paddock is tallest?”
- Small historical calculations: “How much rainfall was there over the last 24 hours?”, “What is the pasture height change in North Flat over the last day?”, and min/max/average/change for permitted fields.
- Derived daylight hours from historical light_lux, counting five-minute samples at or above 1,000 lux. It is not an ingest field.
- Controlled rename: “Rename Paddock A to North Flat”, followed by “confirm” or “yes” in the same browser within five minutes.

Weather forecasts, irrigation decisions, causal claims, agronomic recommendations, LoRaWAN, MQTT, OTA, and control actions are intentionally unavailable.

## Rename safety

FarmPi resolves the source name against the active database paddock, validates the new display name, rejects duplicates, asks for confirmation, then updates paddocks.name and writes paddock_admin_audit. Readings remain linked to numeric paddocks.id/sensor_nodes.id; historical rows are neither rewritten nor orphaned. Dynamic lookup means North Flat, Back Hill, and other current names work in questions.

## Install and update

```bash
git clone git@github.com:w0rmy/farmpi.git ~/farmpi
cd ~/farmpi
./update
sudo bash ./scripts/setup-database
```

./update performs a fast-forward pull, installs requirements, compiles and tests Python, reapplies the additive/idempotent schema, and restarts the services. It stops if the deployment clone has local changes.

## ESP32 configuration

Copy firmware/esp32-sensor/config.example.h to firmware/esp32-sensor/config.h, then set only:

- WIFI_SSID and WIFI_PASSWORD;
- DEVICE_HOSTNAME;
- FARMPI_INGEST_TOKEN from /etc/farmpi/farmpi.env.

config.h is ignored. Do not commit Wi-Fi credentials or the bearer token. The generator's 16 UIDs are compiled into the sketch and seeded by the database.

The sketch preserves Wi-Fi reconnects, mDNS lookup, bearer authentication, serial diagnostics, retry-on-next-round behaviour, and the previous TLS/SNI fix: it connects to the mDNS-resolved IP while supplying farmpi.local as the TLS hostname. It uses setInsecure() only for the prototype's private-CA ESP32 path.

## Capstone evidence

The implementation and evidence are documented in:

- [sensor ingest and simulation](docs/sensor-ingest.md)
- [database layer and migration](docs/database-layer.md)
- [grounding and guardrails](docs/grounding-and-guardrails.md)
- [Flexible Learning guidance](docs/flexible-learning.md)
- [paddock administration](docs/paddock-admin.md)
- [firmware guide](firmware/esp32-sensor/README.md)
- [latency method](docs/latency-optimization.md)

The main lesson is architectural: small local models become more useful when deterministic software owns measurements, calculations, safety boundaries, and mutations, while the model owns understandable language.
