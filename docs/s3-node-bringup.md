# Two ESP32-S3 node configuration bring-up

This block prepares registration and configuration before real probe acquisition. It does not complete T01. FarmPi Needs and Requirements v1.3 still requires six physical measurements with location, source, observation time, measurement identity, units and physical/simulated distinction.

## Live bring-up status - 26 September 2026

Two ESP32-S3 N16R8 boards have now been flashed with the managed-node firmware and exercised against the live FarmPi deployment. Both boards joined the dedicated FarmLAN and reached the managed discovery/registration path. The Android Nodes workflow was then used to connect/register the nodes with FarmPi. This verifies the physical discovery/administrative registration path beyond the earlier compile-only evidence.

Observed hardware UIDs during bring-up were `7c4fadb633c0` and `7c4fadb52c40`. Hardware UID remains identification rather than a secret. Final assigned FarmPi node IDs, desired/applied full fingerprints and screenshots should still be captured in the formal evidence record before claiming the complete two-board checklist.

Two hardware faults/bring-up conditions were also isolated:

- One newly flashed board reported `phy_init: store_cal_data_to_nvs_handle: store calibration data failed(0x1105)`. A deliberate full-flash erase followed by reflashing cleared the condition and the node then reached `Awaiting registration`. Normal subsequent firmware uploads should preserve NVS; full erase is a provisioning/recovery action, not the routine update path.
- A second bring-up produced a repeating lwIP `sys_untimeout` assertion stating `Required to lock TCPIP core functionality!`. The apparent network-stack fault was traced to an unintended breadboard connection. Removing that connection stopped the reboot loop. The software/network stack was therefore not changed to mask a physical wiring fault.

These registration results alone do not constitute physical sensing evidence. On 2 October 2026 an XC4604 analogue soil-moisture probe was then electrically exercised on ESP32-S3 GPIO4: dry air produced raw 0 / 0 mV, immersion in water produced readings centred near raw 1800 / 1.5 V, and finger contact produced readings around raw 300 / 0.27 V. These observations establish that the probe and ADC input respond physically. The managed LIVE telemetry path still requires deployment acceptance below, and T01 remains incomplete until all six FR01 physical measurements are demonstrated with required provenance.


## Current transition design - 27 September 2026

The earlier prototype treated a centrally generated 16-location synthetic dataset as normal application data. Once two real managed ESP32-S3 boards were introduced, that created an avoidable ambiguity: a simulated location could look operational while real hardware existed separately with no physical measurements.

The current branch therefore establishes a clean operational baseline. The old `firmware/esp32-sensor` remains available as an explicit test/demo generator, but a normal FarmPi database starts with no locations, nodes or readings. The one-time reset helper archives the old database before recreating it; the reset is never triggered merely by applying code.

Simulation has moved to the managed-node sensor boundary. Each catalogue measurement is now independently `OFF`, `SIMULATED`, or `LIVE`. Simulated values originate on the ESP32-S3 and use the same device authentication, configuration fingerprint, time, sequence, ingest, storage and Android path as later physical readings. LIVE selection is rejected until firmware advertises the implemented physical driver.

Hardware UID, stable FarmPi node ID and farmer location are separate identities. The logical ID is `FP-xxx`. The farmer can assign names such as `Bob's`, `Back Hill` or `Down by the Trough`, and moving a node does not change its hardware or logical identity.

The managed S3 profile advertises all 13 catalogue keys for simulation and now advertises one physical LIVE driver: `soil_moisture_pct` from an XC4604 on GPIO4. The first implementation uses a proof-of-concept electrical scale of raw 0 (dry air) to raw 1800 (immersed water), clamped to 0–100%. This scale is explicitly uncalibrated and must not be reported as volumetric water content or agronomic calibration. Modes remain managed through the same configuration contract. T01 still requires six real physical measurements.

## Software setup

