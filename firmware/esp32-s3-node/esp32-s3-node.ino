#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <Preferences.h>
#include <ArduinoJson.h>
#include <esp_mac.h>
#include <esp_system.h>
#include <mbedtls/sha256.h>
#include <time.h>
#include "config.h"
#include "board_profile.h"

#if !CONFIG_IDF_TARGET_ESP32S3
#error "Select the verified ESP32-S3 board target"
#endif

static Preferences nvs;
static String hardwareUid, deviceKey, nodeUid, appliedHash, appliedCanonical;
static JsonDocument activeConfig;
static uint32_t lastContact = 0;
static uint32_t lastSample = 0;
static uint64_t locationEpoch = 0;
static bool storageReady = false;

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

static bool validMode(const String& key, const String& mode) {
  if (mode == "OFF" || mode == "SIMULATED") return true;
  return mode == "LIVE" && supportsLive(key);
}

static bool validate(const String& text, const String& hash, const String& uid, JsonDocument& parsed) {
  if (text.length() > 4096 || hash.length() != 64 || sha256(text) != hash || deserializeJson(parsed, text)) return false;
  if (!parsed.is<JsonObject>() || parsed.size() != 3 || !parsed["schema_version"].is<int>() ||
      parsed["schema_version"].as<int>() != 2 || parsed["node_uid"].as<String>() != uid ||
      !parsed["modes"].is<JsonObject>()) return false;

  JsonObject parsedModes = parsed["modes"].as<JsonObject>();
  if (parsedModes.size() != CONFIGURABLE_COUNT) return false;
  for (size_t i = 0; i < CONFIGURABLE_COUNT; ++i) {
    const char* key = CONFIGURABLE_MEASUREMENTS[i];
    if (!parsedModes[key].is<const char*>()) return false;
    String mode = parsedModes[key].as<String>();
    if (!validMode(key, mode)) return false;
  }

  // Rebuild canonical JSON in the same alphabetical key order as the server.
  JsonDocument canonical;
  JsonObject modes = canonical["modes"].to<JsonObject>();
  for (size_t i = 0; i < CONFIGURABLE_COUNT; ++i) {
    const char* key = CONFIGURABLE_MEASUREMENTS[i];
    modes[key] = parsedModes[key];
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
    Serial.printf("FarmPi HTTP %d on %s\n", status, path);
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
  JsonDocument envelope;
  envelope["canonical"] = text;
  envelope["fingerprint"] = hash;
  envelope["node_uid"] = uid;
  String blob; serializeJson(envelope, blob);
  if (nvs.putString(key, blob) != blob.length() || nvs.getString(key, "") != blob) return false;
  if (nvs.putUChar("slot", candidate) != 1) return false;
  activeConfig = parsed; appliedCanonical = text; appliedHash = hash; nodeUid = uid;
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
  locationEpoch = response["location_epoch"] | 0ULL;
  if (!response["registered"].as<bool>()) {
    Serial.println("Awaiting registration; all measurements OFF.");
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
  String text = latest["canonical"].as<String>();
  String hash = latest["fingerprint"].as<String>();
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

static float simulatedValue(const String& key) {
  int step = static_cast<int>((millis() / 10000UL) % 21UL) - 10;
  if (key == "air_temperature_c") return 18.0f + step * 0.10f;
  if (key == "barometric_pressure_hpa") return 1013.0f + step * 0.20f;
  if (key == "leaf_wetness_pct") return 25.0f + step;
  if (key == "light_lux") return 15000.0f + step * 500.0f;
  if (key == "pasture_height_cm") return 12.0f + step * 0.10f;
  if (key == "rainfall_mm") return step > 7 ? 0.2f : 0.0f;
  if (key == "relative_humidity_pct") return 65.0f - step * 0.50f;
  if (key == "soil_ec_ms_cm") return 0.70f + step * 0.01f;
  if (key == "soil_moisture_pct") return 30.0f + step * 0.50f;
  if (key == "soil_ph") return 6.30f + step * 0.01f;
  if (key == "soil_temperature_c") return 15.0f + step * 0.10f;
  if (key == "wind_direction_deg") return 220.0f + step * 3.0f;
  if (key == "wind_speed_kmh") return 8.0f + step * 0.20f;
  return 0.0f;
}

static bool readLiveMeasurement(const String& key, float& value) {
  (void)key;
  (void)value;
  // No physical driver is claimed in this firmware revision.
  // Add a driver here and advertise the key in LIVE_MEASUREMENTS together.
  return false;
}

static uint64_t nextSequence() {
  uint64_t seq = nvs.getULong64("sample_seq", 0) + 1;
  if (nvs.putULong64("sample_seq", seq) != sizeof(uint64_t)) return 0;
  return seq;
}

static bool sendTelemetry(bool simulated) {
  if (!nodeUid.length() || !appliedHash.length() || !activeConfig["modes"].is<JsonObject>()) return false;
  const char* wanted = simulated ? "SIMULATED" : "LIVE";
  JsonObject modes = activeConfig["modes"].as<JsonObject>();

  JsonDocument request, response; auth(request);
  request["sensor"] = nodeUid;
  request["applied_fingerprint"] = appliedHash;
  request["location_epoch"] = locationEpoch;
  request["simulated"] = simulated;
  request["protocol_version"] = 1;

  time_t now = time(nullptr);
  if (now < 1700000000) return false;
  request["clock_valid"] = true;
  request["device_time_unix"] = static_cast<uint64_t>(now);

  bool any = false;
  for (size_t i = 0; i < CONFIGURABLE_COUNT; ++i) {
    String key = CONFIGURABLE_MEASUREMENTS[i];
    if (modes[key].as<String>() != wanted) continue;
    float value = 0.0f;
    if (simulated) {
      value = simulatedValue(key);
    } else if (!readLiveMeasurement(key, value)) {
      Serial.printf("LIVE driver unavailable for %s\n", key.c_str());
      continue;
    }
    request[key] = value;
    any = true;
  }
  if (!any) return false;

  uint64_t seq = nextSequence();
  if (!seq) return false;
  request["sample_seq"] = seq;
  if (!post("/api/ingest", request, response)) return false;
  Serial.printf("Sent %s telemetry sample %llu\n", wanted, static_cast<unsigned long long>(seq));
  return true;
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
    uint8_t secret[32];
    esp_fill_random(secret, sizeof(secret));
    deviceKey = hexBytes(secret, sizeof(secret));
    if (nvs.putString("device_key", deviceKey) != deviceKey.length()) {
      storageReady = false;
      return;
    }
  }

  restore();
  WiFi.mode(WIFI_STA);
  WiFi.setHostname(("farmpi-" + hardwareUid).c_str());
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  configTime(0, 0, "farmpi.local");

  lastContact = millis() - 15000UL;
  lastSample = millis();
  Serial.printf("Hardware %s; saved config %.8s\n", hardwareUid.c_str(), appliedHash.c_str());
}

void loop() {
  if (storageReady && WiFi.status() == WL_CONNECTED) {
    if (millis() - lastContact >= 15000UL) {
      lastContact = millis();
      contactFarmPi();
    }
    if (millis() - lastSample >= 60000UL) {
      lastSample = millis();
      // Split source modes into separate sparse observations so the existing
      // per-reading simulated flag remains exact even on a mixed-mode node.
      sendTelemetry(true);
      sendTelemetry(false);
    }
  }
  delay(20);
}
