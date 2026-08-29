package nz.farmpi.client

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.material3.Card
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Rect
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import kotlin.math.max
import kotlin.math.min

internal data class GraphPoint(val label: String, val value: Double)
internal data class GraphSeries(val name: String, val points: List<GraphPoint>)

private data class GraphMode(val key: String, val label: String)

@Composable
internal fun EnhancedChartCard(
    title: String,
    unit: String,
    period: String,
    provenance: String,
    baseType: String,
    series: List<GraphSeries>,
) {
    val allPoints = series.flatMap { it.points }
    if (allPoints.isEmpty()) return

    val isComparison = baseType.equals("bar", ignoreCase = true)
    val isLight = title.contains("light", ignoreCase = true) || unit.equals("lux", ignoreCase = true)
    val modes = if (isComparison) {
        listOf(GraphMode("bars", "Bars"), GraphMode("dots", "Dots"))
    } else {
        listOf(
            GraphMode("line", "Line"),
            GraphMode("area", if (isLight) "Day profile" else "Area"),
            GraphMode("bars", "Bars"),
            GraphMode("dots", "Dots"),
        )
    }
    val initialMode = if (isComparison) "bars" else if (isLight) "area" else "line"
    var selectedMode by remember(title, period, baseType) { mutableStateOf(initialMode) }
    if (modes.none { it.key == selectedMode }) selectedMode = modes.first().key

    val values = allPoints.map { it.value }
    val minimum = values.minOrNull() ?: 0.0
    val maximum = values.maxOrNull() ?: 0.0
    val latest = series.firstOrNull()?.points?.lastOrNull()?.value

    Card(Modifier.fillMaxWidth().padding(top = 12.dp)) {
        Column(Modifier.padding(16.dp)) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Column(Modifier.weight(1f)) {
                    Text(
                        text = if (isLight) "☀  $title" else title,
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold,
                    )
                    Text(
                        "$period • $provenance",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }

            Spacer(Modifier.height(10.dp))
            Row(
                Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                modes.forEach { mode ->
                    FilterChip(
                        selected = selectedMode == mode.key,
                        onClick = { selectedMode = mode.key },
                        label = { Text(mode.label) },
                    )
                }
            }

            Spacer(Modifier.height(8.dp))
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                StatLabel("Low", minimum, unit)
                latest?.let { StatLabel("Latest", it, unit) }
                StatLabel("High", maximum, unit)
            }

            Spacer(Modifier.height(10.dp))
            ChartCanvas(selectedMode, series)

            val firstLabel = series.firstOrNull()?.points?.firstOrNull()?.label?.let(::shortGraphLabel).orEmpty()
            val lastLabel = series.firstOrNull()?.points?.lastOrNull()?.label?.let(::shortGraphLabel).orEmpty()
            if (!isComparison && firstLabel.isNotBlank() && lastLabel.isNotBlank()) {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text(firstLabel, style = MaterialTheme.typography.labelSmall)
                    Text(lastLabel, style = MaterialTheme.typography.labelSmall)
                }
            }

            if (series.size > 1) {
                Spacer(Modifier.height(8.dp))
                Text("Series", style = MaterialTheme.typography.labelMedium, fontWeight = FontWeight.Bold)
                Text(
                    series.take(8).joinToString(" • ") { it.name },
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                if (series.size > 8) {
                    Text("+ ${series.size - 8} more", style = MaterialTheme.typography.bodySmall)
                }
            } else if (isComparison) {
                val labels = series.first().points.map { shortGraphLabel(it.label) }
                Text(
                    labels.take(8).joinToString(" • "),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                if (labels.size > 8) Text("+ ${labels.size - 8} more paddocks", style = MaterialTheme.typography.bodySmall)
            }

            Text(
                "Display style changes only the visual presentation; values remain the same verified dataset.",
                modifier = Modifier.padding(top = 8.dp),
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

@Composable
private fun StatLabel(label: String, value: Double, unit: String) {
    Column {
        Text(label, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Text(formatGraphValue(value, unit), style = MaterialTheme.typography.labelLarge, fontWeight = FontWeight.SemiBold)
    }
}

@Composable
private fun ChartCanvas(mode: String, series: List<GraphSeries>) {
    val primary = MaterialTheme.colorScheme.primary
    val secondary = MaterialTheme.colorScheme.secondary
    val tertiary = MaterialTheme.colorScheme.tertiary
    val grid = MaterialTheme.colorScheme.outlineVariant
    val palette = listOf(primary, secondary, tertiary, MaterialTheme.colorScheme.error)
    val allValues = series.flatMap { it.points }.map { it.value }
    if (allValues.isEmpty()) return

    val rawMin = allValues.minOrNull() ?: 0.0
    val rawMax = allValues.maxOrNull() ?: 1.0
    val spread = (rawMax - rawMin).takeIf { it > 0.0000001 } ?: max(kotlin.math.abs(rawMax), 1.0)
    val lineLower = rawMin - spread * 0.08
    val lineUpper = rawMax + spread * 0.08
    val barLower = min(0.0, rawMin)
    val barUpper = max(0.0, rawMax).let { if (it == barLower) barLower + 1.0 else it }

    Canvas(Modifier.fillMaxWidth().height(220.dp)) {
        val left = 8.dp.toPx()
        val right = size.width - 8.dp.toPx()
        val top = 8.dp.toPx()
        val bottom = size.height - 8.dp.toPx()
        val width = max(1f, right - left)
        val height = max(1f, bottom - top)

        repeat(5) { index ->
            val y = top + height * index / 4f
            drawLine(grid.copy(alpha = 0.45f), Offset(left, y), Offset(right, y), strokeWidth = 1.dp.toPx())
        }

        fun xFor(index: Int, count: Int): Float = if (count <= 1) left + width / 2f else left + width * index / (count - 1f)
        fun yFor(value: Double, lower: Double, upper: Double): Float {
            val range = (upper - lower).takeIf { it > 0.0000001 } ?: 1.0
            val normalised = ((value - lower) / range).toFloat().coerceIn(0f, 1f)
            return bottom - height * normalised
        }

        when (mode) {
            "bars" -> {
                val flattened = if (series.size == 1) series.first().points else series.flatMap { item -> item.points }
                val count = flattened.size.coerceAtLeast(1)
                val slot = width / count
                val barWidth = (slot * 0.68f).coerceAtLeast(2.dp.toPx())
                val zeroY = yFor(0.0, barLower, barUpper)
                flattened.forEachIndexed { index, point ->
                    val centre = left + slot * (index + 0.5f)
                    val valueY = yFor(point.value, barLower, barUpper)
                    val rectTop = min(valueY, zeroY)
                    val rectHeight = max(2.dp.toPx(), kotlin.math.abs(zeroY - valueY))
                    drawRoundRect(
                        color = palette[index % palette.size],
                        topLeft = Offset(centre - barWidth / 2f, rectTop),
                        size = Size(barWidth, rectHeight),
                        cornerRadius = androidx.compose.ui.geometry.CornerRadius(5.dp.toPx(), 5.dp.toPx()),
                    )
                }
            }

            "dots" -> {
                series.forEachIndexed { seriesIndex, item ->
                    val colour = palette[seriesIndex % palette.size]
                    item.points.forEachIndexed { index, point ->
                        drawCircle(colour, radius = 4.dp.toPx(), center = Offset(xFor(index, item.points.size), yFor(point.value, lineLower, lineUpper)))
                    }
                }
            }

            else -> {
                series.forEachIndexed { seriesIndex, item ->
                    if (item.points.isEmpty()) return@forEachIndexed
                    val colour = palette[seriesIndex % palette.size]
                    val path = Path()
                    item.points.forEachIndexed { index, point ->
                        val x = xFor(index, item.points.size)
                        val y = yFor(point.value, lineLower, lineUpper)
                        if (index == 0) path.moveTo(x, y) else path.lineTo(x, y)
                    }
                    if (mode == "area") {
                        val area = Path().apply {
                            val firstY = yFor(item.points.first().value, lineLower, lineUpper)
                            moveTo(left, bottom)
                            lineTo(left, firstY)
                            item.points.forEachIndexed { index, point ->
                                lineTo(xFor(index, item.points.size), yFor(point.value, lineLower, lineUpper))
                            }
                            lineTo(right, bottom)
                            close()
                        }
                        drawPath(area, colour.copy(alpha = 0.18f))
                    }
                    drawPath(path, colour, style = Stroke(width = 3.dp.toPx()))
                    item.points.forEachIndexed { index, point ->
                        if (item.points.size <= 24 || index == 0 || index == item.points.lastIndex) {
                            drawCircle(colour, radius = 3.dp.toPx(), center = Offset(xFor(index, item.points.size), yFor(point.value, lineLower, lineUpper)))
                        }
                    }
                }
            }
        }
    }
}

private fun shortGraphLabel(value: String): String {
    val trimmed = value.trim()
    val t = trimmed.indexOf('T')
    if (t >= 0 && trimmed.length >= t + 6) return trimmed.substring(t + 1, t + 6)
    return trimmed.take(14)
}

private fun formatGraphValue(value: Double, unit: String): String {
    val digits = when {
        kotlin.math.abs(value) >= 1000 -> 0
        kotlin.math.abs(value) >= 100 -> 1
        else -> 2
    }
    return "%.${digits}f%s".format(value, if (unit.isBlank()) "" else " $unit")
}
