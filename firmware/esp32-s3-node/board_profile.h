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
static const char* FIRMWARE_VERSION = "0.3.0-sensor-modes";

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

// No physical acquisition driver is claimed by this revision.
static const char* LIVE_MEASUREMENTS[1] = { nullptr };
static const size_t LIVE_COUNT = 0;
