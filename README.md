# FarmPi

## Repository structure

- `app/` — Raspberry Pi/FastAPI application, deterministic logic, and API layer.
- `firmware/` — embedded ESP32 sensor/simulator firmware.
- `clients/android/` — native Kotlin/Jetpack Compose user client.
- `config/`, `tests/`, `docs/`, and `scripts/` — deployment configuration, validation, evidence, and repeatable operational helpers.

See [the time-sync contract](docs/time-sync-telemetry.md), [NZ synthetic simulation](docs/nz-synthetic-simulation.md), [deterministic analytics and graphs](docs/analytics-and-graphing.md), [educational grounding](docs/educational-grounding.md), [structured requests](docs/structured-requests.md), and [Android architecture](docs/android-client.md). Editable Mermaid diagram sources are in [docs/diagrams](docs/diagrams/).

FarmPi is a local farm-monitoring alpha and capstone technical medium for Artificial Intelligence/Data Science and Flexible Learning. It deliberately produces a rich, believable **synthetic** dataset while keeping factual queries, calculations, and administration deterministic.

## Alpha stage: 16 virtual paddocks

One physical ESP32 now simulates Paddocks A–P. Each has its own registered sensor UID (test-moisture-a … test-moisture-p) and persistent per-paddock characteristics. It sends one complete node sample every 18.75 seconds; after 16 staggered HTTPS posts, one five-minute simulation round has elapsed. The synthetic day/weather model advances once per round, never once per post.

The generator includes a synchronized real-time Waikato/NZ seasonal daylight cycle, monthly climate baselines, rainfall events, pressure and wind, plus stable paddock differences (wetter/drier, warmer/cooler, shade, pH/EC, and pasture growth). Rain affects humidity, soil moisture, light, air temperature, leaf wetness, and pressure. Occasional pasture drops simulate grazing/cutting. This is useful test telemetry, **not an agronomic model** and not farming advice.

## Architecture and guardrails

```text
ESP32 virtual nodes → HTTPS ingest → FastAPI range validation → MariaDB
                                                     ↓
question/action router → reviewed deterministic operation → verified facts
                                                     ↓
                                          Qwen: concise language only
```

Spoken questions have one additional deterministic step before the question/action router:

```text
browser speech-to-text (en-NZ, up to five alternatives)
        ↓
FarmPi domain normaliser (measurement vocabulary + active paddock names)
        ↓
deterministic router/action layer → grounding → Qwen language response
```

The browser remains responsible for speech recognition. Browser phrase/context biasing is inconsistent across devices and browsers, so FarmPi does not rely on it for correctness. `app/speech_normalizer.py` instead performs a small, explainable correction pass without using Qwen. It can choose a clearly more farm-consistent browser alternative and fixes the observed `Patek` → `paddock` transcription only when the surrounding wording is farm-related. Typed text bypasses this step unchanged.

The first usability finding was that phone dictation sometimes heard *paddock* as *Patek*, leading to poor routing and irrelevant responses. When FarmPi changes a spoken transcript, the interface shows both **Heard** and **Interpreted** text. This makes speech-engine errors distinguishable from FarmPi's deterministic interpretation during evaluation.

Qwen never receives database access, SQL, raw calculation responsibility, or authority to rename a paddock. It is a language interface, not the factual authority.

app/measurements.py is the reviewed measurement catalogue: canonical keys, labels, units, aliases, ranges, and permitted operations. The fields are:

- soil moisture; soil and air temperature; relative humidity; soil pH; soil EC;
- light; rainfall per sample interval; barometric pressure; wind speed/direction;
- pasture height; and leaf wetness.

No fabricated N/P/K values are used; soil EC is the practical raw soil-chemistry proxy.

## Supported deterministic interactions

- Farm-wide inventory: “How many paddocks are we monitoring?” and “How many sensor nodes are active?” return active configuration counts, separately identifying inactive/historical paddock records where applicable.
- Current paddock overview: “What stats are available on Paddock B?”, “What data do we have for Paddock B?”, and “Tell me about Paddock B” return the central measurement catalogue's latest verified values, timestamp, and provenance.
- Natural paddock aliases: `Paddock 1`, `Paddock two`, and `Paddock number 2` map to the active configured order. The stable identity survives a rename, so the second paddock remains `Paddock 2` even if Paddock B becomes North Flat.
- Short contextual follow-ups: after “What is the temperature in Paddock A?”, “What about Paddock 2?” retrieves air temperature for the second configured paddock using the API's opaque conversation token.
- Current values for any supported measurement, including renamed paddocks: “What is the pasture height in North Flat?”
- Current moisture: driest, wettest, and farm average.
- Safe current rankings where listed in the catalogue, for example: “Which paddock is tallest?”
- Expanded historical calculations: totals, min/max/average, change, range, deterministic first-to-last trend, simple baseline anomaly flagging, comparison bars, and time-series charts. Examples: “Compare soil EC across all paddocks.” and “Show a graph of soil moisture over the last 24 hours.”
- Curated concept explanations at Simple/Normal/Technical levels: “What does soil EC mean?”, “Explain simulated data.”, and “What are observed and received times?”
- Learner evidence: returned charts include the selected time period/provenance and a bounded list of measurements used.
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

./update performs a fast-forward pull, installs requirements, compiles and tests Python, reapplies the additive/idempotent schema, runs the rename-safe 16-node prototype data migration, and restarts the services. It stops if the deployment clone has local changes. Existing four-node installations are expanded to Paddocks A–P without moving an existing sensor away from a paddock that has been renamed.

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
- [speech recognition and domain normalisation](docs/flexible-learning.md#speech)
- [paddock administration](docs/paddock-admin.md)
- [firmware guide](firmware/esp32-sensor/README.md)
- [latency method](docs/latency-optimization.md)
- [analytics, chart, and evidence contract](docs/analytics-and-graphing.md)
- [educational content and teach-by-doing design](docs/educational-grounding.md)
- [structured request model](docs/structured-requests.md)
- [testing and nontechnical evaluation plan](docs/testing-and-evaluation.md)

The main lesson is architectural: small local models become more useful when deterministic software owns measurements, calculations, safety boundaries, and mutations, while the model owns understandable language.
