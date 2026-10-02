#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <Preferences.h>
#include <ArduinoJson.h>
#include <esp_mac.h>
#include <esp_system.h>
#include <mbedtls/sha256.h>
#include <math.h>
#include <time.h>
#include <sys/time.h>
#include "config.h"
#include "board_profile.h"

#if !CONFIG_IDF_TARGET_ESP32S3
#error "Select the verified ESP32-S3 board target"
#endif

static Preferences nvs;
static String hardwareUid, deviceKey, nodeUid, appliedHash, appliedCanonical;
static JsonDocument activeConfig;
static uint32_t lastContact = 0;
static uint32_t lastTelemetry = 0;
static uint64_t sampleSeq = 0;
static uint64_t locationEpoch = 0;
static bool storageReady = false;
static const uint32_t CONTACT_INTERVAL_MS = 15000UL;
static const uint32_t TELEMETRY_INTERVAL_MS = 60000UL;

// Representative Waikato/Hamilton synthetic profile. This is deliberately
// realistic-looking test telemetry, not a weather forecast or agronomic model.
static const char* FARM_TIMEZONE = "NZST-12NZDT,M9.5.0/2,M4.1.0/3";
static const float NZ_SIMULATION_LATITUDE = -37.7870f;
static const float NZ_SIMULATION_LONGITUDE = 175.2793f;
static const float MONTHLY_LOW_C[12] = {13.2f, 13.4f, 11.5f, 8.8f, 6.6f, 4.6f, 4.3f, 5.3f, 7.4f, 9.0f, 10.6f, 12.0f};
static const float MONTHLY_HIGH_C[12] = {24.3f, 24.5f, 22.4f, 19.2f, 16.4f, 14.1f, 13.9f, 15.0f, 16.7f, 18.6f, 20.8f, 22.8f};

struct SimulationContext {
  time_t now;
  tm local;
  int dayOfYear;
  int daySerial;
  float localHours;
  float sunriseHours;
  float sunsetHours;
  float solarNoonHours;
  float daylightFraction;
  float cloudCover;
  float nodeVariation;
};

struct RainEvent {
  bool active;
  float intervalMm;
  float recentSoilEffect;
};

static String hexBytes(const uint8_t* bytes, size_t count) {
  String out; out.reserve(count * 2);
  const char hex[] = "0123456789abcdef";
  for (size_t i = 0; i < count; ++i) { out += hex[bytes[i] >> 4]; out += hex[bytes[i] & 15]; }
  return out;
}

static String sha256(const String& value) {
  uint8_t digest[32];
  if (mbedtls_sha256(reinterpret_cast<const unsigned char*>(value.c_str()), value.length(), digest, 0) != 0) return "";
  return hexBytes(digest, 32);
}

static bool supports(const String& key) {
  for (size_t i = 0; i < CONFIGURABLE_COUNT; ++i) if (key == CONFIGURABLE_MEASUREMENTS[i]) return true;
  return false;
}

static bool supportsLive(const String& key) {
  for (size_t i = 0; i < LIVE_COUNT; ++i) if (key == LIVE_MEASUREMENTS[i]) return true;
  return false;
}

static bool validMode(const String& mode) {
  return mode == "OFF" || mode == "SIMULATED" || mode == "LIVE";
}

static bool validate(const String& text, const String& hash, const String& uid, JsonDocument& parsed) {
  if (text.length() > 4096 || hash.length() != 64 || sha256(text) != hash || deserializeJson(parsed, text)) return false;
  if (!parsed.is<JsonObject>() || parsed.size() != 3 || !parsed["schema_version"].is<int>() ||
      parsed["schema_version"].as<int>() != 2 || parsed["node_uid"].as<String>() != uid ||
      !parsed["modes"].is<JsonObject>()) return false;

  JsonObject modes = parsed["modes"].as<JsonObject>();
  if (modes.size() != CONFIGURABLE_COUNT) return false;
  for (JsonPair pair : modes) {
    const String key = pair.key().c_str();
    const String mode = pair.value().as<String>();
    if (!supports(key) || !validMode(mode) || (mode == "LIVE" && !supportsLive(key))) return false;
  }

  // Reconstruct the exact server canonical form. CONFIGURABLE_MEASUREMENTS is
  // alphabetically sorted, as are the top-level keys below.
  JsonDocument canonical;
  JsonObject rebuiltModes = canonical["modes"].to<JsonObject>();
  for (size_t i = 0; i < CONFIGURABLE_COUNT; ++i) {
    const char* key = CONFIGURABLE_MEASUREMENTS[i];
    rebuiltModes[key] = modes[key];
  }
  canonical["node_uid"] = uid;
  canonical["schema_version"] = 2;
  String rebuilt; serializeJson(canonical, rebuilt);
  return rebuilt == text;
}

