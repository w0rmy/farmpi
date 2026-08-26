#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <ESPmDNS.h>
#include <esp_system.h>

#include "config.h"

// A physical ESP32 represents these virtual nodes. Older config.h files can
// retain their old sensor/start macros; they are deliberately harmless here.
#ifndef VIRTUAL_PADDOCK_COUNT
#define VIRTUAL_PADDOCK_COUNT 16
#endif
#ifndef SIMULATION_ROUND_MS
#define SIMULATION_ROUND_MS 300000UL
#endif

static const char* const SENSOR_UIDS[VIRTUAL_PADDOCK_COUNT] = {
  "test-moisture-a", "test-moisture-b", "test-moisture-c", "test-moisture-d",
  "test-moisture-e", "test-moisture-f", "test-moisture-g", "test-moisture-h",
  "test-moisture-i", "test-moisture-j", "test-moisture-k", "test-moisture-l",
  "test-moisture-m", "test-moisture-n", "test-moisture-o", "test-moisture-p"
};
static const unsigned long POST_INTERVAL_MS = SIMULATION_ROUND_MS / VIRTUAL_PADDOCK_COUNT;

struct FarmWeather {
  unsigned long roundNumber;
  unsigned int rainRoundsRemaining;
  float rainMm;
  float pressureHpa;
  float windSpeedKmh;
  float windDirectionDeg;
};

struct PaddockState {
  float moisture;
  float soilTemperatureOffset;
  float airTemperatureOffset;
  float humidityOffset;
  float ph;
  float ec;
  float shade;
  float pastureHeight;
  float pastureGrowthRate;
  float leafWetness;
};

struct SyntheticReading {
  float soilMoisturePct, soilTemperatureC, airTemperatureC, relativeHumidityPct;
  float soilPh, soilEcMsCm, lightLux, rainfallMm, barometricPressureHpa;
  float windSpeedKmh, windDirectionDeg, pastureHeightCm, leafWetnessPct;
};

static FarmWeather weather = {0, 0, 0.0f, 1015.0f, 8.0f, 225.0f};
static PaddockState paddocks[VIRTUAL_PADDOCK_COUNT];
static unsigned long lastPostMs = 0;
static uint8_t nextPaddock = 0;
static IPAddress farmPiAddress;

static float clampFloat(float value, float minimum, float maximum) {
  return min(max(value, minimum), maximum);
}

static float randomSigned(float magnitude) {
  return static_cast<float>(random(-1000, 1001)) / 1000.0f * magnitude;
}

static void connectWiFi() {
  if (WiFi.status() == WL_CONNECTED) return;
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
    Serial.printf("Wi-Fi connected: %s, RSSI %d dBm\n", WiFi.localIP().toString().c_str(), WiFi.RSSI());
    if (!MDNS.begin(DEVICE_HOSTNAME)) Serial.println("mDNS responder failed to start; FarmPi lookup may fail.");
  } else {
    Serial.println("Wi-Fi connection timed out.");
  }
}

static bool resolveFarmPi() {
  if (farmPiAddress != IPAddress()) return true;
  Serial.printf("Resolving %s.local via mDNS...\n", FARMPI_MDNS_HOST);
  farmPiAddress = MDNS.queryHost(FARMPI_MDNS_HOST, 3000);
  if (farmPiAddress == IPAddress()) {
    Serial.println("FarmPi mDNS lookup failed.");
    return false;
  }
  Serial.printf("FarmPi resolved to %s\n", farmPiAddress.toString().c_str());
  return true;
}

static void initialisePaddocks() {
  for (uint8_t index = 0; index < VIRTUAL_PADDOCK_COUNT; ++index) {
    // Stable per-paddock character: even indexes are a little drier/brighter,
    // odd indexes a little wetter/shadier. Values persist across full rounds.
    const float character = static_cast<float>(index) - 7.5f;
    paddocks[index] = {
      23.0f + character * 0.9f,
      character * 0.05f, character * 0.07f, -character * 0.5f,
      6.3f + character * 0.035f, 0.50f + character * 0.018f,
      clampFloat(0.82f + static_cast<float>(index % 5) * 0.04f, 0.75f, 0.98f),
      12.0f + static_cast<float>(index % 7), 0.012f + static_cast<float>(index % 4) * 0.003f,
      5.0f
    };
  }
}

