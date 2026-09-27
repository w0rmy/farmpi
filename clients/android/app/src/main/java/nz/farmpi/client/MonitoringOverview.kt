package nz.farmpi.client

import org.json.JSONArray
import org.json.JSONObject

internal data class OverviewMeasurement(
    val key: String,
    val label: String,
    val unit: String,
    val value: Double,
    val displayValue: String,
    val sourceMode: String?,
    val ageSeconds: Int?,
    val reportingLocations: Int?,
)

internal data class OverviewLocation(
    val id: Int,
    val name: String,
    val activeSensorCount: Int,
    val reporting: Boolean,
    val ageSeconds: Int?,
    val containsSimulated: Boolean,
    val measurements: List<OverviewMeasurement>,
)

internal data class MonitoringOverview(
    val locationCount: Int,
    val reportingLocationCount: Int,
    val farmMeasurements: List<OverviewMeasurement>,
    val locations: List<OverviewLocation>,
    val featuredChart: ChartPayload?,
)

private fun JSONArray.measurements(): List<OverviewMeasurement> =
    (0 until length()).map { index ->
        getJSONObject(index).let { item ->
            OverviewMeasurement(
                key = item.getString("key"),
                label = item.getString("label"),
                unit = item.optString("unit"),
                value = item.getDouble("value"),
                displayValue = item.getString("display_value"),
                sourceMode = item.optString("source_mode").takeIf { it.isNotBlank() && !it.equals("null", true) },
                ageSeconds = if (item.isNull("age_seconds")) null else item.optInt("age_seconds"),
                reportingLocations = if (item.isNull("reporting_locations")) null else item.optInt("reporting_locations"),
            )
        }
    }

private fun JSONObject.overviewChart(): ChartPayload? {
    if (length() == 0) return null
    val entries = optJSONArray("series") ?: return null
    val series = (0 until entries.length()).map { index ->
        val item = entries.getJSONObject(index)
        val points = item.optJSONArray("data") ?: JSONArray()
        item.optString("name") to (0 until points.length()).map { pointIndex ->
            points.getJSONObject(pointIndex).let { point ->
                ChartPoint(point.optString("x"), point.optDouble("y"))
            }
        }
    }
    if (series.all { it.second.isEmpty() }) return null
    return ChartPayload(
        type = optString("type"),
        title = optString("title"),
        unit = optString("unit"),
        period = optString("source_period"),
        provenance = optString("provenance"),
        series = series,
    )
}

internal fun JSONObject.monitoringOverview(): MonitoringOverview {
    val locationArray = optJSONArray("locations") ?: JSONArray()
    val locations = (0 until locationArray.length()).map { index ->
        locationArray.getJSONObject(index).let { item ->
            OverviewLocation(
                id = item.getInt("id"),
                name = item.getString("name"),
                activeSensorCount = item.optInt("active_sensor_count"),
                reporting = item.optBoolean("reporting"),
                ageSeconds = if (item.isNull("age_seconds")) null else item.optInt("age_seconds"),
                containsSimulated = item.optBoolean("contains_simulated"),
                measurements = (item.optJSONArray("measurements") ?: JSONArray()).measurements(),
            )
        }
    }
    return MonitoringOverview(
        locationCount = optInt("location_count"),
        reportingLocationCount = optInt("reporting_location_count"),
        farmMeasurements = (optJSONArray("farm_measurements") ?: JSONArray()).measurements(),
        locations = locations,
        featuredChart = optJSONObject("featured_chart")?.overviewChart(),
    )
}

internal fun ageLabel(ageSeconds: Int?): String = when {
    ageSeconds == null -> "No current reading"
    ageSeconds < 60 -> "Updated just now"
    ageSeconds < 3600 -> {
        val minutes = ageSeconds / 60
        "Updated $minutes min ago"
    }
    ageSeconds < 86_400 -> {
        val hours = ageSeconds / 3600
        "Updated $hours h ago"
    }
    else -> {
        val days = ageSeconds / 86_400
        "Updated $days d ago"
    }
}
