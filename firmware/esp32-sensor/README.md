# FarmPi ESP32 16-paddock generator

Copy config.example.h to config.h and set WIFI_SSID, WIFI_PASSWORD, DEVICE_HOSTNAME, and FARMPI_INGEST_TOKEN. config.h is ignored by Git. Do not place credentials or tokens in source control.

Open esp32-sensor.ino in Arduino IDE, select the actual ESP32 board, and upload. It uses only WiFi.h, WiFiClientSecure.h, ESPmDNS.h and ESP32 core headers; no automated Arduino build is configured in this repository.

One board emits UIDs test-moisture-a through test-moisture-p. Seed the database before flashing. It sends the first node immediately, then one node every 18.75 seconds; a round is five minutes. FarmPi supplies UTC through the normal ingest acknowledgement; this sketch does not use Internet NTP. Its shared weather/per-paddock simulation is explained in [NZ simulation](../../docs/nz-synthetic-simulation.md), and the versioned time/sequence fields are in [the telemetry contract](../../docs/time-sync-telemetry.md).

Expected values in config.h:

```c
#define WIFI_SSID "your network"
#define WIFI_PASSWORD "your password"
#define DEVICE_HOSTNAME "farmpi-sensor-a"
#define FARMPI_INGEST_TOKEN "value from /etc/farmpi/farmpi.env"
#define VIRTUAL_PADDOCK_COUNT 16
#define SIMULATION_ROUND_MS 300000UL
#define NZ_SIMULATION_LATITUDE -37.7870f
#define NZ_SIMULATION_LONGITUDE 175.2793f
```

The sketch preserves mDNS, Wi-Fi reconnects, HTTPS bearer auth, diagnostics, retries, and the Caddy SNI fix. It connects by resolved IP with farmpi.local as TLS hostname. setInsecure() is a prototype-only private-CA compromise.