static void auth(JsonDocument& request) {
  request["hardware_uid"] = hardwareUid;
  request["device_key"] = deviceKey;
}

static bool post(const char* path, JsonDocument& request, JsonDocument& response) {
  WiFiClientSecure tls; tls.setCACert(FARMPI_ROOT_CA);
  HTTPClient http; http.setTimeout(8000);
  if (!http.begin(tls, String(FARMPI_URL) + path)) return false;
  http.addHeader("Content-Type", "application/json");
  String body; serializeJson(request, body);
  int status = http.POST(body);
  if (status < 200 || status >= 300 || http.getSize() > 8192) {
    Serial.printf("FarmPi HTTP %d\n", status);
    http.end();
    return false;
  }
  String returned = http.getString(); http.end();
  return returned.length() <= 8192 && !deserializeJson(response, returned);
}

static void acknowledge(const String& hash, const char* error = nullptr) {
  JsonDocument request, response; auth(request); request["fingerprint"] = hash;
  if (error) request["error"] = error; else request["config"] = activeConfig;
  post("/api/nodes/ack", request, response);
}

static bool restore() {
  const uint8_t selected = nvs.getUChar("slot", 0);
  for (int attempt = 0; attempt < 2; ++attempt) {
    String blob = nvs.getString((selected ^ attempt) ? "config1" : "config0", "");
    JsonDocument envelope, parsed;
    if (deserializeJson(envelope, blob)) continue;
    String text = envelope["canonical"].as<String>();
    String hash = envelope["fingerprint"].as<String>();
    String uid = envelope["node_uid"].as<String>();
    if (!uid.startsWith("FP-") || !validate(text, hash, uid, parsed)) continue;
    activeConfig = parsed; appliedCanonical = text; appliedHash = hash; nodeUid = uid;
    if (attempt) nvs.putUChar("slot", selected ^ 1);
    return true;
  }
  return false;
}

static bool persistAndApply(const String& text, const String& hash, const String& uid, JsonDocument& parsed) {
  uint8_t candidate = nvs.getUChar("slot", 0) ^ 1;
  const char* key = candidate ? "config1" : "config0";
  JsonDocument envelope; envelope["canonical"] = text; envelope["fingerprint"] = hash; envelope["node_uid"] = uid;
  String blob; serializeJson(envelope, blob);
  if (nvs.putString(key, blob) != blob.length() || nvs.getString(key, "") != blob) return false;
  if (nvs.putUChar("slot", candidate) != 1) return false;
  activeConfig = parsed; appliedCanonical = text; appliedHash = hash; nodeUid = uid;
  return true;
}

static float clampFloat(float value, float minimum, float maximum) {
  return min(max(value, minimum), maximum);
}

static uint32_t mix32(uint32_t value) {
  value ^= value >> 16;
  value *= 0x7feb352dU;
  value ^= value >> 15;
  value *= 0x846ca68bU;
  value ^= value >> 16;
  return value;
}

static float nodeVariation() {
  uint32_t hash = 2166136261U;
  for (size_t i = 0; i < hardwareUid.length(); ++i) {
    hash ^= static_cast<uint8_t>(hardwareUid[i]);
    hash *= 16777619U;
  }
  return (static_cast<int>(hash % 2001U) - 1000) / 1000.0f;
}

