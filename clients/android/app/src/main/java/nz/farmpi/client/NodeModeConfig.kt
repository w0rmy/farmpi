package nz.farmpi.client

import org.json.JSONArray
import org.json.JSONObject

internal fun supportedNodeModes(sensors: JSONArray): Map<String, String> =
    (0 until sensors.length())
        .map { sensors.getJSONObject(it) }
        .filter { it.optBoolean("supported", false) }
        .associate { item -> item.getString("key") to item.optString("mode", "OFF") }

internal fun canSelectNodeMode(sensor: JSONObject, mode: String): Boolean {
    if (!sensor.optBoolean("supported", false)) return false
    return mode != "LIVE" || sensor.optBoolean("live_supported", false)
}

internal fun nodeModesJson(modes: Map<String, String>): JSONObject =
    JSONObject().also { output ->
        modes.toSortedMap().forEach { (key, value) -> output.put(key, value) }
    }