static void advanceFarmRound() {
  // Only this function advances simulation time. It runs once before Paddock A
  // in each 16-post round, never once per HTTPS POST.
  weather.roundNumber++;
  if (weather.rainRoundsRemaining == 0 && random(0, 1000) < 18) {
    weather.rainRoundsRemaining = random(3, 19);  // 15–90 minute rain event.
    weather.rainMm = static_cast<float>(random(5, 36)) / 10.0f;
  }
  const bool raining = weather.rainRoundsRemaining > 0;
  if (raining) {
    weather.rainRoundsRemaining--;
    weather.pressureHpa = clampFloat(weather.pressureHpa - 0.45f + randomSigned(0.15f), 970.0f, 1040.0f);
  } else {
    weather.rainMm = 0.0f;
    weather.pressureHpa = clampFloat(weather.pressureHpa + randomSigned(0.28f) + 0.04f, 970.0f, 1040.0f);
  }
  weather.windSpeedKmh = clampFloat(weather.windSpeedKmh + randomSigned(2.5f) + (raining ? 1.5f : 0.0f), 0.0f, 75.0f);
  weather.windDirectionDeg = fmodf(weather.windDirectionDeg + randomSigned(18.0f) + 360.0f, 360.0f);

  for (uint8_t index = 0; index < VIRTUAL_PADDOCK_COUNT; ++index) {
    PaddockState& state = paddocks[index];
    state.moisture = clampFloat(state.moisture + (raining ? weather.rainMm * 0.55f : -0.10f) + randomSigned(0.16f), 5.0f, 95.0f);
    state.leafWetness = clampFloat(state.leafWetness + (raining ? 25.0f : -4.0f) + randomSigned(2.0f), 0.0f, 100.0f);
    state.ph = clampFloat(state.ph + randomSigned(0.008f), 5.2f, 7.7f);
    state.ec = clampFloat(state.ec + randomSigned(0.006f), 0.1f, 1.5f);
    state.pastureHeight = clampFloat(state.pastureHeight + state.pastureGrowthRate + randomSigned(0.01f), 2.0f, 45.0f);
    // Rare, explicit grazing/cutting event, not a causal farm recommendation.
    if (random(0, 20000) < 3) state.pastureHeight = clampFloat(state.pastureHeight - random(3, 9), 2.0f, 45.0f);
  }
}

static SyntheticReading readingFor(uint8_t index) {
  const float phase = 2.0f * PI * static_cast<float>(weather.roundNumber % 288UL) / 288.0f;
  const float daylight = max(0.0f, sinf(phase - PI / 2.0f));
  const bool raining = weather.rainRoundsRemaining > 0;
  const PaddockState& state = paddocks[index];
  const float air = clampFloat(14.0f + 7.0f * sinf(phase - PI / 2.0f) + state.airTemperatureOffset - (raining ? 2.0f : 0.0f), -5.0f, 35.0f);
  return {
    state.moisture,
    clampFloat(12.0f + 4.0f * sinf(phase - PI / 2.0f) + state.soilTemperatureOffset - (raining ? 0.5f : 0.0f), 2.0f, 28.0f),
    air,
    clampFloat(62.0f - 18.0f * daylight + state.humidityOffset + (raining ? 22.0f : 0.0f), 25.0f, 100.0f),
    state.ph, state.ec,
    clampFloat(72000.0f * daylight * state.shade * (raining ? 0.35f : 1.0f), 0.0f, 90000.0f),
    raining ? weather.rainMm : 0.0f, weather.pressureHpa, weather.windSpeedKmh,
    weather.windDirectionDeg, state.pastureHeight, state.leafWetness
  };
}

