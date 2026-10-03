# XC4604 coco-relative soil-moisture calibration — 3 October 2026

## Purpose

The first FarmPi LIVE soil-moisture acceptance on 2 October 2026 proved the physical acquisition path, but its display scale was deliberately uncalibrated: raw 0 in dry air and raw 1800 in immersed water were mapped to 0–100%.

Live use in the actual coco growing medium showed that this electrical proof-of-concept scale was not meaningful for the medium itself. Completely dry coco still displayed around 58–64% on the old scale.

This record captures the medium-specific prototype recalibration.

## Hardware and scope

- FarmPi node: **FP-001**
- ESP32 hardware UID: `7c4fadb633c0`
- Short hardware tag: **HW 33C0**
- Probe: Jaycar/Duinotech XC4604 analogue soil-moisture module
- Signal input: ESP32-S3 **GPIO4 / ADC1**
- Existing physical source mode: `soil_moisture_pct = LIVE`

The purpose is to create a more meaningful **relative moisture percentage for the coco test medium**. This is not volumetric water content and is not an agronomic calibration.

## Saturated coco endpoint

Water was poured over the coco until it reached saturation. After the sensor settled, the following raw readings were observed:

| Reading | Raw ADC |
|---|---:|
| 1 | 1943.7 |
| 2 | 1966.1 |
| 3 | 1955.1 |

Mean saturated reading:

```text
(1943.7 + 1966.1 + 1955.1) / 3 = 1954.97
```

Prototype wet endpoint:

```text
RAW_WET = 1955
```

## Completely dry coco endpoint

The probe was then placed in completely dry coco mix. The following raw readings were retained:

| Reading | Raw ADC |
|---|---:|
| 1 | 1155.6 |
| 2 | 1113.1 |
| 3 | 1096.2 |
| 4 | 1083.5 |
| 5 | 972.1 |
| 6 | 1066.4 |
| 7 | 1056.0 |
| 8 | 1050.9 |
| 9 | 1043.3 |

The dry readings showed some expected contact/insertion variation. The median was selected rather than relying on the lowest or highest single reading.

Dry median:

```text
1066.4
```

Prototype dry endpoint:

```text
RAW_DRY = 1066
```

## Relative scale

The current prototype conversion is:

```text
relative_moisture_pct =
    clamp(
        (raw - RAW_DRY) / (RAW_WET - RAW_DRY) * 100,
        0,
        100
    )
```

with:

```text
RAW_DRY = 1066
RAW_WET = 1955
SPAN    = 889 ADC counts
```

Representative values:

| Raw ADC | Relative prototype moisture |
|---:|---:|
| 1066 | 0% |
| 1288 | ~25% |
| 1511 | ~50% |
| 1733 | ~75% |
| 1955 | 100% |

## Firmware change

Firmware is updated from `0.3.3-xc4604-poc` to `0.3.4-xc4604-coco-cal`.

Serial output changes from the old wording:

```text
prototype_scale=...% (uncalibrated)
```

to:

```text
relative_moisture=...% (coco-calibrated prototype)
```

The mode remains `LIVE`; only the interpretation of the ADC reading is changed.

## Evidence boundary

This calibration supports a more useful relative 0–100% scale for the tested coco medium.

It does **not** support:

- volumetric water content;
- laboratory or commercial calibration;
- transfer of the same endpoints to another soil/media type;
- agronomic irrigation thresholds;
- certified measurement accuracy.

The 2 October physical acceptance remains valid historical evidence of the real probe → ADC → telemetry → database → Android path. This 3 October calibration improves the displayed scale; it does not change the overall T01 state.

**T01 remains PARTIAL (1/6 physical measurements demonstrated).**
