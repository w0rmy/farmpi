#pragma once
// FarmPi standard-node profile. These six measurement keys are understood by
// the firmware and can be OFF, SIMULATED or LIVE independently. LIVE only
// reports once the corresponding physical driver has been implemented.
static const char* BOARD_PROFILE = "esp32-s3-standard-v2";
static const char* FIRMWARE_VERSION = "0.3.0-mode-simulation";

// Keep alphabetic order: canonical configuration hashing depends on sorted keys.
static const char* CONFIGURABLE_MEASUREMENTS[] = {
  "air_temperature_c",
  "barometric_pressure_hpa",
  "light_lux",
  "relative_humidity_pct",
  "soil_moisture_pct",
  "soil_temperature_c"
};
static const size_t CONFIGURABLE_COUNT = sizeof(CONFIGURABLE_MEASUREMENTS) / sizeof(CONFIGURABLE_MEASUREMENTS[0]);