static bool postReading(const char* sensorUid, const SyntheticReading& reading) {
  if (!resolveFarmPi()) return false;
  WiFiClientSecure client;
  // Prototype TLS choice: encrypted transport, private-CA verification omitted.
  client.setInsecure();
  client.setTimeout(10000);
  client.setHandshakeTimeout(10);
  const String tlsHost = String(FARMPI_MDNS_HOST) + ".local";
  Serial.printf("Connecting %s to FarmPi %s:%u using TLS hostname %s...\n", sensorUid, farmPiAddress.toString().c_str(), FARMPI_HTTPS_PORT, tlsHost.c_str());
  // IP connection plus explicit host retains the prior Caddy/SNI fix.
  if (!client.connect(farmPiAddress, FARMPI_HTTPS_PORT, tlsHost.c_str(), nullptr, nullptr, nullptr)) {
    char errorBuffer[160] = {0};
    Serial.printf("HTTPS connection failed (TLS error %d: %s).\n", client.lastError(errorBuffer, sizeof(errorBuffer)), errorBuffer);
    farmPiAddress = IPAddress();
    return false;
  }
  String payload = "{\"sensor\":\"" + String(sensorUid) + "\",\"soil_moisture_pct\":" + String(reading.soilMoisturePct, 2);
  payload += ",\"soil_temperature_c\":" + String(reading.soilTemperatureC, 2);
  payload += ",\"air_temperature_c\":" + String(reading.airTemperatureC, 2);
  payload += ",\"relative_humidity_pct\":" + String(reading.relativeHumidityPct, 2);
  payload += ",\"soil_ph\":" + String(reading.soilPh, 2);
  payload += ",\"soil_ec_ms_cm\":" + String(reading.soilEcMsCm, 2);
  payload += ",\"light_lux\":" + String(reading.lightLux, 0);
  payload += ",\"rainfall_mm\":" + String(reading.rainfallMm, 2);
  payload += ",\"barometric_pressure_hpa\":" + String(reading.barometricPressureHpa, 1);
  payload += ",\"wind_speed_kmh\":" + String(reading.windSpeedKmh, 1);
  payload += ",\"wind_direction_deg\":" + String(reading.windDirectionDeg, 0);
  payload += ",\"pasture_height_cm\":" + String(reading.pastureHeightCm, 1);
  payload += ",\"leaf_wetness_pct\":" + String(reading.leafWetnessPct, 1);
  payload += ",\"simulated\":true}";
  client.print("POST /api/ingest HTTP/1.1\r\nHost: ");
  client.print(tlsHost);
  client.print("\r\nAuthorization: Bearer ");
  client.print(FARMPI_INGEST_TOKEN);
  client.print("\r\nContent-Type: application/json\r\nConnection: close\r\nContent-Length: ");
  client.print(payload.length());
  client.print("\r\n\r\n");
  client.print(payload);
  String statusLine = client.readStringUntil('\n');
  statusLine.trim();
  Serial.printf("FarmPi response: %s\n", statusLine.c_str());
  const bool accepted = statusLine.indexOf(" 201 ") >= 0;
  while (client.connected() || client.available()) {
    if (client.available()) Serial.println(client.readStringUntil('\n'));
    else delay(10);
  }
  client.stop();
  return accepted;
}

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\nFarmPi 16-paddock synthetic ESP32 generator starting");
  Serial.printf("Posts are staggered every %lu ms; one round is %lu ms.\n", POST_INTERVAL_MS, SIMULATION_ROUND_MS);
  randomSeed(esp_random());
  initialisePaddocks();
  connectWiFi();
  lastPostMs = millis() - POST_INTERVAL_MS;  // send Paddock A immediately
}

void loop() {
  connectWiFi();
  if (WiFi.status() == WL_CONNECTED && millis() - lastPostMs >= POST_INTERVAL_MS) {
    lastPostMs = millis();
    if (nextPaddock == 0) advanceFarmRound();
    const SyntheticReading reading = readingFor(nextPaddock);
    Serial.printf("Round %lu, Paddock %c: moisture %.2f%%, air %.1fC, rain %.2fmm, pasture %.1fcm (RSSI %d dBm)\n",
      weather.roundNumber, 'A' + nextPaddock, reading.soilMoisturePct, reading.airTemperatureC,
      reading.rainfallMm, reading.pastureHeightCm, WiFi.RSSI());
    if (postReading(SENSOR_UIDS[nextPaddock], reading)) Serial.println("Reading accepted by FarmPi.");
    else Serial.println("Reading was not accepted; this virtual node retries next round.");
    nextPaddock = (nextPaddock + 1) % VIRTUAL_PADDOCK_COUNT;
  }
  delay(100);
}
