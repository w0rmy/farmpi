package nz.farmpi.client

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import kotlin.math.max
import kotlin.math.min

internal data class GraphPoint(val label: String, val value: Double)
internal data class GraphSeries(val name: String, val points: List<GraphPoint>)

private data class GraphMode(val key: String, val label: String)
private data class GraphRange(val lower: Double, val upper: Double)

@Composable
internal fun EnhancedChartCard(
    title: String,
    unit: String,
    period: String,
    provenance: String,
    baseType: String,
    series: List<GraphSeries>,
) {
    val allPoints = series.flatMap { it.points }.filter { it.value.isFinite() }
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
    val initialMode = if (isComparison) "bars" else "line"
    var selectedMode by remember(title, period, baseType) { mutableStateOf(initialMode) }
    if (modes.none { it.key == selectedMode }) selectedMode = modes.first().key

    val values = allPoints.map { it.value }
    val minimum = values.minOrNull() ?: 0.0
    val maximum = values.maxOrNull() ?: 0.0
    val latest = series.firstOrNull()?.points?.lastOrNull { it.value.isFinite() }?.value
    val range = graphRange(selectedMode, series)
    val xLabels = graphXAxisLabels(series)
    val hasTimeAxis = series.flatMap { it.points }.any { graphTime(it.label) != null }
    val xAxisTitle = when {
        isComparison -> "Location"
        hasTimeAxis -> "Local time"
        else -> "Observation"
    }
    val yAxisTitle = if (unit.isBlank()) title else "$title ($unit)"

    Card(
        Modifier.fillMaxWidth().padding(top = 12.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
    ) {
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

            Spacer(Modifier.height(12.dp))
            Surface(
                modifier = Modifier.fillMaxWidth(),
                shape = MaterialTheme.shapes.medium,
                color = FarmPiSurfaceMuted,
                contentColor = MaterialTheme.colorScheme.onSurface,
            ) {
                Column(Modifier.padding(horizontal = 8.dp, vertical = 14.dp)) {
                    Text(
                        "Y axis · $yAxisTitle",
                        style = MaterialTheme.typography.labelMedium,
                        fontWeight = FontWeight.SemiBold,
                        color = FarmPiText,
                    )
                    Spacer(Modifier.height(8.dp))
                    Row(Modifier.fillMaxWidth()) {
                        Column(
                            modifier = Modifier.width(50.dp).height(220.dp),
                            verticalArrangement = Arrangement.SpaceBetween,
                        ) {
                            graphTicks(range).reversed().forEach { value ->
                                Text(
                                    formatAxisValue(value),
                                    style = MaterialTheme.typography.labelSmall,
                                    color = FarmPiTextMuted,
                                )
                            }
                        }
                        Spacer(Modifier.width(4.dp))
                        ChartCanvas(
                            mode = selectedMode,
                            series = series,
                            range = range,
                            modifier = Modifier.weight(1f).height(220.dp),
                        )
                    }

                    if (xLabels.isNotEmpty()) {
                        Spacer(Modifier.height(8.dp))
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(start = 54.dp)
                                .heightIn(min = if (hasTimeAxis) 54.dp else 28.dp),
                        ) {
                            xLabels.forEachIndexed { index, label ->
                                val alignment = when (index) {
                                    0 -> TextAlign.Start
                                    xLabels.lastIndex -> TextAlign.End
                                    else -> TextAlign.Center
                                }
                                if (hasTimeAxis) {
                                    val parts = label.lines()
                                    val dateLabel = parts.firstOrNull().orEmpty()
                                    val timeLabel = parts.drop(1).joinToString(" ")
                                    Column(Modifier.weight(1f)) {
                                        Text(
                                            when (index) {
                                                0 -> "Start"
                                                xLabels.lastIndex -> "End"
                                                else -> "Middle"
                                            },
                                            modifier = Modifier.fillMaxWidth(),
                                            style = MaterialTheme.typography.labelSmall,
                                            color = FarmPiTextMuted,
                                            textAlign = alignment,
                                        )
                                        Text(
                                            dateLabel,
                                            modifier = Modifier.fillMaxWidth(),
                                            style = MaterialTheme.typography.labelSmall,
                                            color = FarmPiTextMuted,
                                            textAlign = alignment,
                                        )
                                        Text(
                                            timeLabel,
                                            modifier = Modifier.fillMaxWidth(),
                                            style = MaterialTheme.typography.labelMedium,
                                            fontWeight = FontWeight.SemiBold,
                                            color = FarmPiText,
                                            textAlign = alignment,
                                        )
                                    }
                                } else {
                                    Text(
                                        label,
                                        modifier = Modifier.weight(1f),
                                        style = MaterialTheme.typography.labelSmall,
                                        color = FarmPiText,
                                        textAlign = alignment,
                                    )
                                }
                            }
                        }
                    }
                    Text(
                        "X axis · $xAxisTitle",
                        modifier = Modifier.fillMaxWidth().padding(top = 6.dp, start = 54.dp),
                        style = MaterialTheme.typography.labelMedium,
                        fontWeight = FontWeight.SemiBold,
                        textAlign = TextAlign.Center,
                        color = FarmPiText,
                    )
                }
            }

            Spacer(Modifier.height(10.dp))
            Text(
                if (isComparison)
                    "Summarised comparison · calculated by FarmPi."
                else
                    "Line view connects verified observations for readability. Sampling cadence and completeness are not implied; use Dots to inspect individual observations.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )

            if (series.size > 1) {
                Spacer(Modifier.height(8.dp))
                Text("Series", style = MaterialTheme.typography.labelMedium, fontWeight = FontWeight.Bold)
                Text(
                    series.take(8).joinToString(" • ") { it.name },
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                if (series.size > 8) {
                    Text("+ " + (series.size - 8) + " more", style = MaterialTheme.typography.bodySmall)
                }
            } else if (isComparison) {
                val labels = series.first().points.map { shortGraphLabel(it.label) }
                Text(
                    labels.take(8).joinToString(" • "),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                if (labels.size > 8) Text("+ " + (labels.size - 8) + " more locations", style = MaterialTheme.typography.bodySmall)
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
private fun ChartCanvas(
    mode: String,
    series: List<GraphSeries>,
    range: GraphRange,
    modifier: Modifier = Modifier,
) {
    val grid = FarmPiOutline
    val axis = FarmPiTextMuted
    val palette = listOf(FarmPiGreen, FarmPiBlue, FarmPiAmber, FarmPiGrey)
    val times = series.flatMap { it.points }.mapNotNull { graphTime(it.label) }
    val start = times.minOrNull()
    val end = times.maxOrNull()

    Canvas(modifier) {
        val left = 2.dp.toPx()
        val right = size.width - 2.dp.toPx()
        val top = 2.dp.toPx()
        val bottom = size.height - 2.dp.toPx()
        val width = max(1f, right - left)
        val height = max(1f, bottom - top)

        repeat(5) { index ->
            val y = top + height * index / 4f
            drawLine(grid.copy(alpha = 0.85f), Offset(left, y), Offset(right, y), strokeWidth = 1.dp.toPx())
        }
        repeat(5) { index ->
            val x = left + width * index / 4f
            drawLine(grid.copy(alpha = 0.45f), Offset(x, top), Offset(x, bottom), strokeWidth = 1.dp.toPx())
        }
        drawLine(axis, Offset(left, top), Offset(left, bottom), strokeWidth = 1.5.dp.toPx())
        drawLine(axis, Offset(left, bottom), Offset(right, bottom), strokeWidth = 1.5.dp.toPx())

        fun xFor(index: Int, item: GraphSeries): Float =
            left + width * graphPosition(item.points[index].label, index, item.points.size, start, end)

        fun yFor(value: Double): Float {
            val span = (range.upper - range.lower).takeIf { it > 0.0000001 } ?: 1.0
            val normalised = ((value - range.lower) / span).toFloat().coerceIn(0f, 1f)
            return bottom - height * normalised
        }

        when (mode) {
            "bars" -> {
                val flattened = if (series.size == 1) series.first().points else series.flatMap { item -> item.points }
                val count = flattened.size.coerceAtLeast(1)
                val slot = width / count
                val barWidth = (slot * 0.68f).coerceAtLeast(2.dp.toPx())
                val zeroY = yFor(0.0.coerceIn(range.lower, range.upper))
                flattened.forEachIndexed { index, point ->
                    if (!point.value.isFinite()) return@forEachIndexed
                    val centre = left + slot * (index + 0.5f)
                    val valueY = yFor(point.value)
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
                        if (!point.value.isFinite()) return@forEachIndexed
                        drawCircle(colour, radius = 4.dp.toPx(), center = Offset(xFor(index, item), yFor(point.value)))
                    }
                }
            }

            else -> {
                series.forEachIndexed { seriesIndex, item ->
                    if (item.points.isEmpty()) return@forEachIndexed
                    val colour = palette[seriesIndex % palette.size]
                    val path = Path()
                    var connected = false
                    item.points.forEachIndexed { index, point ->
                        if (!point.value.isFinite()) {
                            connected = false
                            return@forEachIndexed
                        }
                        val x = xFor(index, item)
                        val y = yFor(point.value)
                        if (!connected) path.moveTo(x, y) else path.lineTo(x, y)
                        connected = true
                    }
                    if (mode == "area" && item.points.all { it.value.isFinite() }) {
                        val area = Path().apply {
                            moveTo(xFor(0, item), bottom)
                            lineTo(xFor(0, item), yFor(item.points.first().value))
                            item.points.forEachIndexed { index, point ->
                                lineTo(xFor(index, item), yFor(point.value))
                            }
                            lineTo(xFor(item.points.lastIndex, item), bottom)
                            close()
                        }
                        drawPath(area, colour.copy(alpha = 0.14f))
                    }
                    drawPath(path, colour, style = Stroke(width = 3.dp.toPx()))
                    item.points.forEachIndexed { index, point ->
                        if (!point.value.isFinite()) return@forEachIndexed
                        if (item.points.size <= 24 || index == 0 || index == item.points.lastIndex) {
                            drawCircle(colour, radius = 3.dp.toPx(), center = Offset(xFor(index, item), yFor(point.value)))
                        }
                    }
                }
            }
        }
    }
}

private fun graphRange(mode: String, series: List<GraphSeries>): GraphRange {
    val values = series.flatMap { it.points }.map { it.value }.filter { it.isFinite() }
    if (values.isEmpty()) return GraphRange(0.0, 1.0)

    val rawMin = values.minOrNull() ?: 0.0
    val rawMax = values.maxOrNull() ?: 1.0
    val spread = (rawMax - rawMin).takeIf { it > 0.0000001 }
        ?: max(kotlin.math.abs(rawMax), 1.0)

    return if (mode == "bars") {
        val baseLower = min(0.0, rawMin)
        val baseUpper = max(0.0, rawMax)
        val span = (baseUpper - baseLower).takeIf { it > 0.0000001 } ?: 1.0
        GraphRange(
            lower = if (rawMin < 0.0) baseLower - span * 0.05 else baseLower,
            upper = baseUpper + span * 0.08,
        )
    } else {
        GraphRange(
            lower = rawMin - spread * 0.08,
            upper = rawMax + spread * 0.08,
        )
    }
}

private fun graphTicks(range: GraphRange): List<Double> {
    val span = (range.upper - range.lower).takeIf { it > 0.0000001 } ?: 1.0
    return (0..4).map { index -> range.lower + span * index / 4.0 }
}

private fun graphXAxisLabels(series: List<GraphSeries>, maximum: Int = 3): List<String> {
    val points = series.firstOrNull()?.points.orEmpty()
    if (points.isEmpty()) return emptyList()
    if (points.size <= maximum) return points.map { shortGraphLabel(it.label) }

    return (0 until maximum)
        .map { index -> ((points.lastIndex.toDouble() * index) / (maximum - 1)).toInt() }
        .distinct()
        .map { index -> shortGraphLabel(points[index].label) }
}

private fun shortGraphLabel(value: String): String {
    val trimmed = value.trim()
    graphTimeLabel(trimmed)?.let { return it }
    return trimmed.take(18)
}

private fun formatAxisValue(value: Double): String {
    val digits = when {
        kotlin.math.abs(value) >= 1000 -> 0
        kotlin.math.abs(value) >= 100 -> 1
        else -> 2
    }
    return ("%." + digits + "f").format(value)
}

private fun formatGraphValue(value: Double, unit: String): String {
    val digits = when {
        kotlin.math.abs(value) >= 1000 -> 0
        kotlin.math.abs(value) >= 100 -> 1
        else -> 2
    }
    return (("%." + digits + "f%s").format(value, if (unit.isBlank()) "" else " " + unit))
}