static SimulationContext simulationContext() {
  SimulationContext context = {};
  context.now = time(nullptr);
  localtime_r(&context.now, &context.local);
  context.dayOfYear = context.local.tm_yday + 1;
  const int utcOffsetHours = context.local.tm_isdst > 0 ? 13 : 12;
  context.daySerial = static_cast<int>((context.now + utcOffsetHours * 3600) / 86400);
  context.localHours = context.local.tm_hour + context.local.tm_min / 60.0f + context.local.tm_sec / 3600.0f;
  context.nodeVariation = nodeVariation();

  const float gamma = 2.0f * M_PI / 365.0f *
    (context.dayOfYear - 1 + (context.localHours - 12.0f) / 24.0f);
  const float declination =
    0.006918f - 0.399912f * cosf(gamma) + 0.070257f * sinf(gamma)
    - 0.006758f * cosf(2.0f * gamma) + 0.000907f * sinf(2.0f * gamma)
    - 0.002697f * cosf(3.0f * gamma) + 0.00148f * sinf(3.0f * gamma);
  const float equationOfTime = 229.18f *
    (0.000075f + 0.001868f * cosf(gamma) - 0.032077f * sinf(gamma)
    - 0.014615f * cosf(2.0f * gamma) - 0.040849f * sinf(2.0f * gamma));
  const float latitudeRadians = NZ_SIMULATION_LATITUDE * M_PI / 180.0f;
  const float cosHourAngle = clampFloat(
    (cosf(90.833f * M_PI / 180.0f) - sinf(latitudeRadians) * sinf(declination)) /
      (cosf(latitudeRadians) * cosf(declination)),
    -1.0f,
    1.0f
  );
  const float daylightHours = 2.0f * acosf(cosHourAngle) * 180.0f / M_PI / 15.0f;
  const float utcOffset = static_cast<float>(utcOffsetHours);
  context.solarNoonHours = 12.0f + utcOffset - NZ_SIMULATION_LONGITUDE / 15.0f - equationOfTime / 60.0f;
  context.sunriseHours = context.solarNoonHours - daylightHours / 2.0f;
  context.sunsetHours = context.solarNoonHours + daylightHours / 2.0f;
  context.daylightFraction = 0.0f;
  if (context.localHours >= context.sunriseHours && context.localHours <= context.sunsetHours) {
    context.daylightFraction = sinf(
      M_PI * (context.localHours - context.sunriseHours) / daylightHours
    );
  }

  const float synopticDay = context.daySerial + context.localHours / 24.0f;
  context.cloudCover = clampFloat(
    0.32f
      + 0.20f * sinf(2.0f * M_PI * synopticDay / 3.8f + 0.7f)
      + 0.10f * sinf(2.0f * M_PI * synopticDay / 8.5f + 2.1f),
    0.05f,
    0.85f
  );
  return context;
}

static RainEvent rainEventFor(const SimulationContext& context) {
  RainEvent event = {false, 0.0f, 0.0f};

  for (int daysBack = 0; daysBack <= 3; ++daysBack) {
    const int serial = context.daySerial - daysBack;
    const uint32_t hash = mix32(static_cast<uint32_t>(serial));
    const bool rainDay = (hash % 100U) < 32U;
    if (!rainDay) continue;

    const float startHour = 3.0f + ((hash >> 8) % 1300U) / 100.0f;
    const float durationHours = 1.0f + ((hash >> 20) % 350U) / 100.0f;
    const float hourlyRate = 0.8f + ((hash >> 12) % 420U) / 100.0f;
    const float endHour = min(23.5f, startHour + durationHours);

    if (daysBack == 0 && context.localHours >= startHour && context.localHours <= endHour) {
      event.active = true;
      event.intervalMm = hourlyRate / 60.0f;
    }

    if (daysBack == 0 && context.localHours >= startHour && context.localHours <= endHour) {
      const float accumulatedMm = hourlyRate * (context.localHours - startHour);
      event.recentSoilEffect += accumulatedMm * 0.28f;
    } else {
      const bool eventHasFinished = daysBack > 0 || context.localHours > endHour;
      if (eventHasFinished) {
        const float hoursSinceEnd = max(
          0.0f,
          daysBack * 24.0f + context.localHours - endHour
        );
        const float eventTotalMm = hourlyRate * durationHours;
        event.recentSoilEffect += eventTotalMm * 0.28f * expf(-hoursSinceEnd / 42.0f);
      }
    }
  }
  return event;
}

static float airTemperatureFor(const SimulationContext& context) {
  const int month = constrain(context.local.tm_mon, 0, 11);
  const float low = MONTHLY_LOW_C[month];
  const float high = MONTHLY_HIGH_C[month];
  const float range = high - low;
  const float minHour = context.sunriseHours + 0.5f;
  const float maxHour = context.solarNoonHours + 3.0f;
  float base;

  if (context.localHours >= minHour && context.localHours <= maxHour) {
    base = low + range *
      sinf((context.localHours - minHour) / max(1.0f, maxHour - minHour) * M_PI / 2.0f);
  } else {
    const float afterMax = context.localHours > maxHour
      ? context.localHours - maxHour
      : context.localHours + 24.0f - maxHour;
    base = low + range *
      cosf(afterMax / max(1.0f, 24.0f - (maxHour - minHour)) * M_PI / 2.0f);
  }

  const float synopticDay = context.daySerial + context.localHours / 24.0f;
  const float synopticOffset = 1.2f * sinf(2.0f * M_PI * synopticDay / 6.5f + 0.4f);
  return clampFloat(
    base + synopticOffset - context.cloudCover * 1.1f + context.nodeVariation * 0.45f,
    -5.0f,
    35.0f
  );
}

