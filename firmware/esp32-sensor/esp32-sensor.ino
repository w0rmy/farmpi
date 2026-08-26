#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <ESPmDNS.h>
#include <esp_system.h>
#include <time.h>

#include "config.h"

#ifndef VIRTUAL_PADDOCK_COUNT
#define VIRTUAL_PADDOCK_COUNT 16
#endif
#ifndef SIMULATION_ROUND_MS
#define SIMULATION_ROUND_MS 300000UL
#endif
#ifndef NZ_SIMULATION_LATITUDE
#define NZ_SIMULATION_LATITUDE -37.7870f
#endif
#ifndef NZ_SIMULATION_LONGITUDE
#define NZ_SIMULATION_LONGITUDE 175.2793f
#endif

// Waikato (Hamilton) is a fixed synthetic training profile, not a forecast or
// agronomic model. The POSIX rule makes Pacific/Auckland DST deterministic.
static const char* const FARM_TIMEZONE = "NZST-12NZDT,M9.5.0/2,M4.1.0/3";
static const float MONTHLY_LOW_C[12] = {13.2, 13.4, 11.5, 8.8, 6.6, 4.6, 4.3, 5.3, 7.4, 9.0, 10.6, 12.0};
static const float MONTHLY_HIGH_C[12] = {24.3, 24.5, 22.4, 19.2, 16.4, 14.1, 13.9, 15.0, 16.7, 18.6, 20.8, 22.8};
static const char* const SENSOR_UIDS[VIRTUAL_PADDOCK_COUNT] = {
  "test-moisture-a", "test-moisture-b", "test-moisture-c", "test-moisture-d", "test-moisture-e", "test-moisture-f", "test-moisture-g", "test-moisture-h",
  "test-moisture-i", "test-moisture-j", "test-moisture-k", "test-moisture-l", "test-moisture-m", "test-moisture-n", "test-moisture-o", "test-moisture-p"
};
static const unsigned long POST_INTERVAL_MS = SIMULATION_ROUND_MS / VIRTUAL_PADDOCK_COUNT;

struct FarmWeather { unsigned long roundNumber; unsigned int rainRoundsRemaining; float rainMm, cloudCover, pressureHpa, windSpeedKmh, windDirectionDeg; };
struct PaddockState { float moisture, soilTemperatureC, soilTemperatureOffset, airTemperatureOffset, humidityOffset, ph, ec, shade, pastureHeight, pastureGrowthRate, leafWetness; };
struct SyntheticReading { float soilMoisturePct, soilTemperatureC, airTemperatureC, relativeHumidityPct, soilPh, soilEcMsCm, lightLux, rainfallMm, barometricPressureHpa, windSpeedKmh, windDirectionDeg, pastureHeightCm, leafWetnessPct; };
struct SolarDay { float sunriseHours, sunsetHours, solarNoonHours, daylightFraction, localHours, dailyLowC, dailyHighC; };

static FarmWeather weather = {0, 0, 0.0f, 0.30f, 1015.0f, 8.0f, 225.0f};
static PaddockState paddocks[VIRTUAL_PADDOCK_COUNT];
static unsigned long lastPostMs = 0;
static uint8_t nextPaddock = 0;
static IPAddress farmPiAddress;
static time_t farmEpochAtSync = 0;
static unsigned long millisAtSync = 0;

static float clampFloat(float value, float minimum, float maximum) { return min(max(value, minimum), maximum); }
static float randomSigned(float magnitude) { return static_cast<float>(random(-1000, 1001)) / 1000.0f * magnitude; }
static bool clockIsValid() { return farmEpochAtSync >= 1577836800; }
static time_t farmNow() { return clockIsValid() ? farmEpochAtSync + (millis() - millisAtSync) / 1000UL : 0; }
static void setFarmTime(time_t epoch) { if (epoch >= 1577836800) { farmEpochAtSync = epoch; millisAtSync = millis(); } }

static void connectWiFi() {
  if (WiFi.status() == WL_CONNECTED) return;
  Serial.printf("Connecting to Wi-Fi SSID '%s'...\n", WIFI_SSID);
  WiFi.mode(WIFI_STA); WiFi.setHostname(DEVICE_HOSTNAME); WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  const unsigned long started = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - started < 20000UL) { delay(500); Serial.print('.'); }
  Serial.println();
  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("Wi-Fi connected: %s, RSSI %d dBm\n", WiFi.localIP().toString().c_str(), WiFi.RSSI());
    if (!MDNS.begin(DEVICE_HOSTNAME)) Serial.println("mDNS responder failed to start; FarmPi lookup may fail.");
  } else Serial.println("Wi-Fi connection timed out.");
}

