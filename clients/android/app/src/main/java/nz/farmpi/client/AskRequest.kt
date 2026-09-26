package nz.farmpi.client

import org.json.JSONObject

/** Shared by typed, spoken and suggested questions; course state is not an input. */
internal fun askRequestBody(
    question: String,
    explanation: String,
    guidance: String,
    conversationId: String?,
): JSONObject = JSONObject()
    .put("question", question)
    .put("preferences", JSONObject().put("explanation_level", explanation).put("guidance_level", guidance))
    .apply { if (conversationId != null) put("conversation_id", conversationId) }