static float simulatedValue(const String& key) {
  const SimulationContext context = simulationContext();
  const RainEvent rain = rainEventFor(context);
  const float day = context.daySerial + context.localHours / 24.0f;
  const float air = airTemperatureFor(context);
  const float node = context.nodeVariation;

  if (key == "soil_moisture_pct") {
    const float seasonal = 3.0f * cosf(2.0f * M_PI * (context.dayOfYear - 200.0f) / 365.0f);
    const float slowVariation =
      1.5f * sinf(2.0f * M_PI * day / 11.0f + node)
      + 0.7f * sinf(2.0f * M_PI * day / 29.0f + 1.6f);
    return clampFloat(
      27.0f + seasonal + slowVariation + rain.recentSoilEffect
        + node * 1.8f - context.daylightFraction * 0.35f,
      12.0f,
      55.0f
    );
  }

  if (key == "soil_temperature_c") {
    const int month = constrain(context.local.tm_mon, 0, 11);
    const float mean = (MONTHLY_LOW_C[month] + MONTHLY_HIGH_C[month]) / 2.0f;
    const float daily = 1.4f * cosf(
      2.0f * M_PI * (context.localHours - 16.5f) / 24.0f
    );
    return clampFloat(mean - 1.0f + daily + node * 0.25f, 2.0f, 28.0f);
  }

  if (key == "air_temperature_c") return air;

  if (key == "relative_humidity_pct") {
    const float humidity =
      88.0f - 30.0f * context.daylightFraction
      + context.cloudCover * 7.0f
      + (rain.active ? 8.0f : 0.0f)
      - (air - 15.0f) * 0.35f
      + node * 2.0f;
    return clampFloat(humidity, 35.0f, 100.0f);
  }

  if (key == "light_lux") {
    if (context.daylightFraction <= 0.0f) return 0.0f;
    const float clearSkyLux = 90000.0f * powf(context.daylightFraction, 1.20f);
    const float cloudAttenuation = 1.0f - context.cloudCover * 0.68f;
    const float nodeShade = clampFloat(0.95f + node * 0.05f, 0.88f, 1.02f);
    return clampFloat(clearSkyLux * cloudAttenuation * nodeShade, 0.0f, 90000.0f);
  }

  if (key == "barometric_pressure_hpa") {
    return clampFloat(
      1015.0f
        + 5.2f * sinf(2.0f * M_PI * day / 6.2f + 0.9f)
        + 1.6f * sinf(2.0f * M_PI * day / 13.0f),
      985.0f,
      1035.0f
    );
  }

  if (key == "leaf_wetness_pct") {
    if (rain.active) return 92.0f;
    return clampFloat(78.0f - 72.0f * context.daylightFraction + context.cloudCover * 12.0f, 4.0f, 88.0f);
  }

  if (key == "pasture_height_cm") {
    const float grazingCycleDay = fmodf(context.daySerial + (node + 1.0f) * 4.0f, 28.0f);
    return clampFloat(8.5f + grazingCycleDay * 0.17f + node * 0.5f, 6.0f, 18.0f);
  }

  if (key == "rainfall_mm") return rain.intervalMm;

  if (key == "soil_ec_ms_cm") {
    return clampFloat(
      0.75f + node * 0.06f + 0.025f * sinf(2.0f * M_PI * day / 21.0f),
      0.3f,
      1.3f
    );
  }

  if (key == "soil_ph") {
    return clampFloat(
      6.15f + node * 0.12f + 0.025f * sinf(2.0f * M_PI * day / 35.0f),
      5.5f,
      6.8f
    );
  }

  if (key == "wind_direction_deg") {
    return fmodf(
      225.0f + 38.0f * sinf(2.0f * M_PI * day / 5.2f + 0.8f) + 360.0f,
      360.0f
    );
  }

  if (key == "wind_speed_kmh") {
    return clampFloat(
      9.0f
        + 5.0f * fabsf(sinf(2.0f * M_PI * day / 3.5f + 0.5f))
        + context.cloudCover * 3.0f,
      1.0f,
      35.0f
    );
  }

  return 0.0f;
}