static bool resolveFarmPi() {
  if (farmPiAddress != IPAddress()) return true;
  Serial.printf("Resolving %s.local via mDNS...\n", FARMPI_MDNS_HOST);
  farmPiAddress = MDNS.queryHost(FARMPI_MDNS_HOST, 3000);
  if (farmPiAddress == IPAddress()) { Serial.println("FarmPi mDNS lookup failed."); return false; }
  Serial.printf("FarmPi resolved to %s\n", farmPiAddress.toString().c_str()); return true;
}

static SolarDay solarDay() {
  // No Internet NTP is used: localtime_r converts the FarmPi-synchronised UTC.
  time_t now = farmNow(); tm local = {};
  if (now > 0) localtime_r(&now, &local);
  const int month = clockIsValid() ? local.tm_mon : 6;
  const int dayOfYear = clockIsValid() ? local.tm_yday + 1 : 182;
  const float localHours = clockIsValid() ? local.tm_hour + local.tm_min / 60.0f + local.tm_sec / 3600.0f : 12.0f;
  const float gamma = 2.0f * PI / 365.0f * (dayOfYear - 1 + (localHours - 12.0f) / 24.0f);
  const float declination = 0.006918f - 0.399912f * cosf(gamma) + 0.070257f * sinf(gamma) - 0.006758f * cosf(2 * gamma) + 0.000907f * sinf(2 * gamma) - 0.002697f * cosf(3 * gamma) + 0.00148f * sinf(3 * gamma);
  const float equationOfTime = 229.18f * (0.000075f + 0.001868f * cosf(gamma) - 0.032077f * sinf(gamma) - 0.014615f * cosf(2 * gamma) - 0.040849f * sinf(2 * gamma));
  const float latitudeRadians = NZ_SIMULATION_LATITUDE * PI / 180.0f;
  const float cosHourAngle = clampFloat((cosf(90.833f * PI / 180.0f) - sinf(latitudeRadians) * sinf(declination)) / (cosf(latitudeRadians) * cosf(declination)), -1.0f, 1.0f);
  const float daylightHours = 2.0f * acosf(cosHourAngle) * 180.0f / PI / 15.0f;
  const float utcOffset = (clockIsValid() && local.tm_isdst > 0) ? 13.0f : 12.0f;
  const float solarNoon = 12.0f + utcOffset - NZ_SIMULATION_LONGITUDE / 15.0f - equationOfTime / 60.0f;
  const float sunrise = solarNoon - daylightHours / 2.0f, sunset = solarNoon + daylightHours / 2.0f;
  float daylightFraction = 0.0f;
  if (localHours >= sunrise && localHours <= sunset) daylightFraction = sinf(PI * (localHours - sunrise) / daylightHours);
  return {sunrise, sunset, solarNoon, clampFloat(daylightFraction, 0.0f, 1.0f), localHours, MONTHLY_LOW_C[month], MONTHLY_HIGH_C[month]};
}

static float airTemperatureFor(const SolarDay& sun, float paddockOffset) {
  // Lowest shortly after sunrise, highest in mid-afternoon, then night cooling.
  const float minHour = sun.sunriseHours + 0.5f, maxHour = sun.solarNoonHours + 3.0f, range = sun.dailyHighC - sun.dailyLowC;
  float base;
  if (sun.localHours >= minHour && sun.localHours <= maxHour) base = sun.dailyLowC + range * sinf((sun.localHours - minHour) / (maxHour - minHour) * PI / 2.0f);
  else { const float afterMax = sun.localHours > maxHour ? sun.localHours - maxHour : sun.localHours + 24.0f - maxHour; base = sun.dailyLowC + range * cosf(afterMax / (24.0f - (maxHour - minHour)) * PI / 2.0f); }
  return clampFloat(base + paddockOffset - weather.cloudCover * 1.2f - (weather.rainRoundsRemaining ? 0.9f : 0.0f) + randomSigned(0.25f), -5.0f, 35.0f);
}

static void initialisePaddocks() {
  for (uint8_t index = 0; index < VIRTUAL_PADDOCK_COUNT; ++index) {
    const float character = static_cast<float>(index) - 7.5f;
    paddocks[index] = {23.0f + character * 0.9f, 12.0f + character * 0.05f, character * 0.05f, character * 0.07f, -character * 0.5f, 6.3f + character * 0.035f, 0.50f + character * 0.018f, clampFloat(0.82f + static_cast<float>(index % 5) * 0.04f, 0.75f, 0.98f), 12.0f + static_cast<float>(index % 7), 0.012f + static_cast<float>(index % 4) * 0.003f, 5.0f};
  }
}

