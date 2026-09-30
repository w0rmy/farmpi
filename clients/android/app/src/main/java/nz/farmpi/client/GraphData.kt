package nz.farmpi.client

import java.time.Instant
import java.time.LocalDateTime
import java.time.OffsetDateTime
import java.time.ZoneId
import java.time.ZoneOffset
import java.time.format.DateTimeFormatter
import java.util.Locale

// The backend labels naive historical timestamps as UTC.
internal fun graphTime(label: String): Long? =
    runCatching { Instant.parse(label).toEpochMilli() }.getOrNull()
        ?: runCatching { OffsetDateTime.parse(label).toInstant().toEpochMilli() }.getOrNull()
        ?: runCatching { LocalDateTime.parse(label).toInstant(ZoneOffset.UTC).toEpochMilli() }.getOrNull()

internal fun graphPosition(label: String, index: Int, count: Int, start: Long?, end: Long?): Float {
    val timestamp = graphTime(label)
    return if (timestamp != null && start != null && end != null && end > start)
        ((timestamp - start).toDouble() / (end - start)).toFloat().coerceIn(0f, 1f)
    else if (count <= 1) .5f else index.toFloat() / (count - 1)
}


private val graphAxisTimeFormatter: DateTimeFormatter =
    DateTimeFormatter.ofPattern("dd MMM\nHH:mm", Locale.ENGLISH)

internal fun graphTimeLabel(
    label: String,
    zoneId: ZoneId = ZoneId.systemDefault(),
): String? {
    val timestamp = graphTime(label) ?: return null
    return graphAxisTimeFormatter
        .withZone(zoneId)
        .format(Instant.ofEpochMilli(timestamp))
}
