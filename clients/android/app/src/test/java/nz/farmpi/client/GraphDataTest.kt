package nz.farmpi.client

import java.time.ZoneId
import org.junit.Assert.*
import org.junit.Test

class GraphDataTest {
    @Test fun backendNaiveTimesUseUtc() {
        assertEquals(graphTime("2026-09-27T01:00:00Z"), graphTime("2026-09-27T01:00:00"))
        assertEquals(graphTime("2026-09-27T01:00:00Z"), graphTime("2026-09-27T13:00:00+12:00"))
        assertNull(graphTime("North paddock"))
    }
    @Test fun graphLabelsUseDeviceLocalZoneIncludingNzDst() {
        assertEquals(
            "28 Sep\n18:35",
            graphTimeLabel("2026-09-28T05:35:00Z", ZoneId.of("Pacific/Auckland")),
        )
        assertEquals(
            "28 Sep\n05:35",
            graphTimeLabel("2026-09-28T05:35:00Z", ZoneId.of("UTC")),
        )
    }

    @Test fun unequalSamplingIntervalsPreserveVisibleTimeGaps() {
        val start = graphTime("2026-09-27T00:00:00")!!
        val end = graphTime("2026-09-27T10:00:00")!!
        assertEquals(.1f, graphPosition("2026-09-27T01:00:00", 1, 3, start, end), .0001f)
        assertEquals(1f, graphPosition("2026-09-27T10:00:00", 2, 3, start, end), .0001f)
    }
    @Test fun categoricalAndSinglePointsRemainFinite() {
        assertEquals(.5f, graphPosition("North", 0, 1, null, null), 0f)
        assertEquals(.5f, graphPosition("South", 1, 3, null, null), 0f)
    }
}
