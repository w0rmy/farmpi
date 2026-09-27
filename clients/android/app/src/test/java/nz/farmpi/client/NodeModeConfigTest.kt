package nz.farmpi.client

import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

class NodeModeConfigTest {
    private fun sensors() = JSONArray()
        .put(JSONObject()
            .put("key", "soil_moisture_pct")
            .put("supported", true)
            .put("live_supported", false)
            .put("mode", "OFF"))
        .put(JSONObject()
            .put("key", "air_temperature_c")
            .put("supported", true)
            .put("live_supported", true)
            .put("mode", "SIMULATED"))
        .put(JSONObject()
            .put("key", "rainfall_mm")
            .put("supported", false)
            .put("mode", "OFF"))

    @Test
    fun supportedModesInitialiseFromServerAndExcludeUnsupportedMeasurements() {
        assertEquals(
            mapOf(
                "soil_moisture_pct" to "OFF",
                "air_temperature_c" to "SIMULATED",
            ),
            supportedNodeModes(sensors()),
        )
    }

    @Test
    fun liveIsSelectableOnlyWhenFirmwareAdvertisesLiveDriver() {
        val items = sensors()
        val soil = items.getJSONObject(0)
        val air = items.getJSONObject(1)
        val unsupported = items.getJSONObject(2)

        assertTrue(canSelectNodeMode(soil, "OFF"))
        assertTrue(canSelectNodeMode(soil, "SIMULATED"))
        assertFalse(canSelectNodeMode(soil, "LIVE"))
        assertTrue(canSelectNodeMode(air, "LIVE"))
        assertFalse(canSelectNodeMode(unsupported, "OFF"))
    }

    @Test
    fun savePayloadContainsCompleteSelectedModeMap() {
        val payload = nodeModesJson(
            mapOf(
                "soil_moisture_pct" to "SIMULATED",
                "air_temperature_c" to "LIVE",
            )
        )

        assertEquals(2, payload.length())
        assertEquals("LIVE", payload.getString("air_temperature_c"))
        assertEquals("SIMULATED", payload.getString("soil_moisture_pct"))
    }
}