static void advanceFarmRound(const SolarDay& sun) {
  // Persistent world state advances once per 16-post, five-minute round only.
  weather.roundNumber++;
  if (weather.rainRoundsRemaining == 0 && random(0, 1000) < 2) { weather.rainRoundsRemaining = random(3, 19); weather.rainMm = static_cast<float>(random(5, 36)) / 10.0f; weather.cloudCover = clampFloat(weather.cloudCover + 0.35f, 0.35f, 0.95f); }
  const bool raining = weather.rainRoundsRemaining > 0;
  if (raining) { weather.rainRoundsRemaining--; weather.pressureHpa = clampFloat(weather.pressureHpa - 0.45f + randomSigned(0.15f), 970.0f, 1040.0f); }
  else { weather.rainMm = 0.0f; weather.cloudCover = clampFloat(weather.cloudCover + randomSigned(0.08f) - 0.015f, 0.05f, 0.80f); weather.pressureHpa = clampFloat(weather.pressureHpa + randomSigned(0.28f) + 0.04f, 970.0f, 1040.0f); }
  weather.windSpeedKmh = clampFloat(weather.windSpeedKmh + randomSigned(2.5f) + (raining ? 1.5f : 0.0f), 0.0f, 75.0f); weather.windDirectionDeg = fmodf(weather.windDirectionDeg + randomSigned(18.0f) + 360.0f, 360.0f);
  for (uint8_t index = 0; index < VIRTUAL_PADDOCK_COUNT; ++index) {
    PaddockState& state = paddocks[index]; const float air = airTemperatureFor(sun, state.airTemperatureOffset); const float mean = (sun.dailyLowC + sun.dailyHighC) / 2.0f;
    state.soilTemperatureC += 0.05f * (mean + state.soilTemperatureOffset + 0.25f * (air - mean) - state.soilTemperatureC);
    state.moisture = clampFloat(state.moisture + (raining ? weather.rainMm * 0.55f : -0.025f - sun.daylightFraction * 0.045f) + randomSigned(0.08f), 5.0f, 95.0f);
    state.leafWetness = clampFloat(state.leafWetness + (raining ? 25.0f : -2.5f - sun.daylightFraction * 1.5f) + randomSigned(1.0f), 0.0f, 100.0f); state.ph = clampFloat(state.ph + randomSigned(0.004f), 5.2f, 7.7f); state.ec = clampFloat(state.ec + randomSigned(0.003f), 0.1f, 1.5f);
    state.pastureHeight = clampFloat(state.pastureHeight + state.pastureGrowthRate + randomSigned(0.01f), 2.0f, 45.0f); if (random(0, 20000) < 3) state.pastureHeight = clampFloat(state.pastureHeight - random(3, 9), 2.0f, 45.0f);
  }
}

static SyntheticReading readingFor(uint8_t index, const SolarDay& sun) {
  const bool raining = weather.rainRoundsRemaining > 0; const PaddockState& state = paddocks[index]; const float air = airTemperatureFor(sun, state.airTemperatureOffset);
  return {state.moisture, clampFloat(state.soilTemperatureC, 2.0f, 28.0f), air, clampFloat(78.0f - 24.0f * sun.daylightFraction + state.humidityOffset + weather.cloudCover * 8.0f + (raining ? 16.0f : 0.0f), 25.0f, 100.0f), state.ph, state.ec, clampFloat(95000.0f * sun.daylightFraction * state.shade * (1.0f - weather.cloudCover * 0.72f), 0.0f, 90000.0f), raining ? weather.rainMm : 0.0f, weather.pressureHpa, weather.windSpeedKmh, weather.windDirectionDeg, state.pastureHeight, state.leafWetness};
}

static long extractServerTime(const String& response) { const int marker = response.indexOf("\"server_time\":"); if (marker < 0) return 0; int start = marker + 14; while (start < response.length() && !isDigit(response[start])) start++; int end = start; while (end < response.length() && isDigit(response[end])) end++; return response.substring(start, end).toInt(); }

