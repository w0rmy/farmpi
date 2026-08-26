#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <ESPmDNS.h>
#include <esp_system.h>

#include "config.h"

static float syntheticMoisture = SYNTHETIC_START_MOISTURE;
static float syntheticTemperatureBase = SYNTHETIC_START_AIR_TEMPERATURE_C;
static float syntheticHumidity = SYNTHETIC_START_RELATIVE_HUMIDITY_PCT;
static float syntheticSoilPh = SYNTHETIC_START_SOIL_PH;
static float syntheticLightOffset = 0.0f;
static unsigned long lastSendMs = 0;
static IPAddress farmPiAddress;
static unsigned long sampleNumber = 0;

struct SyntheticReading {
  float soilMoisturePct;
  float airTemperatureC;
  float relativeHumidityPct;
  float soilPh;
  float lightLux;
};

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

static float clampFloat(float value, float minimum, float maximum) {
  return min(max(value, minimum), maximum);
}

static float nextBoundedWalk(float current, float minimum, float maximum, float maxStep) {
  const float step = static_cast<float>(random(-1000, 1001)) / 1000.0f * maxStep;
  return clampFloat(current + step, minimum, maximum);
}

static SyntheticReading nextSyntheticReading() {
  // 288 five-minute samples make one gentle synthetic 24-hour cycle. It is a
  // test pattern only; the ESP32 does not need a real-time clock in this stage.
  const float phase = 2.0f * PI * static_cast<float>(sampleNumber % 288UL) / 288.0f;
  const float daylight = max(0.0f, sinf(phase - PI / 2.0f));
  sampleNumber++;

  syntheticMoisture = nextBoundedWalk(
    syntheticMoisture, SYNTHETIC_MIN_MOISTURE, SYNTHETIC_MAX_MOISTURE, 0.40f
  );
  syntheticTemperatureBase = nextBoundedWalk(syntheticTemperatureBase, 8.0f, 22.0f, 0.20f);
  syntheticHumidity = nextBoundedWalk(syntheticHumidity, 35.0f, 95.0f, 1.20f);
  syntheticSoilPh = nextBoundedWalk(syntheticSoilPh, 5.5f, 7.5f, 0.03f);
  syntheticLightOffset = nextBoundedWalk(syntheticLightOffset, -4000.0f, 4000.0f, 600.0f);

  SyntheticReading reading = {
    syntheticMoisture,
    clampFloat(syntheticTemperatureBase + 4.0f * sinf(phase - PI / 2.0f), 2.0f, 30.0f),
    syntheticHumidity,
    syntheticSoilPh,
    clampFloat(65000.0f * daylight + syntheticLightOffset, 0.0f, 70000.0f),
  };
  return reading;
}

static bool postReading(const SyntheticReading& reading) {
  if (!resolveFarmPi()) {
    return false;
  }

  WiFiClientSecure client;

  // Prototype-only choice: traffic is encrypted, but the ESP32 does not
  // validate Caddy's private-CA certificate. This avoids certificate-management
  // work while the synthetic sensor path is being proven.
  client.setInsecure();
  client.setTimeout(10000);
  client.setHandshakeTimeout(10);

  const String tlsHost = String(FARMPI_MDNS_HOST) + ".local";

  Serial.printf(
    "Connecting to FarmPi %s:%u using TLS hostname %s...\n",
    farmPiAddress.toString().c_str(),
    FARMPI_HTTPS_PORT,
    tlsHost.c_str()
  );

  // Connect to the address obtained through mDNS, but also supply farmpi.local
  // as the TLS hostname. Caddy selects the correct certificate/site using SNI;
  // connecting by IP alone does not provide that hostname during the handshake.
  if (!client.connect(
        farmPiAddress,
        FARMPI_HTTPS_PORT,
        tlsHost.c_str(),
        nullptr,
        nullptr,
        nullptr)) {
    char errorBuffer[160] = {0};
    const int errorCode = client.lastError(errorBuffer, sizeof(errorBuffer));
    Serial.printf(
      "HTTPS connection to FarmPi failed (TLS error %d: %s).\n",
      errorCode,
      errorBuffer
    );
    farmPiAddress = IPAddress();
    return false;
  }

  String payload = "{\"sensor\":\"";
  payload += SENSOR_UID;
  payload += "\",\"soil_moisture_pct\":";
  payload += String(reading.soilMoisturePct, 2);
  payload += ",\"air_temperature_c\":";
  payload += String(reading.airTemperatureC, 2);
  payload += ",\"relative_humidity_pct\":";
  payload += String(reading.relativeHumidityPct, 2);
  payload += ",\"soil_ph\":";
  payload += String(reading.soilPh, 2);
  payload += ",\"light_lux\":";
  payload += String(reading.lightLux, 2);
  payload += ",\"simulated\":true}";

  client.print("POST /api/ingest HTTP/1.1\r\n");
  client.print("Host: ");
  client.print(tlsHost);
  client.print("\r\n");
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

    const SyntheticReading reading = nextSyntheticReading();
    Serial.printf(
      "Synthetic reading: moisture %.2f%%, air %.2fC, humidity %.2f%%, pH %.2f, light %.0f lux (RSSI %d dBm)\n",
      reading.soilMoisturePct,
      reading.airTemperatureC,
      reading.relativeHumidityPct,
      reading.soilPh,
      reading.lightLux,
      WiFi.RSSI()
    );

    if (postReading(reading)) {
      Serial.println("Reading accepted by FarmPi.");
    } else {
      Serial.println("Reading was not accepted; will try again next interval.");
    }
  }

  delay(100);
}
