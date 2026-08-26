# FarmPi ESP32 synthetic sensor

This firmware is a deliberately small test node for the FarmPi capstone. It proves the real device-to-server data path without requiring the final physical soil-moisture sensor yet.

The ESP32:

1. joins Wi-Fi;
2. resolves `farmpi.local` by mDNS;
3. identifies itself with a registered `sensor_nodes.node_uid`;
4. generates a slowly changing synthetic soil-moisture value;
5. sends the value to `POST /api/ingest` over HTTPS every 30 seconds;
6. marks every reading as `simulated: true`;
7. prints connection and HTTP status information to the serial console.

## Configure

Copy the example configuration:

```text
config.example.h -> config.h
```

Edit `config.h` and set:

- Wi-Fi SSID and password;
- sensor UID;
- local ESP32 hostname;
- FarmPi ingest token.

The default sensor UID is `test-moisture-a`, which is created by the prototype MariaDB seed. The seed also provides `test-moisture-b`, `test-moisture-c`, and `test-moisture-d` for additional test nodes.

On FarmPi, display the ingest token with:

```bash
sudo grep '^FARMPI_INGEST_TOKEN=' /etc/farmpi/farmpi.env
```

Copy only the token value into `config.h`. `config.h` is ignored by Git.

## Build

The sketch uses only libraries supplied by the ESP32 Arduino core:

- `WiFi.h`
- `WiFiClientSecure.h`
- `ESPmDNS.h`

Open `esp32-sensor.ino` in the Arduino IDE, select the appropriate ESP32/ESP32-S3 board, and upload it normally.

No special flash partitioning or external libraries are required for this test firmware.

## Prototype TLS choice

The test node uses `WiFiClientSecure::setInsecure()`. The connection is still TLS-encrypted, but the ESP32 does not validate Caddy's private-CA certificate. This is intentional for the capstone test platform so certificate provisioning does not become a separate embedded-security project.

The browser/user interface remains properly HTTPS-protected and trusted through Caddy's internal CA. Production device certificate validation is outside the current prototype scope.

## Expected serial output

Typical output is:

```text
FarmPi synthetic ESP32 sensor starting
Sensor UID: test-moisture-a
Connecting to Wi-Fi SSID '...'
Wi-Fi connected: 192.168.x.x, RSSI -48 dBm
Resolving farmpi.local via mDNS...
FarmPi resolved to 192.168.x.x
Synthetic reading: 17.82% soil moisture (RSSI -48 dBm)
FarmPi response: HTTP/1.1 201 Created
Reading accepted by FarmPi.
```

Once a reading is accepted, the existing deterministic FarmPi queries use it automatically because it becomes the latest reading for that sensor.