static bool postReading(const char* sensorUid, const SyntheticReading& reading) {
  if (!resolveFarmPi()) return false;
  WiFiClientSecure client;
  // Android verifies the local CA. ESP32 private-CA pinning remains a bounded,
  // documented alpha follow-up so existing installed generators keep working.
  client.setInsecure(); client.setTimeout(10000); client.setHandshakeTimeout(10);
  const String tlsHost = String(FARMPI_MDNS_HOST) + ".local";
  if (!client.connect(farmPiAddress, FARMPI_HTTPS_PORT, tlsHost.c_str(), nullptr, nullptr, nullptr)) { char errorBuffer[160] = {0}; Serial.printf("HTTPS connection failed (TLS error %d: %s).\n", client.lastError(errorBuffer, sizeof(errorBuffer)), errorBuffer); farmPiAddress = IPAddress(); return false; }
  const bool validTime = clockIsValid(); const uint32_t epoch = validTime ? static_cast<uint32_t>(farmNow()) : 0;
  String payload = "{\"sensor\":\"" + String(sensorUid) + "\",\"protocol_version\":1,\"device_time_unix\":" + String(epoch) + ",\"clock_valid\":" + (validTime ? "true" : "false") + ",\"sample_seq\":" + String(epoch);
  payload += ",\"soil_moisture_pct\":" + String(reading.soilMoisturePct, 2) + ",\"soil_temperature_c\":" + String(reading.soilTemperatureC, 2) + ",\"air_temperature_c\":" + String(reading.airTemperatureC, 2) + ",\"relative_humidity_pct\":" + String(reading.relativeHumidityPct, 2) + ",\"soil_ph\":" + String(reading.soilPh, 2) + ",\"soil_ec_ms_cm\":" + String(reading.soilEcMsCm, 2) + ",\"light_lux\":" + String(reading.lightLux, 0);
  payload += ",\"rainfall_mm\":" + String(reading.rainfallMm, 2) + ",\"barometric_pressure_hpa\":" + String(reading.barometricPressureHpa, 1) + ",\"wind_speed_kmh\":" + String(reading.windSpeedKmh, 1) + ",\"wind_direction_deg\":" + String(reading.windDirectionDeg, 0) + ",\"pasture_height_cm\":" + String(reading.pastureHeightCm, 1) + ",\"leaf_wetness_pct\":" + String(reading.leafWetnessPct, 1) + ",\"simulated\":true}";
  client.print("POST /api/ingest HTTP/1.1\r\nHost: "); client.print(tlsHost); client.print("\r\nAuthorization: Bearer "); client.print(FARMPI_INGEST_TOKEN); client.print("\r\nContent-Type: application/json\r\nConnection: close\r\nContent-Length: "); client.print(payload.length()); client.print("\r\n\r\n"); client.print(payload);
  String statusLine = client.readStringUntil('\n'); statusLine.trim(); const String response = client.readString(); client.stop(); Serial.printf("FarmPi response: %s\n", statusLine.c_str());
  const bool accepted = statusLine.indexOf(" 201 ") >= 0; const long serverTime = extractServerTime(response);
  if (accepted && serverTime > 0 && (!validTime || response.indexOf("\"time_sync_required\":true") >= 0)) { setFarmTime(static_cast<time_t>(serverTime)); Serial.printf("FarmPi UTC time synchronised: %ld\n", serverTime); }
  return accepted;
}

void setup() {
  Serial.begin(115200); delay(1000); Serial.println("\nFarmPi real-time NZ 16-paddock synthetic ESP32 generator starting");
  Serial.printf("Posts are staggered every %lu ms; one round is %lu ms. FarmPi is the clock authority.\n", POST_INTERVAL_MS, SIMULATION_ROUND_MS);
  setenv("TZ", FARM_TIMEZONE, 1); tzset(); randomSeed(esp_random()); initialisePaddocks(); connectWiFi(); lastPostMs = millis() - POST_INTERVAL_MS;
}

void loop() {
  connectWiFi();
  if (WiFi.status() == WL_CONNECTED && millis() - lastPostMs >= POST_INTERVAL_MS) {
    lastPostMs = millis(); const SolarDay sun = solarDay(); if (nextPaddock == 0) advanceFarmRound(sun); const SyntheticReading reading = readingFor(nextPaddock, sun);
    Serial.printf("Round %lu, Paddock %c: clock %s, daylight %.2f, air %.1fC, rain %.2fmm\n", weather.roundNumber, 'A' + nextPaddock, clockIsValid() ? "synced" : "awaiting FarmPi", sun.daylightFraction, reading.airTemperatureC, reading.rainfallMm);
    if (postReading(SENSOR_UIDS[nextPaddock], reading)) Serial.println("Reading accepted by FarmPi."); else Serial.println("Reading was not accepted; this virtual node retries next round.");
    nextPaddock = (nextPaddock + 1) % VIRTUAL_PADDOCK_COUNT;
  }
  delay(100);
}
