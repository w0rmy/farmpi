# Live ESP32-S3 bring-up evidence - 26 September 2026

## Scope

This record captures live integration evidence obtained after the managed ESP32-S3 node implementation was merged. It supplements the earlier compile/test evidence in this directory. It does **not** claim completion of T01 or physical sensor acquisition.

## Deployment state

- Two ESP32-S3 N16R8 boards were flashed with the managed-node firmware.
- Both boards joined the dedicated FarmLAN and reached the FarmPi discovery/registration path.
- The Android FarmPi Nodes workflow was used to connect/register the boards.
- Observed hardware UIDs: `7c4fadb633c0` and `7c4fadb52c40`.
- No physical probe reading is claimed by this record.
- Final assigned FarmPi node IDs, full desired/applied fingerprints, screenshots and timestamps should be captured in the next formal evidence pass.

## Fresh-provisioning NVS fault

One newly flashed board produced:

```text
E (...) phy_init: store_cal_data_to_nvs_handle: store calibration data failed(0x1105)
```

A deliberate **Erase All Flash** followed by reflashing cleared the condition. The firmware then booted normally and reached:

```text
Awaiting registration; no sensors running.
```

Interpretation: this was treated as a first-provisioning/recovery issue rather than a reason to change normal persistence behaviour. Routine firmware uploads should continue to preserve NVS so the device key and last known-good configuration survive.

## Breadboard-induced reboot fault

During another board bring-up, the ESP32-S3 repeatedly rebooted with:

```text
assert failed: sys_untimeout ... (Required to lock TCPIP core functionality!)
```

The symptom initially appeared to implicate lwIP/TCPIP behaviour. Investigation found an unintended breadboard connection. Removing that connection stopped the reboot loop. No FarmPi network-stack change was made to work around the symptom.

This is useful fault-isolation evidence because the visible failure occurred in the network stack while the actual cause was physical wiring.

## FarmLAN state relevant to this test

- Raspberry Pi retains a separate management/home-LAN Wi-Fi connection.
- The dedicated FarmLAN access-point connection is bound to the intended Wi-Fi adapter by MAC address rather than relying on the `wlanN` interface name.
- FarmLAN AP-side address: `10.42.0.1/24`.
- Application clients continue to use `https://farmpi.local/` for the prototype.
- Direct fixed-IP HTTPS for embedded nodes is a deferred hardening option because it would require the server certificate to include the IP address as a SAN.

## Pi-local LLM verification

Live inspection of the Raspberry Pi showed:

```text
farmpi-llm.service  active running
llama-server ... -hf lmstudio-community/Qwen3-1.7B-GGUF:Q4_K_M -c 2048 --host 127.0.0.1 --port 8080 --reasoning off --parallel 1
```

`GET http://127.0.0.1:8080/health` returned `{"status":"ok"}`, and `/v1/models` reported the same Qwen3 1.7B model.

`farmpi.service` loads `/etc/farmpi/farmpi.env`; no `FARMPI_LLAMA_URL` override is present. `app/app.py` therefore uses its default `http://127.0.0.1:8080`. The development PC is not part of the normal inference path.

## Remaining evidence

Before claiming the managed-node block complete, retain evidence for:

- assigned FarmPi node IDs and locations;
- desired/applied full configuration fingerprints and derived sync state;
- two-node configuration isolation;
- reboot/offline recovery with saved configuration;
- the first real probe driver and observation;
- correct source/location/time/unit/provenance through API, database and Android;
- final six-measurement physical T01 acceptance.
