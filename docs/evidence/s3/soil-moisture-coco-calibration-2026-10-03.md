# XC4604 coco-relative soil-moisture calibration — 3 October 2026

## Status and purpose

The first FarmPi LIVE soil-moisture acceptance on 2 October 2026 proved the physical acquisition path, but its display scale was deliberately uncalibrated: raw 0 in dry air and raw 1800 in immersed water were mapped to 0–100%.

Live use in the actual coco growing medium showed that this electrical proof-of-concept scale was not meaningful for the medium itself. Completely dry coco still displayed around 58–64% on the old scale.

This record preserves the calibration history rather than rewriting the earlier observations. The first coco-relative calibration used approximately **1066 dry / 1955 wet**. Further saturated-coco testing led to the retained firmware endpoints of **1000 dry / 2200 wet**.

The retained 1000/2200 values are engineering endpoints for this prototype. They must not be described as the directly measured dry median and wet mean. The measured dry median retained below was approximately 1066.4; the later saturated-coco series had a mean around 2120 and included at least one reading around 2185.

## Hardware and scope

- FarmPi node: **FP-001**
- ESP32 hardware UID: `7c4fadb633c0`
- Short hardware tag: **HW 33C0**
- Probe: Jaycar/Duinotech XC4604 analogue soil-moisture module
- Signal input: ESP32-S3 **GPIO4 / ADC1**
- Existing physical source mode: `soil_moisture_pct = LIVE`

The purpose is to create a more useful **relative moisture percentage for the coco test medium**. This is not volumetric water content and is not an agronomic calibration.

## Calibration stages

| Stage | Dry endpoint | Wet endpoint | Purpose / evidence |
|---|---:|---:|---|
| Initial electrical proof of concept | 0 | 1800 | Proved the physical probe → ADC → telemetry → database → Android path only |
| First coco-relative calibration | 1066 | 1955 | Based on the retained dry-coco median and the first three saturated-coco readings |
| Retained prototype firmware scale | 1000 | 2200 | Rounded engineering endpoints retained after further saturated-coco testing |

The earlier 1066/1955 values remain valid historical evidence of the first medium-specific calibration. They are **superseded as active firmware endpoints**, not erased from the development history.

## First saturated-coco observations

Water was poured over the coco until it reached saturation. After the sensor settled, the first retained raw readings were:

| Reading | Raw ADC |
|---|---:|
| 1 | 1943.7 |
| 2 | 1966.1 |
| 3 | 1955.1 |

Mean of these first three saturated readings:

```text
(1943.7 + 1966.1 + 1955.1) / 3 = 1954.97
```

This produced the first provisional wet endpoint:

```text
PROVISIONAL_RAW_WET = 1955
```

## Completely dry coco observations

The probe was placed in completely dry coco mix. The retained raw readings were:

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

The dry readings showed contact/insertion variation. The median was selected for the first provisional calibration rather than relying on a single extreme reading.

Dry median:

```text
1066.4
```

This produced the first provisional dry endpoint:

```text
PROVISIONAL_RAW_DRY = 1066
```

## Later saturated-coco refinement

Further saturated-coco testing was carried out after the first 1066/1955 calibration. The later test series contained nine readings, with a mean of approximately **2120** and at least one reading around **2185**.

Those observations showed that the original 1955 upper endpoint was too low to represent the later saturated-coco behaviour. The practical wet marker was therefore moved to **2200**.

The current retained firmware source uses:

```text
RAW_DRY = 1000
RAW_WET = 2200
SPAN    = 1200 ADC counts
```

The dry endpoint of 1000 is a rounded engineering endpoint used by the firmware. It should not be described as the measured median; the retained dry-coco median was approximately 1066.4.

## Current relative scale

The retained prototype conversion is:

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
RAW_DRY = 1000
RAW_WET = 2200
SPAN    = 1200 ADC counts
```

Representative values:

| Raw ADC | Relative prototype moisture |
|---:|---:|
| 1000 | 0% |
| 1300 | 25% |
| 1600 | 50% |
| 1900 | 75% |
| 2200 | 100% |

## Firmware history

The first coco-relative implementation replaced the earlier `0.3.3-xc4604-poc` proof-of-concept scaling with firmware `0.3.4-xc4604-coco-cal`.

PR #50 introduced the provisional 1066/1955 coco-relative endpoints and renamed the firmware constants away from the original proof-of-concept names. PR #51 then corrected stale `setup()` references left by that rename so the firmware compiled successfully.

A later calibration change recorded in commit `54b00e7` moved the retained source endpoints to **1000 dry / 2200 wet**. That commit also contained unrelated build artefacts and other changes, so this record treats the calibration result separately from that unrelated file churn.

The source mode remains `LIVE`; only the interpretation of the ADC reading changed.

## Relationship to retained screenshots and earlier evidence

The 2 October physical acceptance remains valid historical evidence of the real probe → ADC → telemetry → database → Android path.

Some retained screenshots and samples, including sample 7219 used in the capstone evidence, were captured while the earlier 1955 wet endpoint was still active. Their displayed percentage therefore belongs to that earlier calibration state. They remain evidence of the end-to-end physical path and LIVE provenance, but they must not be presented as evidence of the final 1000/2200 percentage scale.

## Evidence boundary

The retained 1000/2200 calibration supports a practical relative 0–100% scale for the tested coco medium.

It does **not** support:

- volumetric water content;
- laboratory or commercial calibration;
- transfer of the same endpoints to another soil/media type;
- agronomic irrigation thresholds;
- certified measurement accuracy.

The calibration changes do not alter the overall physical-coverage result.

**T01 remains PARTIAL (1/6 physical measurement types demonstrated).**