static bool readLiveMeasurement(const String& key, float& value) {
  if (key != "soil_moisture_pct") return false;

  // XC4604 proof-of-concept acquisition. The observed electrical span is
  // approximately raw 0 in dry air and raw 1800 immersed in water. Mapping
  // that span to 0-100 proves the physical acquisition/telemetry path only;
  // it is NOT a calibrated volumetric or agronomic soil-moisture percentage.
  uint32_t total = 0;
  for (uint8_t i = 0; i < SOIL_MOISTURE_ADC_SAMPLES; ++i) {
    total += analogRead(SOIL_MOISTURE_ADC_PIN);
    delay(4);
  }
  const float raw = total / (float)SOIL_MOISTURE_ADC_SAMPLES;
  const float span = (float)SOIL_MOISTURE_POC_RAW_WET - (float)SOIL_MOISTURE_POC_RAW_DRY;
  if (span <= 0.0f) return false;

  value = clampFloat(
    (raw - (float)SOIL_MOISTURE_POC_RAW_DRY) * 100.0f / span,
    0.0f,
    100.0f
  );

  Serial.printf(
    "XC4604 GPIO%u raw=%.1f prototype_scale=%.2f%% (uncalibrated)\n",
    SOIL_MOISTURE_ADC_PIN,
    raw,
    value
  );
  return true;
}

static bool syncClockFromFarmPi(JsonDocument& response) {
  if (!response["server_time"].is<uint64_t>()) {
    Serial.println("FarmPi contact did not include server_time; clock unchanged.");
    return false;
  }

  const uint64_t serverTime = response["server_time"].as<uint64_t>();
  if (serverTime < 1700000000ULL || serverTime > 4102444800ULL) {
    Serial.printf("FarmPi server_time rejected: %llu\n", (unsigned long long)serverTime);
    return false;
  }

  const time_t localNow = time(nullptr);
  const int64_t offset = (int64_t)serverTime - (int64_t)localNow;
  if (localNow >= 1700000000 && offset >= -5 && offset <= 5) return true;

  struct timeval tv;
  tv.tv_sec = (time_t)serverTime;
  tv.tv_usec = 0;
  if (settimeofday(&tv, nullptr) != 0) {
    Serial.printf("Could not set clock from FarmPi server_time=%llu\n", (unsigned long long)serverTime);
    return false;
  }

  Serial.printf("FarmPi time synchronised: %llu (offset=%llds)\n",
    (unsigned long long)serverTime, (long long)offset);
  return true;
}

static void contactFarmPi() {
  JsonDocument request, response; auth(request);
  request["firmware_version"] = FIRMWARE_VERSION;
  request["board_profile"] = BOARD_PROFILE;
  JsonArray capabilities = request["capabilities"].to<JsonArray>();
  for (size_t i = 0; i < CONFIGURABLE_COUNT; ++i) capabilities.add(CONFIGURABLE_MEASUREMENTS[i]);
  JsonArray live = request["live_capabilities"].to<JsonArray>();
  for (size_t i = 0; i < LIVE_COUNT; ++i) live.add(LIVE_MEASUREMENTS[i]);
  if (appliedHash.length()) request["applied_fingerprint"] = appliedHash;
  if (!post("/api/nodes/contact", request, response)) return;

  syncClockFromFarmPi(response);
  locationEpoch = response["location_epoch"].as<uint64_t>();
  if (!response["registered"].as<bool>()) {
    Serial.println("Awaiting registration; all sensors remain off.");
    return;
  }

  String assigned = response["node_uid"].as<String>();
  String desired = response["desired_fingerprint"].as<String>();
  if (nodeUid.length() && nodeUid != assigned) {
    Serial.println("Assigned identity mismatch; retaining configuration.");
    return;
  }
  if (desired == appliedHash) {
    Serial.println("Configuration IN SYNC");
    return;
  }

  JsonDocument pull, latest; auth(pull);
  if (!post("/api/nodes/configuration", pull, latest)) return;
  String text = latest["canonical"].as<String>(), hash = latest["fingerprint"].as<String>();
  JsonDocument parsed;
  if (!validate(text, hash, assigned, parsed)) {
    acknowledge(hash, "Invalid or unsupported configuration");
    return;
  }
  if (!persistAndApply(text, hash, assigned, parsed)) {
    acknowledge(hash, "NVS persistence failed");
    return;
  }
  acknowledge(hash);
  Serial.printf("Applied config %.8s\n", appliedHash.c_str());
}

