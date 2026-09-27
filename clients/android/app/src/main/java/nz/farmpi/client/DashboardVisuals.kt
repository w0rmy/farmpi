package nz.farmpi.client

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.Air
import androidx.compose.material.icons.rounded.LightMode
import androidx.compose.material.icons.rounded.Science
import androidx.compose.material.icons.rounded.Speed
import androidx.compose.material.icons.rounded.Thermostat
import androidx.compose.material.icons.rounded.WaterDrop
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp

private data class MeasurementVisual(val icon: ImageVector)

private fun measurementVisual(key: String): MeasurementVisual = MeasurementVisual(
    when (key) {
        "soil_moisture_pct" -> Icons.Rounded.WaterDrop
        "soil_temperature_c", "air_temperature_c" -> Icons.Rounded.Thermostat
        "relative_humidity_pct", "rainfall_mm", "leaf_wetness_pct" -> Icons.Rounded.WaterDrop
        "light_lux" -> Icons.Rounded.LightMode
        "barometric_pressure_hpa" -> Icons.Rounded.Speed
        "wind_speed_kmh" -> Icons.Rounded.Air
        "wind_direction_deg" -> Icons.Rounded.Air
        "pasture_height_cm" -> Icons.Rounded.Science
        "soil_ph", "soil_ec_ms_cm" -> Icons.Rounded.Science
        else -> Icons.Rounded.Science
    }
)

@Composable
internal fun FarmOverviewHeader(
    overview: MonitoringOverview,
    connection: String,
    checkedAt: String,
    refresh: () -> Unit,
) {
    Card(
        Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer),
    ) {
        Column(Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f)) {
                    Text(
                        "Farm overview",
                        style = MaterialTheme.typography.headlineSmall,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.onPrimaryContainer,
                    )
                    Text(
                        "${overview.locationsWithReadingsCount} of ${overview.locationCount} configured locations have stored readings",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onPrimaryContainer,
                    )
                }
                StatusChip(connection)
            }
            Text(
                "Connection checked: $checkedAt",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onPrimaryContainer,
            )
            TextButton(onClick = refresh) { Text("Refresh") }
        }
    }
}

@Composable
internal fun MeasurementGrid(
    measurements: List<OverviewMeasurement>,
    sparkline: List<ChartPoint> = emptyList(),
) {
    if (measurements.isEmpty()) {
        InfoMessageCard("No stored measurements", "FarmPi has no database readings to show yet.")
        return
    }
    measurements.chunked(2).forEach { rowItems ->
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            rowItems.forEach { measurement ->
                MeasurementTile(
                    measurement = measurement,
                    sparkline = if (measurement.key == "soil_moisture_pct") sparkline else emptyList(),
                    modifier = Modifier.weight(1f),
                )
            }
            if (rowItems.size == 1) Spacer(Modifier.weight(1f))
        }
        Spacer(Modifier.height(12.dp))
    }
}

@Composable
private fun MeasurementTile(
    measurement: OverviewMeasurement,
    sparkline: List<ChartPoint>,
    modifier: Modifier = Modifier,
) {
    val visual = measurementVisual(measurement.key)
    Card(
        modifier,
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
    ) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(7.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Surface(
                    color = MaterialTheme.colorScheme.primaryContainer,
                    shape = MaterialTheme.shapes.small,
                ) {
                    Icon(
                        visual.icon,
                        contentDescription = measurement.label,
                        tint = MaterialTheme.colorScheme.primary,
                        modifier = Modifier.padding(8.dp).size(22.dp),
                    )
                }
                Text(
                    measurement.label.replaceFirstChar { it.uppercase() },
                    style = MaterialTheme.typography.labelLarge,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            Text(
                measurement.displayValue,
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Bold,
            )
            measurement.reportingLocations?.let {
                Text(
                    "Farm average · $it location${if (it == 1) "" else "s"}",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            if (sparkline.size >= 2) MiniSparkline(sparkline)
            measurement.sourceMode?.let {
                StatusChip(it.lowercase().replaceFirstChar { c -> c.uppercase() })
            }
            Text(
                ageLabel(measurement.ageSeconds),
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

@Composable
private fun MiniSparkline(points: List<ChartPoint>) {
    val clean = points.filter { it.value.isFinite() }
    if (clean.size < 2) return
    val low = clean.minOf { it.value }
    val high = clean.maxOf { it.value }
    val span = (high - low).takeIf { it > 0.0 } ?: 1.0
    val times = clean.mapNotNull { graphTime(it.label) }
    val start = times.minOrNull()
    val end = times.maxOrNull()
    val lineColor = MaterialTheme.colorScheme.primary
    Canvas(Modifier.fillMaxWidth().height(34.dp)) {
        val path = Path()
        clean.forEachIndexed { index, point ->
            val x = size.width * graphPosition(point.label, index, clean.size, start, end)
            val y = size.height - (((point.value - low) / span).toFloat() * size.height)
            if (index == 0) path.moveTo(x, y) else path.lineTo(x, y)
        }
        drawPath(path, lineColor, style = Stroke(width = 3f))
    }
}

@Composable
internal fun LocationOverviewCard(
    location: OverviewLocation,
    open: () -> Unit,
) {
    Card(
        onClick = open,
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
    ) {
        Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f)) {
                    Text(location.name, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.SemiBold)
                    Text(
                        "${location.activeSensorCount} active node${if (location.activeSensorCount == 1) "" else "s"} · ${ageLabel(location.ageSeconds)}",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
                StatusChip(if (location.hasReading) "Data available" else "Missing")
            }
            if (location.measurements.isEmpty()) {
                Text(
                    "No stored measurements are available.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            } else {
                location.measurements.take(3).forEach { measurement ->
                    Row(
                        Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            Icon(
                                measurementVisual(measurement.key).icon,
                                contentDescription = null,
                                tint = MaterialTheme.colorScheme.primary,
                                modifier = Modifier.size(19.dp),
                            )
                            Text(measurement.label.replaceFirstChar { it.uppercase() })
                        }
                        Text(measurement.displayValue, fontWeight = FontWeight.SemiBold)
                    }
                }
                if (location.measurements.size > 3) {
                    Text(
                        "+ ${location.measurements.size - 3} more measurements",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.primary,
                    )
                }
            }
            Text("Open location", style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.primary)
        }
    }
}

@Composable
internal fun LocationMeasurementSection(location: OverviewLocation) {
    Text(location.name, style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
    Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
        StatusChip(if (location.hasReading) "Data available" else "Missing")
        if (location.containsSimulated) StatusChip("Simulated")
    }
    Text(
        "${location.activeSensorCount} active node${if (location.activeSensorCount == 1) "" else "s"} · ${ageLabel(location.ageSeconds)}",
        style = MaterialTheme.typography.bodySmall,
        color = MaterialTheme.colorScheme.onSurfaceVariant,
    )
    MeasurementGrid(location.measurements)
}

@Composable
internal fun InfoMessageCard(title: String, detail: String) {
    Card(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text(title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            Text(detail, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}