1. Before the one-time transition to the clean operational baseline, run `sudo bash ./scripts/reset-operational-database --yes-really-reset`. The helper first creates a timestamped SQL archive under `/var/backups/farmpi`, then stops FarmPi, recreates the database, applies the current schema and empty operational seed, and restarts the service. Do not run it until the current synthetic dataset is no longer needed. Normal future updates continue to use the additive schema workflow and do not erase operational data.
2. The updated `scripts/setup-database` preserves or generates `FARMPI_ADMIN_TOKEN` in the existing protected environment file. On an existing installation that only runs the schema update, add a separately generated administrator token to `/etc/farmpi/farmpi.env` and restart FarmPi. Do not reuse the ingest token. The Android Nodes screen holds this token only for its current screen session. No secrets belong in Git or evidence logs.
3. Build/install the Android client, open **Nodes**, enter the administrator token and refresh. The earlier managed-environment Gradle attempt failed before Kotlin compilation because Gradle could not establish a loopback connection, but the live Android Nodes workflow has since been exercised successfully against FarmPi for S3 discovery/registration. Preserve both records: the earlier build failure is development evidence and the later device use is live integration evidence.
4. Copy `firmware/esp32-s3-node/config.example.h` to `config.h`; set Wi-Fi and the FarmPi HTTPS address. Paste the existing Caddy local root CA certificate. `farmpi.local` is the HTTPS application endpoint, not an NTP server. The two live boards already reach the managed contact path successfully. After each successful contact, the firmware reads FarmPi's existing `server_time` response and uses it to establish/correct the node clock when required. No NTP service or Internet time source is required for managed telemetry. The existing telemetry guard still refuses to send a timestamped sample until the local clock is valid.
5. Compile with Arduino ESP32 core **3.3.11** and ArduinoJson **7.4.2**. The verified compile target is `esp32:esp32:esp32s3:FlashSize=16M,PSRAM=opi,PartitionScheme=app3M_fat9M_16MB`. Jeremy identified the modules as ESP32-S3 N16R8. This target matches 16 MB quad flash and 8 MB octal PSRAM for the WROOM-1 N16R8 variant. The XC4604 proof-of-concept wiring is `+` → 3V3, `-` → GND, and `S` → GPIO4 (ADC1). Keep the probe electronics/connector dry during immersion tests.
6. Upload the same image to both boards with **Erase All Flash disabled** for normal updates so NVS identity/configuration survives. During first live provisioning, one board required a deliberate full-flash erase to clear an NVS/PHY calibration-storage failure before registration could proceed. Treat full erase as provisioning/recovery only: erasing the device key requires deliberate administrative recovery, and the server will reject an unknown replacement key for an existing hardware UID rather than silently reassign identity.

## Configuration contract

Device contact remains `POST /api/nodes/contact` with hardware UID, device key, firmware version, board profile, capabilities and optional applied fingerprint. Unknown devices appear as pending and cannot approve themselves.

`POST /api/nodes/{id}/approve` assigns a stable logical ID such as `FP-001`. Registration starts every advertised measurement in OFF mode. Friendly node name and assigned location remain separate from that logical identity.

The schema-version-2 canonical document contains exactly `modes`, `node_uid`, and `schema_version`. `modes` contains one of `OFF`, `SIMULATED`, or `LIVE` for every capability advertised by that firmware. JSON is compact and key-sorted before SHA-256 fingerprinting.

`PUT /api/nodes/{id}/configuration` accepts friendly name, location ID, the mode map and the expected current fingerprint. Stale edits, unknown measurements and invalid modes are rejected. Location changes increase `location_epoch`; delayed samples carrying an old assignment are rejected rather than silently attributed to the new location.

The ESP32 checks FarmPi every 15 seconds. A successful contact also returns FarmPi's authoritative Unix `server_time`; the node validates it and sets/corrects its application clock when required. It then fetches only the latest complete desired document when the desired fingerprint differs, validates identity/schema/capabilities/canonical bytes/hash, persists it into the two-slot NVS last-known-good store, then acknowledges the applied fingerprint. Rejected candidates never replace the active configuration.

Sync state remains derived: matching desired/applied fingerprints = IN SYNC; a failure against the current desired fingerprint = UPDATE FAILED; otherwise UPDATE PENDING.

## Managed telemetry and simulation

The managed S3 firmware now uses `/api/ingest` for both node-local simulation and later physical drivers. Every accepted sample includes the registered node identity, hardware UID, device credential, applied fingerprint, location epoch, valid observation time and persistent sample sequence. The firmware sends telemetry every 60 seconds only when at least one configured measurement produces a value and the local clock is valid. FarmPi contact is the managed-node time source; the node no longer attempts `configTime(..., "farmpi.local")`.

