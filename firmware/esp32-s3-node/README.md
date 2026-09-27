# ESP32-S3 managed FarmPi node

Both ESP32-S3 boards run the same managed-node firmware. A board discovers FarmPi,
authenticates with its persisted per-device credential, pulls one complete desired
configuration, validates its SHA-256 fingerprint, persists the last-known-good
configuration in NVS, and acknowledges what it applied.

## Sensor modes

Each standard measurement has exactly one mode:

- `OFF` — no value is produced.
- `SIMULATED` — the ESP32 generates a bounded test value at the sensor-driver
  boundary and sends it through the normal authenticated telemetry path.
- `LIVE` — the firmware asks the physical driver for a value. A measurement in
  LIVE mode reports nothing until that driver and probe are implemented.

The standard profile currently exposes soil moisture, soil temperature, air
temperature, relative humidity, ambient light and barometric pressure. This does
**not** claim that six physical probes are fitted. T01 remains incomplete until
all six measurements have been demonstrated from real hardware.

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
