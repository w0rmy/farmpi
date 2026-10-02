#pragma once

// Managed ESP32-S3 prototype profile.
//
// Every catalogue measurement can be simulated in firmware so the real node,
// credentials, configuration, timing, network, ingest, database and Android
// path can be exercised before the corresponding probe is fitted.
//
// LIVE support is deliberately separate. Add a measurement to LIVE_MEASUREMENTS
// only when its physical driver and electrical interface have been implemented
// and tested on this board profile.

static const char* BOARD_PROFILE = "esp32-s3-managed-v2";
static const char* FIRMWARE_VERSION = "0.3.3-xc4604-poc";

// Alphabetical order is intentional: it matches the canonical configuration.
static const char* CONFIGURABLE_MEASUREMENTS[] = {
  "air_temperature_c",
  "barometric_pressure_hpa",
  "leaf_wetness_pct",
  "light_lux",
  "pasture_height_cm",
  "rainfall_mm",
  "relative_humidity_pct",
  "soil_ec_ms_cm",
  "soil_moisture_pct",
  "soil_ph",
  "soil_temperature_c",
  "wind_direction_deg",
  "wind_speed_kmh"
};
static const size_t CONFIGURABLE_COUNT = sizeof(CONFIGURABLE_MEASUREMENTS) / sizeof(CONFIGURABLE_MEASUREMENTS[0]);

// Physical proof-of-concept driver currently fitted to the managed S3 profile.
// XC4604 is an analogue resistive probe on ESP32-S3 ADC1 GPIO4.
// The electrical scaling below is intentionally NOT an agronomic calibration.
static const uint8_t SOIL_MOISTURE_ADC_PIN = 4;
static const uint16_t SOIL_MOISTURE_POC_RAW_DRY = 0;
static const uint16_t SOIL_MOISTURE_POC_RAW_WET = 1800;
static const uint8_t SOIL_MOISTURE_ADC_SAMPLES = 16;

static const char* LIVE_MEASUREMENTS[] = {
  "soil_moisture_pct"
};
static const size_t LIVE_COUNT = sizeof(LIVE_MEASUREMENTS) / sizeof(LIVE_MEASUREMENTS[0]);
