# Two ESP32-S3 node configuration bring-up

This block prepares registration and configuration before real probe acquisition. It does not complete T01. FarmPi Needs and Requirements v1.3 still requires six physical measurements with location, source, observation time, measurement identity, units and physical/simulated distinction.

## Live bring-up status - 26 September 2026

Two ESP32-S3 N16R8 boards have now been flashed with the managed-node firmware and exercised against the live FarmPi deployment. Both boards joined the dedicated FarmLAN and reached the managed discovery/registration path. The Android Nodes workflow was then used to connect/register the nodes with FarmPi. This verifies the physical discovery/administrative registration path beyond the earlier compile-only evidence.

Observed hardware UIDs during bring-up were `7c4fadb633c0` and `7c4fadb52c40`. Hardware UID remains identification rather than a secret. Final assigned FarmPi node IDs, desired/applied full fingerprints and screenshots should still be captured in the formal evidence record before claiming the complete two-board checklist.

Two hardware faults/bring-up conditions were also isolated:

- One newly flashed board reported `phy_init: store_cal_data_to_nvs_handle: store calibration data failed(0x1105)`. A deliberate full-flash erase followed by reflashing cleared the condition and the node then reached `Awaiting registration`. Normal subsequent firmware uploads should preserve NVS; full erase is a provisioning/recovery action, not the routine update path.
- A second bring-up produced a repeating lwIP `sys_untimeout` assertion stating `Required to lock TCPIP core functionality!`. The apparent network-stack fault was traced to an unintended breadboard connection. Removing that connection stopped the reboot loop. The software/network stack was therefore not changed to mask a physical wiring fault.

These results do not constitute physical sensing evidence. No real probe reading has yet been claimed here, and T01 remains incomplete until all six FR01 physical measurements are demonstrated with required provenance.


## What exists

The existing `sensor_nodes`, catalogue, readings table, `/api/ingest`, database connection layer and Android HTTPS client are extended. The old `firmware/esp32-sensor` remains the explicitly simulated 16-node generator. The new `firmware/esp32-s3-node` target is a physical configuration client; it never generates readings. Both physical boards use the same binary and network configuration. UID is read from factory eFuse MAC and an independently generated device key is persisted in NVS; the server stores only its SHA-256 hash.

The S3 bring-up profile understands soil-moisture enablement only and has no acquisition driver. The Android screen shows all 13 catalogue entries, with unsupported capabilities disabled. Enabling soil moisture produces **CONFIGURED BUT NOT REPORTING** until the real identified probe driver exists. Do not equate configuration support with a working sensor.

## Software setup

1. Back up the MariaDB database before applying `config/database/schema.sql` through the existing update workflow. This change preserves existing rows and relaxes old baseline NOT NULL columns. It adds registration/configuration fields to sensor_nodes and captures paddock_id in readings. The initial backfill uses the assignment known at migration time; it cannot reconstruct location changes that predate this migration. Run the schema twice on a disposable MariaDB copy and compare counts before live deployment. MariaDB execution remains an outstanding integration check.
2. The updated `scripts/setup-database` preserves or generates `FARMPI_ADMIN_TOKEN` in the existing protected environment file. On an existing installation that only runs the schema update, add a separately generated administrator token to `/etc/farmpi/farmpi.env` and restart FarmPi. Do not reuse the ingest token. The Android Nodes screen holds this token only for its current screen session. No secrets belong in Git or evidence logs.
3. Build/install the Android client, open **Nodes**, enter the administrator token and refresh. The earlier managed-environment Gradle attempt failed before Kotlin compilation because Gradle could not establish a loopback connection, but the live Android Nodes workflow has since been exercised successfully against FarmPi for S3 discovery/registration. Preserve both records: the earlier build failure is development evidence and the later device use is live integration evidence.
4. Copy `firmware/esp32-s3-node/config.example.h` to `config.h`; set Wi-Fi and the FarmPi HTTPS address. Paste the existing Caddy local root CA certificate. The physical target verifies TLS. It also needs a trusted clock for certificate validation: provide a reachable local NTP service at `farmpi.local` before first connection. The repository’s existing Pi setup does not currently install an NTP server; verify this prerequisite explicitly. No Internet time service is required.
5. Compile with Arduino ESP32 core **3.3.11** and ArduinoJson **7.4.2**. The verified compile target is `esp32:esp32:esp32s3:FlashSize=16M,PSRAM=opi,PartitionScheme=app3M_fat9M_16MB`. Jeremy identified the modules as ESP32-S3 N16R8. This target matches 16 MB quad flash and 8 MB octal PSRAM for the WROOM-1 N16R8 variant. Two boards have now been flashed and reached the live FarmPi registration path; exact carrier/pin/probe details still need to be established before acquisition-driver wiring.
6. Upload the same image to both boards with **Erase All Flash disabled** for normal updates so NVS identity/configuration survives. During first live provisioning, one board required a deliberate full-flash erase to clear an NVS/PHY calibration-storage failure before registration could proceed. Treat full erase as provisioning/recovery only: erasing the device key requires deliberate administrative recovery, and the server will reject an unknown replacement key for an existing hardware UID rather than silently reassign identity.

