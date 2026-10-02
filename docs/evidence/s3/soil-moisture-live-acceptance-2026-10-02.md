# XC4604 LIVE soil-moisture acceptance — 2 October 2026

## Scope

This record captures the first end-to-end physical sensor acceptance for FarmPi T01. It demonstrates one real soil-moisture channel through the managed ESP32-S3 architecture. It does **not** demonstrate the other five required FR01 physical measurements and does not establish calibrated agronomic accuracy.

## Hardware and firmware

- FarmPi node: **FP-001**
- ESP32 hardware UID: `7c4fadb633c0`
- Short physical tag: **HW 33C0**
- Probe: Jaycar/Duinotech XC4604 analogue soil-moisture module
- Signal input: ESP32-S3 **GPIO4 / ADC1**
- Firmware: `0.3.3-xc4604-poc`
- Firmware source mode: `soil_moisture_pct = LIVE`

The proof-of-concept mapping uses approximately raw 0 as the dry electrical endpoint and raw 1800 as the wet electrical endpoint, clamped to 0–100%. This is explicitly an **uncalibrated prototype scale**, not volumetric water content.

## Electrical pre-check

Before integration into the managed firmware, the XC4604 and GPIO4 ADC path were exercised directly:

| Condition | Observed result |
|---|---:|
| Dry air | raw 0 / 0 mV |
| Finger contact across sensing electrodes | approximately raw 300 / 0.27 V |
| Sensing section immersed in water | approximately raw 1800 / 1.5 V |

These values demonstrate physical electrical response only.

## Managed-node acceptance

After the merged LIVE driver was flashed with NVS preserved:

1. the node booted and reported `Hardware 7c4fadb633c0`;
2. Android Node Detail selected **Soil moisture → LIVE**;
3. the desired configuration was applied and the node returned to **IN SYNC**;
4. dry serial readings repeatedly showed `raw=0.0 prototype_scale=0.00% (uncalibrated)`;
5. accepted telemetry sequences 6856–6859 contained the dry LIVE soil-moisture value;
6. after immersing the sensing section in water, serial reported:

```text
XC4604 GPIO4 raw=1164.4 prototype_scale=64.69% (uncalibrated)
Telemetry accepted seq=6860 simulated=true
```

7. MariaDB stored the same sample as a LIVE soil-moisture measurement;
8. Android displayed the current/history change.

## Database verification

The deployed MariaDB query returned:

```text
node_uid  hardware_uid  sample_seq  soil_moisture_pct  simulated  soil_mode
FP-001    7c4fadb633c0  6860        64.69              1          LIVE
FP-001    7c4fadb633c0  6861        66.09              1          LIVE
FP-001    7c4fadb633c0  6862        65.21              1          LIVE
```

Earlier dry samples 6856–6859 were stored as `0.00` with `soil_mode=LIVE`.

The row-level `simulated=1` value is expected because other measurements in the same sample remained SIMULATED. `measurement_modes_json` is the authoritative per-measurement provenance and recorded soil moisture as `LIVE`.

For sample 6860:

- observed_at: `2026-10-02 02:50:24 UTC`
- received_at: `2026-10-02 02:50:25.460038 UTC`
- observation-to-receipt delay: approximately 1.46 seconds.

## Result

**PASS — physical soil-moisture channel.**

The following chain was demonstrated:

```text
XC4604 physical probe
  -> ESP32-S3 GPIO4 ADC
  -> managed LIVE driver
  -> authenticated sparse telemetry
  -> FarmPi ingest validation
  -> MariaDB with soil_moisture_pct mode LIVE
  -> Android current/history display
```

This is one component of T01. Overall T01 remains **PARTIAL (1/6 physical measurements demonstrated)** because soil temperature, air temperature, relative humidity, light and barometric pressure have not been physically demonstrated.

## Evidence boundary

This record supports physical acquisition, responsiveness, managed-node integration, provenance and end-to-end data flow. It does not support:

- volumetric-water-content calibration;
- commercial sensor accuracy;
- agronomic decision thresholds;
- production environmental durability;
- the five remaining physical FR01 measurements.
