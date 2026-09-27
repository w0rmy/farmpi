package nz.farmpi.client

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class ApiTimeoutPolicyTest {
    @Test
    fun llmCapableAskRequestsHaveLongerReadWindowThanOrdinaryApiCalls() {
        assertEquals(30_000, DEFAULT_API_READ_TIMEOUT_MS)
        assertEquals(130_000, ASK_API_READ_TIMEOUT_MS)
        assertTrue(ASK_API_READ_TIMEOUT_MS > DEFAULT_API_READ_TIMEOUT_MS)
    }
}
