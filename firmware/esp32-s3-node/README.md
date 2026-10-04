# ESP32-S3 managed FarmPi node

Both ESP32-S3 boards run the same managed-node firmware. A board discovers FarmPi,
authenticates with its persisted per-device credential, pulls one complete desired
configuration, validates its SHA-256 fingerprint, persists the last-known-good
configuration in NVS, and acknowledges what it applied.

## Time source

FarmPi itself is the managed node's application time authority. The node does not
treat `farmpi.local` as an NTP server and does not require Internet time. Every
successful `POST /api/nodes/contact` response already carries authoritative
`server_time`; the firmware validates that Unix time and applies it with
`settimeofday()` when its local clock is invalid or differs by more than five
seconds.

Telemetry retains the existing safety guard and is deferred until the node has a
valid clock. Contact remains every 15 seconds and telemetry remains every 60
seconds.

## Sensor modes

Each catalogue measurement has exactly one mode:

- `OFF` — no value is produced.
- `SIMULATED` — the ESP32 generates a bounded test value at the sensor-driver
  boundary and sends it through the normal authenticated telemetry path.
- `LIVE` — requires an implemented physical driver advertised in `LIVE_MEASUREMENTS`; unsupported LIVE configuration is rejected.

The managed profile exposes all 13 catalogue keys for simulation and currently advertises one LIVE driver: `soil_moisture_pct` from a Jaycar/Duinotech XC4604 analogue probe connected to ESP32-S3 GPIO4 (ADC1).

For the current prototype, the XC4604 uses a **relative coco-moisture prototype scale** with retained firmware endpoints of raw 1000 = 0% and raw 2200 = 100%, clamped to that range. The first medium-specific calibration used provisional endpoints of 1066/1955 from the retained dry-coco median and the first three saturated-coco readings. Further saturated-coco testing showed the upper endpoint needed to move higher; the retained 1000/2200 values are engineering endpoints, not the directly measured median and mean. This is not volumetric water content or an agronomic calibration. It improves the usefulness of the displayed prototype percentage while preserving the real probe → ADC → managed telemetry path. T01 remains incomplete until all six required physical measurements have been demonstrated from real hardware.

### Synthetic profile

Firmware version `0.3.4-xc4604-coco-cal` retains the realistic simulation profile, the first physical LIVE acquisition path, and the coco-relative calibration. The simulator itself still replaces the earlier one-hour sine-wave generator. The managed node now builds synthetic values from the FarmPi-synchronised clock using a representative Hamilton/Waikato profile:

- light follows calculated sunrise, sunset and solar elevation for the current day of year and the NZ daylight-saving rule;
- air temperature follows a seasonal daily low/high profile with a normal day/night cycle;
- soil temperature uses a smaller, delayed daily cycle;
- humidity generally moves opposite daytime heating and increases with synthetic cloud/rain;
- soil moisture changes over multi-day periods and responds gradually to deterministic synthetic rain events, then dries slowly;
- barometric pressure, wind speed and direction change over multi-day synthetic weather-like periods rather than every hour;
- pH and EC change only very slowly;
- pasture height follows a slow growth/grazing-style cycle;
- leaf wetness is high during synthetic rain and overnight and falls through daylight.

Node-specific offsets keep two managed boards from reporting identical values. The profile is for visually and functionally realistic **test telemetry only**. It is not a Hamilton weather record, forecast, soil-water model, pasture model or agronomic recommendation.

A managed sample may contain only the measurements that produced values. The
server derives per-measurement provenance from the acknowledged configuration;
the ESP32 does not get to relabel a LIVE value as simulated or vice versa.

## Identity

Three identities remain separate:

- hardware UID — immutable ESP32/eFuse identity;
- FarmPi logical ID — stable ID such as `FP-001`;
- assigned location — farmer-defined name such as `Bob's`, `Back Hill`, or
  `Down by the Trough`.

Moving a node to another location does not change its hardware or FarmPi identity.

See [setup, contract and hardware evidence checklist](../../docs/s3-node-bringup.md).

The older `../esp32-sensor` sketch remains an explicit 16-location test/demo
generator. It is no longer the normal operational database baseline.

Source-mode changes can be made from Android Node Detail or from `scripts/configure-node-modes`. Both paths update the same desired configuration and fingerprint contract. Android enables LIVE only when this firmware advertises a matching physical driver. See the [upgrade procedure](../../docs/s3-node-bringup.md) when replacing the six-key profile.
