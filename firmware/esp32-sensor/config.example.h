#pragma once

// Copy this file to config.h and edit the values for the test node.
// config.h is ignored by Git so Wi-Fi credentials and the ingest token stay local.

#define WIFI_SSID "YOUR_WIFI_SSID"
#define WIFI_PASSWORD "YOUR_WIFI_PASSWORD"

// FarmPi mDNS hostname without the .local suffix.
#define FARMPI_MDNS_HOST "farmpi"
#define FARMPI_HTTPS_PORT 443

// Must match a sensor_nodes.node_uid already registered in MariaDB.
// The seed data provides test-moisture-a through test-moisture-d.
#define SENSOR_UID "test-moisture-a"
#define DEVICE_HOSTNAME "farmpi-sensor-a"

// Copy the value from FARMPI_INGEST_TOKEN in /etc/farmpi/farmpi.env.
#define FARMPI_INGEST_TOKEN "PASTE_INGEST_TOKEN_HERE"

// Synthetic-data controls.
#define SYNTHETIC_START_MOISTURE 18.0f
#define SYNTHETIC_MIN_MOISTURE 5.0f
#define SYNTHETIC_MAX_MOISTURE 95.0f
#define SYNTHETIC_START_AIR_TEMPERATURE_C 16.0f
#define SYNTHETIC_START_RELATIVE_HUMIDITY_PCT 72.0f
#define SYNTHETIC_START_SOIL_PH 6.3f
#define SEND_INTERVAL_MS 300000UL
