#pragma once
// Configuration-only bring-up profile. No pins are touched until the exact
// S3 carrier board and real probe/module have been identified and reviewed.
static const char* BOARD_PROFILE = "esp32-s3-bringup-v1";
static const char* FIRMWARE_VERSION = "0.2.0-config-bringup";
// This capability means the enable/disable configuration is understood.
// Acquisition is deliberately unavailable until the probe driver is added.
static const char* CONFIGURABLE_MEASUREMENTS[] = {"soil_moisture_pct"};
static const size_t CONFIGURABLE_COUNT = 1;
