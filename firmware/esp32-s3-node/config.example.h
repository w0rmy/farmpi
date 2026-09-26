#pragma once
#define WIFI_SSID "YOUR_WIFI_SSID"
#define WIFI_PASSWORD "YOUR_WIFI_PASSWORD"
#define FARMPI_URL "https://farmpi.local"
// Export the FarmPi Caddy root certificate and paste its complete PEM here.
// The physical target verifies TLS; do not use the simulator's setInsecure().
static const char FARMPI_ROOT_CA[] = R"PEM(-----BEGIN CERTIFICATE-----
REPLACE_WITH_FARMPI_ROOT_CA
-----END CERTIFICATE-----
)PEM";
