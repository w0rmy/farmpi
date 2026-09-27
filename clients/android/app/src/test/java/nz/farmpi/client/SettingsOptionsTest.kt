package nz.farmpi.client

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Test

class SettingsOptionsTest {
    @Test
    fun explanationOptionsMatchBackendContract() {
        assertEquals(listOf("simple", "normal", "technical"), EXPLANATION_OPTIONS.map { it.key })
    }

    @Test
    fun guidanceOptionsMatchBackendContract() {
        assertEquals(listOf("more", "normal", "less"), GUIDANCE_OPTIONS.map { it.key })
    }

    @Test
    fun textSizeRemainsPresentationOnly() {
        assertEquals(listOf("compact", "standard", "large"), TEXT_SIZE_OPTIONS.map { it.key })
        val request = askRequestBody("Which paddock is driest?", "normal", "normal", null)
        assertFalse(request.getJSONObject("preferences").has("display_density"))
    }
}
