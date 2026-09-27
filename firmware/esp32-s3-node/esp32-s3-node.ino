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

static float simulatedValue(const String& key) {
  const double phase = (double)(millis() % 3600000UL) / 3600000.0 * 2.0 * M_PI;
  const double nodeOffset = hardwareUid.length() ? (hardwareUid[hardwareUid.length() - 1] % 7) * 0.35 : 0.0;
  if (key == "soil_moisture_pct") return 27.0f + 5.0f * sin(phase + nodeOffset);
  if (key == "soil_temperature_c") return 14.5f + 2.5f * sin(phase - 0.4 + nodeOffset);
  if (key == "air_temperature_c") return 18.0f + 4.0f * sin(phase + nodeOffset);
  if (key == "relative_humidity_pct") return 68.0f - 8.0f * sin(phase + nodeOffset);
  if (key == "light_lux") return max(0.0f, 18000.0f + 15000.0f * (float)sin(phase));
  if (key == "barometric_pressure_hpa") return 1014.0f + 2.0f * sin(phase / 3.0 + nodeOffset);
  if (key == "leaf_wetness_pct") return 30.0f + 10.0f * sin(phase);
  if (key == "pasture_height_cm") return 12.0f + 2.0f * sin(phase);
  if (key == "rainfall_mm") return max(0.0f, 1.0f + (float)sin(phase));
  if (key == "soil_ec_ms_cm") return 1.0f + 0.2f * sin(phase);
  if (key == "soil_ph") return 6.2f + 0.2f * sin(phase);
  if (key == "wind_direction_deg") return 180.0f + 90.0f * sin(phase);
  if (key == "wind_speed_kmh") return 10.0f + 5.0f * sin(phase);
  return 0.0f;
}

static bool readLiveMeasurement(const String& key, float& value) {
  // Physical drivers are added one measurement at a time. Until a driver is
  // fitted and advertised in LIVE_MEASUREMENTS, LIVE cannot be selected.
  (void)key; (void)value;
  return false;
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
