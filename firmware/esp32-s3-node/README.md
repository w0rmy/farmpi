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

The managed profile exposes all 13 catalogue keys for simulation and advertises no LIVE drivers. This does
**not** claim that physical probes are fitted. T01 remains incomplete until
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

Source-mode changes can be made from Android Node Detail or from `scripts/configure-node-modes`. Both paths update the same desired configuration and fingerprint contract. Android enables LIVE only when this firmware advertises a matching physical driver. See the [upgrade procedure](../../docs/s3-node-bringup.md) when replacing the six-key profile.
