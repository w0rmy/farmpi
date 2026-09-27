package nz.farmpi.client

import org.junit.Assert.*
import org.junit.Test

class AskRequestTest {
    @Test fun firstQuestionRetainsPreferencesWithoutCourseOrConversation() {
        val body = askRequestBody("Show current soil moisture", "simple", "less", null)
        assertEquals(setOf("question", "preferences"), body.keys().asSequence().toSet())
        assertEquals("Show current soil moisture", body.getString("question"))
        assertEquals("simple", body.getJSONObject("preferences").getString("explanation_level"))
        assertEquals("less", body.getJSONObject("preferences").getString("guidance_level"))
    }

    @Test fun followUpRetainsConversationWithoutModuleContext() {
        val body = askRequestBody("Explain that graph", "technical", "normal", "conversation-123")
        assertEquals(setOf("question", "preferences", "conversation_id"), body.keys().asSequence().toSet())
        assertEquals("conversation-123", body.getString("conversation_id"))
        assertFalse(body.has("course_module_id"))
    }
}
