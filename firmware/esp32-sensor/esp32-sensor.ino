#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <ESPmDNS.h>
#include <esp_system.h>

#include "config.h"

static float syntheticMoisture = SYNTHETIC_START_MOISTURE;
static unsigned long lastSendMs = 0;
static IPAddress farmPiAddress;

static void connectWiFi() {
  if (WiFi.status() == WL_CONNECTED) {
    return;
  }

  Serial.printf("Connecting to Wi-Fi SSID '%s'...\n", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.setHostname(DEVICE_HOSTNAME);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  const unsigned long started = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - started < 20000UL) {
    delay(500);
    Serial.print('.');
  }
  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf(
      "Wi-Fi connected: %s, RSSI %d dBm\n",
      WiFi.localIP().toString().c_str(),
      WiFi.RSSI()
    );

    if (!MDNS.begin(DEVICE_HOSTNAME)) {
      Serial.println("mDNS responder failed to start; FarmPi lookup may fail.");
    }
  } else {
    Serial.println("Wi-Fi connection timed out.");
  }
}

static bool resolveFarmPi() {
  if (farmPiAddress != IPAddress()) {
    return true;
  }

  Serial.printf("Resolving %s.local via mDNS...\n", FARMPI_MDNS_HOST);
  farmPiAddress = MDNS.queryHost(FARMPI_MDNS_HOST, 3000);

  if (farmPiAddress == IPAddress()) {
    Serial.println("FarmPi mDNS lookup failed.");
    return false;
  }

  Serial.printf("FarmPi resolved to %s\n", farmPiAddress.toString().c_str());
  return true;
}

static float nextSyntheticMoisture() {
  // Small random walk: +/- 0.40 percentage points per sample.
  const int stepHundredths = random(-40, 41);
  syntheticMoisture += static_cast<float>(stepHundredths) / 100.0f;

  if (syntheticMoisture < SYNTHETIC_MIN_MOISTURE) {
    syntheticMoisture = SYNTHETIC_MIN_MOISTURE;
  }
  if (syntheticMoisture > SYNTHETIC_MAX_MOISTURE) {
    syntheticMoisture = SYNTHETIC_MAX_MOISTURE;
  }

  return syntheticMoisture;
}

static bool postReading(float moisturePct) {
  if (!resolveFarmPi()) {
    return false;
  }

  WiFiClientSecure client;

  // Prototype-only choice: traffic is encrypted, but the ESP32 does not
  // validate Caddy's private-CA certificate. This avoids certificate-management
  // work while the synthetic sensor path is being proven.
  client.setInsecure();
  client.setTimeout(10000);

  Serial.printf(
    "Connecting to FarmPi %s:%u...\n",
    farmPiAddress.toString().c_str(),
    FARMPI_HTTPS_PORT
  );

  if (!client.connect(farmPiAddress, FARMPI_HTTPS_PORT)) {
    Serial.println("HTTPS connection to FarmPi failed.");
    farmPiAddress = IPAddress();
    return false;
  }

  String payload = "{\"sensor\":\"";
  payload += SENSOR_UID;
  payload += "\",\"soil_moisture_pct\":";
  payload += String(moisturePct, 2);
  payload += ",\"simulated\":true}";

  client.print("POST /api/ingest HTTP/1.1\r\n");
  client.print("Host: ");
  client.print(FARMPI_MDNS_HOST);
  client.print(".local\r\n");
  client.print("Authorization: Bearer ");
  client.print(FARMPI_INGEST_TOKEN);
  client.print("\r\n");
  client.print("Content-Type: application/json\r\n");
  client.print("Connection: close\r\n");
  client.print("Content-Length: ");
  client.print(payload.length());
  client.print("\r\n\r\n");
  client.print(payload);

  String statusLine = client.readStringUntil('\n');
  statusLine.trim();
  Serial.printf("FarmPi response: %s\n", statusLine.c_str());

  const bool accepted = statusLine.indexOf(" 201 ") >= 0;

  // Drain the small response so the serial console shows useful diagnostics.
  while (client.connected() || client.available()) {
    if (client.available()) {
      String line = client.readStringUntil('\n');
      line.trim();
      if (line.length() > 0) {
        Serial.println(line);
      }
    } else {
      delay(10);
    }
  }

  client.stop();
  return accepted;
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println();
  Serial.println("FarmPi synthetic ESP32 sensor starting");
  Serial.printf("Sensor UID: %s\n", SENSOR_UID);

  randomSeed(esp_random());
  connectWiFi();

  // Send immediately after boot rather than waiting for the first interval.
  lastSendMs = millis() - SEND_INTERVAL_MS;
}

void loop() {
  connectWiFi();

  if (WiFi.status() == WL_CONNECTED && millis() - lastSendMs >= SEND_INTERVAL_MS) {
    lastSendMs = millis();

    const float moisture = nextSyntheticMoisture();
    Serial.printf(
      "Synthetic reading: %.2f%% soil moisture (RSSI %d dBm)\n",
      moisture,
      WiFi.RSSI()
    );

    if (postReading(moisture)) {
      Serial.println("Reading accepted by FarmPi.");
    } else {
      Serial.println("Reading was not accepted; will try again next interval.");
    }
  }

  delay(100);
}