The server does not trust the device to declare provenance independently. It derives the source mode of each supplied measurement from the acknowledged desired/applied configuration. A supplied OFF measurement is rejected. A SIMULATED value is stored as simulated for that measurement. A LIVE value also requires the measurement to appear in the firmware-advertised `live_capabilities` list.

`readings.measurement_modes_json` preserves that per-measurement provenance. The existing row-level `simulated` field remains as a conservative compatibility flag when any measurement in the sample is simulated.

The firmware generates bounded test values for measurements configured SIMULATED. For `soil_moisture_pct` configured LIVE, `readLiveMeasurement()` now averages 16 ADC samples from GPIO4 and maps the observed XC4604 proof-of-concept electrical span to 0–100%. That mapping is intentionally uncalibrated; it demonstrates the acquisition/telemetry contract without claiming agronomic accuracy. Other measurements still require physical drivers before LIVE can be selected.

Sequence allocation is persisted in NVS. A full offline queue and resend policy are still T02 work; this change does not claim communication-loss recovery is complete.

## Updated two-board evidence checklist

Record source revision, toolchain versions, binary SHA-256, hardware UIDs, assigned `FP-xxx` IDs, farmer location names, UTC times, desired/applied full hashes and screenshots/serial output without credentials.

1. Archive the old synthetic database, create the clean operational baseline and confirm it contains no preloaded locations, nodes or readings.
2. Flash both boards with the schema-v2 managed firmware. Verify they appear as two pending devices with distinct hardware UIDs.
3. Create two farmer-named locations, register both nodes, and verify every standard measurement begins OFF.
4. Set selected measurements to SIMULATED from Android Node Detail or with `.venv/bin/python scripts/configure-node-modes FP-001 soil_moisture_pct=SIMULATED`. Verify desired/applied fingerprints are IN SYNC, serial output shows FarmPi time synchronisation (when required) and `Telemetry accepted`, then verify `/api/ingest` and MariaDB contain simulated rows for both nodes.
5. Change one node without changing the other. Verify desired/applied fingerprints and mode state remain independent.
6. Move one node to a different farmer-defined location. Verify its `FP-xxx` and hardware UID stay unchanged, its location epoch increases, and historical readings remain attached to the original location.
7. Reboot with FarmPi unreachable and verify the last-known-good configuration survives. Reconnect and verify normal sync recovery.
8. For the XC4604 node, change `soil_moisture_pct` from SIMULATED to LIVE. Verify the node reports `soil_moisture_pct` in `live_capabilities`, desired/applied fingerprints return to IN SYNC, serial output shows `XC4604 GPIO4 raw=...` followed by accepted telemetry, and MariaDB/Android show the resulting measurement as LIVE/non-simulated provenance.
9. Move the probe between clearly different electrical conditions (for example dry air and wet contact) and verify the stored/displayed LIVE reading changes correspondingly. This proves responsiveness, not calibration.
10. Continue one physical measurement at a time until all six FR01 measurements have real evidence. LIVE configuration without an advertised driver must be rejected.

T01 remains incomplete until all six FR01 measurements are demonstrated physically. The node-local simulator is development evidence, not physical acquisition evidence.

## References

* [Espressif WROOM-1 module memory variants](https://www.espressif.com/sites/default/files/documentation/esp32-s3-wroom-1_wroom-1u_datasheet_en.pdf)
* [Espressif Preferences persistence API](https://docs.espressif.com/projects/arduino-esp32/en/latest/api/preferences.html)
* [ArduinoJson 7 deserialization API](https://arduinojson.org/v7/api/json/deserializejson/)

When upgrading a node from the six-key profile merged in PR #10, let the new firmware contact the server, then use the console helper to save its modes. This creates the complete 13-key configuration required by the new profile. Clear previously selected LIVE modes to OFF or SIMULATED until a driver is advertised. Until the new complete configuration is saved and acknowledged, the node can report UPDATE PENDING/FAILED; do not treat this as completed hardware validation.