static void sendTelemetry() {
  if (!nodeUid.length() || !appliedHash.length() || !activeConfig["modes"].is<JsonObject>()) return;
  time_t now = time(nullptr);
  if (now < 1700000000) {
    Serial.println("Clock not ready; telemetry deferred.");
    return;
  }

  JsonDocument request, response;
  auth(request);
  request["sensor"] = nodeUid;
  request["applied_fingerprint"] = appliedHash;
  request["location_epoch"] = locationEpoch;
  request["protocol_version"] = 1;
  request["clock_valid"] = true;
  request["device_time_unix"] = (uint64_t)now;

  bool anyValue = false;
  bool anySimulated = false;
  JsonObject modes = activeConfig["modes"].as<JsonObject>();
  for (size_t i = 0; i < CONFIGURABLE_COUNT; ++i) {
    const String key = CONFIGURABLE_MEASUREMENTS[i];
    const String mode = modes[key].as<String>();
    if (mode == "SIMULATED") {
      request[key] = simulatedValue(key);
      anyValue = true;
      anySimulated = true;
    } else if (mode == "LIVE") {
      float value = 0.0f;
      if (readLiveMeasurement(key, value)) {
        request[key] = value;
        anyValue = true;
      }
    }
  }

  if (!anyValue) return;
  sampleSeq += 1;
  if (nvs.putULong64("sample_seq", sampleSeq) != sizeof(uint64_t)) {
    sampleSeq -= 1;
    Serial.println("Could not persist sample sequence; telemetry deferred.");
    return;
  }
  request["sample_seq"] = sampleSeq;
  request["simulated"] = anySimulated;

  if (post("/api/ingest", request, response)) {
    Serial.printf("Telemetry accepted seq=%llu simulated=%s\n",
      (unsigned long long)sampleSeq, anySimulated ? "true" : "false");
  } else {
    Serial.printf("Telemetry send failed seq=%llu; retry uses a new sequence after next interval.\n",
      (unsigned long long)sampleSeq);
  }
}

void setup() {
  Serial.begin(115200);

  pinMode(SOIL_MOISTURE_ADC_PIN, INPUT);
  analogReadResolution(12);
  analogSetPinAttenuation(SOIL_MOISTURE_ADC_PIN, ADC_11db);
  Serial.printf(
    "XC4604 proof-of-concept input: GPIO%u, raw dry=%u, raw wet=%u; scaling is uncalibrated.\n",
    SOIL_MOISTURE_ADC_PIN,
    SOIL_MOISTURE_POC_RAW_DRY,
    SOIL_MOISTURE_POC_RAW_WET
  );

  setenv("TZ", FARM_TIMEZONE, 1);
  tzset();
  uint8_t mac[6]; if (esp_efuse_mac_get_default(mac) != ESP_OK) return;
  hardwareUid = hexBytes(mac, 6);
  WiFi.mode(WIFI_STA);
  storageReady = nvs.begin("farmpi", false);
  if (!storageReady) return;

  deviceKey = nvs.getString("device_key", "");
  if (!deviceKey.length()) {
    uint8_t secret[32]; esp_fill_random(secret, sizeof(secret)); deviceKey = hexBytes(secret, sizeof(secret));
    if (nvs.putString("device_key", deviceKey) != deviceKey.length()) { storageReady = false; return; }
  }
  sampleSeq = nvs.getULong64("sample_seq", 0);
  restore();

  WiFi.mode(WIFI_STA);
  WiFi.setHostname(("farmpi-" + hardwareUid).c_str());
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.println("Clock will be synchronised from FarmPi contact.");
  lastContact = millis() - CONTACT_INTERVAL_MS;
  lastTelemetry = millis();
  Serial.printf("Hardware %s; saved config %.8s; sample seq=%llu\n",
    hardwareUid.c_str(), appliedHash.c_str(), (unsigned long long)sampleSeq);
}

void loop() {
  if (storageReady && WiFi.status() == WL_CONNECTED) {
    if (millis() - lastContact >= CONTACT_INTERVAL_MS) {
      lastContact = millis();
      contactFarmPi();
    }
    if (millis() - lastTelemetry >= TELEMETRY_INTERVAL_MS) {
      lastTelemetry = millis();
      sendTelemetry();
    }
  }
  delay(20);
}