## Configuration contract

Device contact: `POST /api/nodes/contact` with hardware_uid, device_key, firmware_version, board_profile, capabilities and optional applied_fingerprint. Unknown devices appear pending. Discovery cannot approve itself. `POST /api/nodes/{id}/approve`, using the administrator bearer token, assigns node UID and starts with `enabled: []`. Node IDs derive from existing numeric row IDs; seeded simulator rows may mean the first physical node is `node-017`, not `node-001`. Names are editable; IDs remain stable.

The canonical document contains exactly `enabled` (sorted, unique catalogue keys), `node_uid`, and numeric `schema_version: 1`. JSON uses sorted keys and compact ASCII separators. SHA-256 over those exact bytes is authoritative; the UI shows its first eight hexadecimal characters only. Location, friendly name and firmware diagnostics are separate from sensor configuration and do not select GPIOs.

`PUT /api/nodes/{id}/configuration` accepts name, paddock_id, enabled and expected_fingerprint. It rejects unsupported capabilities and stale edits. The device compares fingerprints during each 15-second contact, requests the complete latest document with `POST /api/nodes/configuration`, checks schema/identity/capabilities/canonical bytes/hash, persists it, applies it and sends `/api/nodes/ack`. It never requests intermediate revisions. Acknowledgements for a superseded unknown configuration return 409; the device fetches latest on its next contact. A lost current acknowledgement is repaired by the next contact.

The firmware has two NVS configuration slots. It writes and reads back the inactive complete document before switching the selector. Boot validates the selected document and can fall back to the other valid slot. A rejected candidate does not replace the active state. Physical reboot, power interruption and network-loss behaviour still require hardware evidence; a successful compile does not prove NVS recovery.

Sync is derived: matching desired/applied hashes = IN SYNC; failure for the current desired hash = UPDATE FAILED; otherwise UPDATE PENDING. An old failure cannot mark a newer desired state failed. Per-sensor reporting uses its last actual observation with a ten-minute freshness policy; node contact does not invent readings.

## Sparse physical telemetry

The future acquisition driver will use the existing `/api/ingest` with sensor (assigned UID), hardware_uid, device_key, applied_fingerprint, location_epoch, simulated=false, clock_valid=true, device_time_unix, persistent sample_seq and only actual measurement values. The current bring-up firmware intentionally sends no telemetry.

Managed ingestion requires authenticated registered identity, assigned active location, acknowledged configuration, catalogue membership, capability and enablement in both desired and applied state. It rejects simulated submissions from physical nodes, invalid types/ranges, missing or future observation times, duplicate sequences with changed content, and stale location assignment epochs. Exact retries return the original sample. The next driver must persist sequence allocation across reboot; this block does not claim a working offline observation queue.

The server returns location_epoch in contact responses. A later driver must associate that epoch with each captured sample. Relocation increases it, and old-epoch arrivals are rejected for explicit reconciliation rather than silently placed in the new location. Already stored history uses its captured paddock_id. Existing valid delayed observation times are retained. Legacy simulator ingest remains explicitly simulated and cannot impersonate a managed physical node using only the shared ingest token.

## Two-board evidence checklist

Record source revision, toolchain versions, binary SHA-256, hardware UIDs, assigned node IDs, UTC times, desired/applied full hashes and screenshots/serial output without credentials.

1. Power on both boards without probes. Verify two pending entries, distinct hardware UIDs and no observations.
2. Register both; verify separate assigned UIDs, all 13 disabled and both IN SYNC after pulling the initial empty configuration.
3. Enable soil moisture only on the first node. Verify its desired hash changes, UPDATE PENDING transitions to IN SYNC, and its runtime state is CONFIGURED BUT NOT REPORTING. Verify the second node’s configuration/hash stays unchanged and IN SYNC.
4. Disconnect the first node, change its desired state repeatedly, reconnect, and verify it pulls only the latest complete state.
5. Reboot with FarmPi unreachable; record restoration of the same valid saved configuration. Reconnect and verify acknowledgement recovery.
6. Exercise invalid schema, unsupported measurement, corrupted fingerprint and failed persistence in a controlled test build. Verify the working document remains intact. Interrupt power during persistence and inspect both slots after reboot.
7. Verify location reassignment leaves old history in its original location. Verify disabled/unsupported/cross-node/simulated physical submissions are rejected and exact retry is idempotent using the test fixture; do not label fixture data as physical probe evidence.

Only after this path passes should the actual probe/module be identified, wiring standardised in board_profile.h, its driver/calibration added and one real soil-moisture channel tested. T01 remains incomplete until all six FR01 measurements are demonstrated physically.

## References

* [Espressif WROOM-1 module memory variants](https://www.espressif.com/sites/default/files/documentation/esp32-s3-wroom-1_wroom-1u_datasheet_en.pdf)
* [Espressif Preferences persistence API](https://docs.espressif.com/projects/arduino-esp32/en/latest/api/preferences.html)
* [ArduinoJson 7 deserialization API](https://arduinojson.org/v7/api/json/deserializejson/)
