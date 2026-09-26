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

static bool validate(const String& text, const String& hash, const String& uid, JsonDocument& parsed) {
  if (text.length() > 2048 || hash.length() != 64 || sha256(text) != hash || deserializeJson(parsed, text)) return false;
  if (!parsed.is<JsonObject>() || parsed.size() != 3 || !parsed["schema_version"].is<int>() || parsed["schema_version"].as<int>() != 1 || parsed["node_uid"].as<String>() != uid || !parsed["enabled"].is<JsonArray>()) return false;
  String previous;
  for (JsonVariant value : parsed["enabled"].as<JsonArray>()) {
    if (!value.is<const char*>()) return false;
    String key = value.as<String>();
    if (!supports(key) || (previous.length() && key.compareTo(previous) <= 0)) return false;
    previous = key;
  }
  // Reconstruct canonical bytes to reject whitespace/order/extra-field tricks.
  JsonDocument canonical;
  canonical["enabled"] = parsed["enabled"];
  canonical["node_uid"] = uid;
  canonical["schema_version"] = 1;
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
  if (status < 200 || status >= 300 || http.getSize() > 8192) { Serial.printf("FarmPi HTTP %d\n", status); http.end(); return false; }
  String returned = http.getString(); http.end();
  return returned.length() <= 8192 && !deserializeJson(response, returned);
}

static void acknowledge(const String& hash, const char* error = nullptr) {
  JsonDocument request, response; auth(request); request["fingerprint"] = hash;
  if (error) request["error"] = error; else request["config"] = activeConfig;
  // Lost acknowledgements are repaired by the next contact's applied hash.
  post("/api/nodes/ack", request, response);
}

static bool restore() {
  // Each slot is one complete NVS string, containing identity, canonical bytes
  // and hash. Selector is updated only after candidate read-back validation.
  const uint8_t selected = nvs.getUChar("slot", 0);
  for (int attempt = 0; attempt < 2; ++attempt) {
    String blob = nvs.getString((selected ^ attempt) ? "config1" : "config0", "");
    JsonDocument envelope, parsed;
    if (deserializeJson(envelope, blob)) continue;
    String text = envelope["canonical"].as<String>(), hash = envelope["fingerprint"].as<String>(), uid = envelope["node_uid"].as<String>();
    if (!uid.startsWith("node-") || !validate(text, hash, uid, parsed)) continue;
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
  // In this bring-up profile application is only the validated enabled set;
  // there is no hardware driver whose initialisation can fail.
  if (nvs.putUChar("slot", candidate) != 1) return false;
  activeConfig = parsed; appliedCanonical = text; appliedHash = hash; nodeUid = uid;
  return true;
}

static void contactFarmPi() {
  JsonDocument request, response; auth(request);
  request["firmware_version"] = FIRMWARE_VERSION; request["board_profile"] = BOARD_PROFILE;
  JsonArray capabilities = request["capabilities"].to<JsonArray>();
  for (size_t i = 0; i < CONFIGURABLE_COUNT; ++i) capabilities.add(CONFIGURABLE_MEASUREMENTS[i]);
  if (appliedHash.length()) request["applied_fingerprint"] = appliedHash;
  if (!post("/api/nodes/contact", request, response)) return;
  if (!response["registered"].as<bool>()) { Serial.println("Awaiting registration; no sensors running."); return; }
  String assigned = response["node_uid"].as<String>();
  String desired = response["desired_fingerprint"].as<String>();
  if (nodeUid.length() && nodeUid != assigned) { Serial.println("Assigned identity mismatch; retaining configuration."); return; }
  if (desired == appliedHash) { Serial.println("Configuration IN SYNC"); return; }
  JsonDocument pull, latest; auth(pull);
  if (!post("/api/nodes/configuration", pull, latest)) return;
  String text = latest["canonical"].as<String>(), hash = latest["fingerprint"].as<String>();
  JsonDocument parsed;
  if (!validate(text, hash, assigned, parsed)) { acknowledge(hash, "Invalid or unsupported configuration"); return; }
  if (!persistAndApply(text, hash, assigned, parsed)) { acknowledge(hash, "NVS persistence failed"); return; }
  acknowledge(hash);
  Serial.printf("Applied config %.8s; enabled sensors have no probe driver yet.\n", appliedHash.c_str());
}

void setup() {
  Serial.begin(115200);
  uint8_t mac[6]; if (esp_efuse_mac_get_default(mac) != ESP_OK) return;
  hardwareUid = hexBytes(mac, 6);
  WiFi.mode(WIFI_STA); // Enable RF entropy before generating the device secret.
  storageReady = nvs.begin("farmpi", false);
  if (!storageReady) return;
  deviceKey = nvs.getString("device_key", "");
  if (!deviceKey.length()) {
    uint8_t secret[32]; esp_fill_random(secret, sizeof(secret)); deviceKey = hexBytes(secret, sizeof(secret));
    if (nvs.putString("device_key", deviceKey) != deviceKey.length()) { storageReady = false; return; }
  }
  restore(); // Last known-good state is loaded before any network operation.
  WiFi.mode(WIFI_STA); WiFi.setHostname(("farmpi-" + hardwareUid).c_str());
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  // TLS certificate validity needs a clock before the first HTTPS response.
  // Point local NTP at FarmPi; no external Internet service is required.
  configTime(0, 0, "farmpi.local");
  lastContact = millis() - 15000UL;
  Serial.printf("Hardware %s; saved config %.8s\n", hardwareUid.c_str(), appliedHash.c_str());
}

void loop() {
  if (storageReady && WiFi.status() == WL_CONNECTED && millis() - lastContact >= 15000UL) {
    lastContact = millis(); contactFarmPi();
  }
  // No analogRead, electrical assumptions, synthetic readings or placeholders.
  // The identified physical probe driver is the next development stage.
  delay(20);
}
