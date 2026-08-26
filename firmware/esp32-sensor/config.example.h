#pragma once

// Copy this file to config.h and edit the values for the test node.
// config.h is ignored by Git so Wi-Fi credentials and the ingest token stay local.

#define WIFI_SSID "YOUR_WIFI_SSID"
#define WIFI_PASSWORD "YOUR_WIFI_PASSWORD"

// FarmPi mDNS hostname without the .local suffix.
#define FARMPI_MDNS_HOST "farmpi"
#define FARMPI_HTTPS_PORT 443

#define DEVICE_HOSTNAME "farmpi-sensor-a"

// Copy the value from FARMPI_INGEST_TOKEN in /etc/farmpi/farmpi.env.
#define FARMPI_INGEST_TOKEN "PASTE_INGEST_TOKEN_HERE"

// One ESP32 posts a full 16-paddock synthetic round every five minutes.
// It sends exactly one virtual node at a time, every 18.75 seconds.
#define VIRTUAL_PADDOCK_COUNT 16
#define SIMULATION_ROUND_MS 300000UL

// Default is a Waikato/Hamilton dairy-farming reference profile. These are
// compile-time profile settings only; the ESP32 never makes weather web calls.
#define NZ_SIMULATION_LATITUDE -37.7870f
#define NZ_SIMULATION_LONGITUDE 175.2793f
