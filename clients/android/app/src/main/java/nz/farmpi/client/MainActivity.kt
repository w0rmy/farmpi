package nz.farmpi.client

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Bundle
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import android.util.Log
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.net.URL
import java.util.Locale
import javax.net.ssl.HttpsURLConnection

private const val TTS_TAG = "FarmPiTTS"
private const val TTS_CHUNK_LIMIT = 3000

private data class SpeechResult(val heard: String, val interpreted: String, val changed: Boolean)
private data class ChartPoint(val label: String, val value: Double)
private data class ChartPayload(val type: String, val title: String, val unit: String, val period: String, val provenance: String, val series: List<Pair<String, List<ChartPoint>>>)
private data class AskResult(val answer: String, val spokenAnswer: String, val suggestions: List<String>, val intent: String, val conversationId: String?, val chart: ChartPayload?, val evidence: List<String>, val provenance: List<String>)
private class FarmPiApiException(message: String) : Exception(message)

private fun ttsChunks(text: String, maxChars: Int = TTS_CHUNK_LIMIT): List<String> {
    val clean = text.trim()
    if (clean.isEmpty()) return emptyList()
    if (clean.length <= maxChars) return listOf(clean)

    val chunks = mutableListOf<String>()
    var current = StringBuilder()
    val sentences = clean.split(Regex("(?<=[.!?])\\s+"))

    fun flushCurrent() {
        if (current.isNotEmpty()) {
            chunks += current.toString().trim()
            current = StringBuilder()
        }
    }

    for (sentence in sentences) {
        var remaining = sentence.trim()
        if (remaining.isEmpty()) continue

        while (remaining.length > maxChars) {
            flushCurrent()
            chunks += remaining.take(maxChars)
            remaining = remaining.drop(maxChars).trimStart()
        }

        val extra = if (current.isEmpty()) remaining.length else remaining.length + 1
        if (current.length + extra > maxChars) flushCurrent()
        if (current.isNotEmpty()) current.append(' ')
        current.append(remaining)
    }
    flushCurrent()
    return chunks
}

private val FarmPiColours = darkColorScheme(
    primary = Color(0xFF9ACBA6),
    onPrimary = Color(0xFF12351E),
    secondary = Color(0xFFB7C3B9),
    onSecondary = Color(0xFF26312A),
    background = Color(0xFF171A18),
    onBackground = Color(0xFFE3E7E1),
    surface = Color(0xFF202522),
    onSurface = Color(0xFFE3E7E1),
    surfaceVariant = Color(0xFF343A35),
    onSurfaceVariant = Color(0xFFC4CBC4),
)

@Composable
private fun FarmPiTheme(content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = FarmPiColours, content = content)
}

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent { FarmPiTheme { FarmPiApp() } }
    }
}

@Composable
private fun FarmPiApp() {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var question by remember { mutableStateOf("") }
    var answer by remember { mutableStateOf("Ask FarmPi about farming or your monitored farm data to begin.") }
    var connection by remember { mutableStateOf("Checking FarmPi…") }
    var heard by remember { mutableStateOf<String?>(null) }
    var interpreted by remember { mutableStateOf<String?>(null) }
    var suggestions by remember { mutableStateOf(listOf<String>()) }
    var explanation by remember { mutableStateOf("normal") }
    var guidance by remember { mutableStateOf("normal") }
    var learnTab by remember { mutableStateOf(false) }
    var asking by remember { mutableStateOf(false) }
    var isSpeaking by remember { mutableStateOf(false) }
    var chart by remember { mutableStateOf<ChartPayload?>(null) }
    var evidence by remember { mutableStateOf(emptyList<String>()) }
    var provenance by remember { mutableStateOf(emptyList<String>()) }
    var showEvidence by remember { mutableStateOf(false) }
    var conversationId by remember { mutableStateOf<String?>(null) }
    var ttsReady by remember { mutableStateOf(false) }
    var ttsStatus by remember { mutableStateOf("Voice: initialising…") }
    var lastQueuedText by remember { mutableStateOf("") }
    var utteranceCounter by remember { mutableLongStateOf(0L) }
    val recognizerHolder = remember { arrayOfNulls<SpeechRecognizer>(1) }
    val preferences = remember { context.getSharedPreferences("farmpi-learning", 0) }

    LaunchedEffect(Unit) {
        explanation = preferences.getString("explanation", "normal") ?: "normal"
        guidance = preferences.getString("guidance", "normal") ?: "normal"
    }

    val tts = remember {
        TextToSpeech(context) { status ->
            scope.launch {
                ttsReady = status == TextToSpeech.SUCCESS
                ttsStatus = if (ttsReady) "Voice: initialised; selecting en-NZ voice…" else "Voice: TTS initialisation failed ($status)"
                Log.d(TTS_TAG, "TTS initialisation status=$status success=$ttsReady")
            }
        }
    }

    LaunchedEffect(ttsReady) {
        if (!ttsReady) return@LaunchedEffect

        val nz = Locale("en", "NZ")
        var selectedLocale = nz
        var languageResult = if (tts.isLanguageAvailable(nz) >= TextToSpeech.LANG_AVAILABLE) {
            tts.setLanguage(nz)
        } else {
            TextToSpeech.LANG_NOT_SUPPORTED
        }
        if (languageResult < TextToSpeech.LANG_AVAILABLE) {
            selectedLocale = Locale.ENGLISH
            languageResult = tts.setLanguage(selectedLocale)
        }

        if (languageResult < TextToSpeech.LANG_AVAILABLE) {
            ttsReady = false
            ttsStatus = "Voice: no supported English TTS language is installed."
            Log.e(TTS_TAG, "No supported English TTS language; result=$languageResult")
            return@LaunchedEffect
        }

        val voices = tts.voices.orEmpty()
        val preferredVoice = voices.firstOrNull { it.locale.toLanguageTag().equals("en-NZ", ignoreCase = true) }
            ?: voices.firstOrNull { it.locale.language.equals("en", ignoreCase = true) }
        if (preferredVoice != null) tts.voice = preferredVoice

        val voice = tts.voice
        val localeTag = voice?.locale?.toLanguageTag() ?: selectedLocale.toLanguageTag()
        val voiceName = voice?.name ?: "default"
        ttsStatus = "Voice ready: $localeTag • $voiceName"
        Log.d(TTS_TAG, "TTS ready engine=${tts.defaultEngine} locale=$localeTag voice=$voiceName")
    }

    DisposableEffect(tts) {
        tts.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
            override fun onStart(utteranceId: String?) {
                scope.launch {
                    isSpeaking = true
                    ttsStatus = "Voice speaking: ${lastQueuedText.length} characters queued."
                }
                Log.d(TTS_TAG, "onStart id=$utteranceId")
            }

            override fun onDone(utteranceId: String?) {
                if (utteranceId?.endsWith("-last") == true) {
                    scope.launch {
                        isSpeaking = false
                        ttsStatus = "Voice finished: ${lastQueuedText.length} characters."
                    }
                }
                Log.d(TTS_TAG, "onDone id=$utteranceId")
            }

            @Deprecated("Deprecated in Android")
            override fun onError(utteranceId: String?) {
                scope.launch {
                    isSpeaking = false
                    ttsStatus = "Voice error while speaking. Check Logcat tag $TTS_TAG."
                }
                Log.e(TTS_TAG, "onError id=$utteranceId")
            }

            override fun onError(utteranceId: String?, errorCode: Int) {
                scope.launch {
                    isSpeaking = false
                    ttsStatus = "Voice error $errorCode while speaking. Check Logcat tag $TTS_TAG."
                }
                Log.e(TTS_TAG, "onError id=$utteranceId errorCode=$errorCode")
            }
        })
        onDispose {
            tts.stop()
            tts.shutdown()
        }
    }

    fun stopSpeaking() {
        val result = tts.stop()
        isSpeaking = false
        ttsStatus = "Voice stopped (result=$result)."
        Log.d(TTS_TAG, "stop result=$result")
    }

    fun speak(text: String) {
        val clean = text.trim()
        if (clean.isEmpty()) return

        // Stop recognition before playback so STT and TTS do not compete for
        // the same audio session on devices which manage them aggressively.
        recognizerHolder[0]?.cancel()
        tts.stop()
        isSpeaking = false

        if (!ttsReady) {
            ttsStatus = "Voice not ready; ${clean.length} characters were not queued."
            Log.w(TTS_TAG, "speak ignored because TTS is not ready; text=$clean")
            return
        }

        val chunks = ttsChunks(clean)
        if (chunks.isEmpty()) return
        lastQueuedText = clean
        utteranceCounter += 1
        val baseId = "farmpi-${System.currentTimeMillis()}-$utteranceCounter"
        val localeTag = tts.voice?.locale?.toLanguageTag() ?: "unknown"
        val voiceName = tts.voice?.name ?: "default"

        Log.d(TTS_TAG, "Queueing ${clean.length} chars in ${chunks.size} chunk(s); engine=${tts.defaultEngine}; locale=$localeTag; voice=$voiceName; text=$clean")

        chunks.forEachIndexed { index, chunk ->
            val isLast = index == chunks.lastIndex
            val utteranceId = "$baseId-${index + 1}${if (isLast) "-last" else ""}"
            val queueMode = if (index == 0) TextToSpeech.QUEUE_FLUSH else TextToSpeech.QUEUE_ADD
            val result = tts.speak(chunk, queueMode, null, utteranceId)
            Log.d(TTS_TAG, "speak result=$result id=$utteranceId chars=${chunk.length} text=$chunk")
            if (result == TextToSpeech.ERROR) {
                tts.stop()
                isSpeaking = false
                ttsStatus = "Voice queue error on chunk ${index + 1}/${chunks.size}."
                Log.e(TTS_TAG, "Failed to queue utterance id=$utteranceId")
                return
            }
        }

        ttsStatus = "Voice queued: ${clean.length} characters in ${chunks.size} chunk(s) • $localeTag • $voiceName"
    }

    fun checkStatus() = scope.launch {
        connection = "Checking FarmPi…"
        connection = try {
            if (FarmPiApi.status()) "FarmPi connected" else "FarmPi is unavailable"
        } catch (_: Exception) {
            "FarmPi is unavailable"
        }
    }

    fun ask(text: String, speechAlternatives: List<String> = emptyList()) = scope.launch {
        if (text.isBlank() || asking) return@launch
        stopSpeaking()
        asking = true
        answer = "Asking FarmPi…"
        try {
            val speech = if (speechAlternatives.isEmpty()) null else FarmPiApi.normalise(text, speechAlternatives)
            val routedQuestion = speech?.interpreted ?: text
            heard = speech?.heard
            interpreted = speech?.interpreted?.takeIf { speech.changed }
            question = routedQuestion
            val result = FarmPiApi.ask(routedQuestion, explanation, guidance, conversationId)
            conversationId = result.conversationId ?: conversationId
            answer = result.answer
            suggestions = result.suggestions
            chart = result.chart
            evidence = result.evidence
            provenance = result.provenance
            showEvidence = false
            connection = "FarmPi connected"
            speak(result.spokenAnswer)
        } catch (error: FarmPiApiException) {
            answer = error.message ?: "FarmPi could not complete that request."
            connection = "FarmPi connected — request not completed"
        } catch (error: Exception) {
            val detail = error.message?.takeIf { it.isNotBlank() }?.let { " ($it)" } ?: ""
            answer = "I could not reach FarmPi$detail. Check the local connection and certificate trust."
            connection = "FarmPi is unavailable"
        }
        asking = false
    }

    fun guideMe() = scope.launch {
        stopSpeaking()
        try {
            val guide = FarmPiApi.guidance(guidance)
            answer = guide.first
            suggestions = guide.second
            speak(guide.first)
        } catch (error: FarmPiApiException) {
            answer = error.message ?: "FarmPi guidance is unavailable."
        } catch (_: Exception) {
            answer = "FarmPi guidance is unavailable."
        }
    }

    val recordAudio = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        if (!granted) answer = "Microphone permission is needed for voice questions. You can still type a question."
    }

    val recognizer = remember {
        SpeechRecognizer.createSpeechRecognizer(context).also { recognizer ->
            recognizerHolder[0] = recognizer
            recognizer.setRecognitionListener(object : RecognitionListener {
                override fun onReadyForSpeech(params: Bundle?) { }
                override fun onBeginningOfSpeech() { }
                override fun onRmsChanged(rmsdB: Float) { }
                override fun onBufferReceived(buffer: ByteArray?) { }
                override fun onEndOfSpeech() { }
                override fun onError(error: Int) { answer = "I could not hear a complete question. Please try again or type it." }
                override fun onResults(results: Bundle?) {
                    val all = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION).orEmpty()
                    val top = all.firstOrNull().orEmpty()
                    if (top.isNotBlank()) ask(top, all.take(5))
                }
                override fun onPartialResults(partialResults: Bundle?) { }
                override fun onEvent(eventType: Int, params: Bundle?) { }
            })
        }
    }

    DisposableEffect(recognizer) {
        onDispose {
            if (recognizerHolder[0] === recognizer) recognizerHolder[0] = null
            recognizer.destroy()
        }
    }

    fun listen() {
        if (ContextCompat.checkSelfPermission(context, Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            recordAudio.launch(Manifest.permission.RECORD_AUDIO)
            return
        }
        stopSpeaking()
        recognizer.startListening(Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
            putExtra(RecognizerIntent.EXTRA_LANGUAGE, "en-NZ")
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 5)
        })
    }

    LaunchedEffect(Unit) { checkStatus() }

    Scaffold(bottomBar = {
        NavigationBar {
            NavigationBarItem(selected = !learnTab, onClick = { learnTab = false }, icon = { Text("💬") }, label = { Text("Ask") })
            NavigationBarItem(selected = learnTab, onClick = { learnTab = true }, icon = { Text("✓") }, label = { Text("Learn") })
        }
    }) { padding ->
        if (learnTab) {
            LearnArea(Modifier.padding(padding)) { prompt ->
                learnTab = false
                question = prompt
                ask(prompt)
            }
        } else {
            Column(
                modifier = Modifier.padding(padding).padding(20.dp).fillMaxSize().verticalScroll(rememberScrollState()),
                horizontalAlignment = Alignment.CenterHorizontally,
            ) {
                Text("FarmPi", style = MaterialTheme.typography.headlineLarge, fontWeight = FontWeight.Bold)
                Text(connection, style = MaterialTheme.typography.bodyMedium)
                Text(ttsStatus, style = MaterialTheme.typography.bodySmall, textAlign = TextAlign.Center)
                Spacer(Modifier.height(18.dp))
                OutlinedTextField(
                    value = question,
                    onValueChange = { question = it },
                    modifier = Modifier.fillMaxWidth(),
                    label = { Text("Ask about farming or your farm data") },
                    minLines = 3,
                )
                Spacer(Modifier.height(10.dp))
                Button(
                    onClick = { if (isSpeaking) stopSpeaking() else listen() },
                    modifier = Modifier.size(132.dp),
                    enabled = !asking || isSpeaking,
                ) {
                    Text(if (isSpeaking) "■\nStop" else "🎤\nSpeak", textAlign = TextAlign.Center, style = MaterialTheme.typography.titleLarge)
                }
                Spacer(Modifier.height(10.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Button(onClick = { ask(question) }, enabled = !asking) { Text("Ask FarmPi") }
                    OutlinedButton(onClick = { guideMe() }) { Text("Guide me") }
                }
                if (heard != null) Text("Heard: $heard", modifier = Modifier.fillMaxWidth().padding(top = 14.dp), style = MaterialTheme.typography.bodySmall)
                if (interpreted != null) Text("Interpreted: $interpreted", modifier = Modifier.fillMaxWidth(), style = MaterialTheme.typography.bodySmall, fontWeight = FontWeight.Bold)
                Card(modifier = Modifier.fillMaxWidth().padding(top = 14.dp)) {
                    Text(answer, modifier = Modifier.padding(16.dp), style = MaterialTheme.typography.bodyLarge)
                }
                chart?.let { ChartCard(it) }
                if (evidence.isNotEmpty() || provenance.isNotEmpty()) {
                    TextButton(onClick = { showEvidence = !showEvidence }) {
                        Text(if (showEvidence) "Hide sources / evidence" else "Show sources / evidence")
                    }
                    if (showEvidence) {
                        Card(Modifier.fillMaxWidth()) {
                            Column(Modifier.padding(12.dp)) {
                                if (provenance.isNotEmpty()) {
                                    Text("Sources / provenance", fontWeight = FontWeight.Bold)
                                    provenance.take(12).forEach { Text(it, style = MaterialTheme.typography.bodySmall) }
                                }
                                if (evidence.isNotEmpty()) {
                                    Text("Evidence used", modifier = Modifier.padding(top = 8.dp), fontWeight = FontWeight.Bold)
                                    evidence.take(12).forEach { Text(it, style = MaterialTheme.typography.bodySmall) }
                                }
                            }
                        }
                    }
                }
                suggestions.forEach { suggestion ->
                    TextButton(onClick = { question = suggestion; ask(suggestion) }) {
                        Text(suggestion, textAlign = TextAlign.Start)
                    }
                }
                Preferences(
                    explanation,
                    guidance,
                    { explanation = it; preferences.edit().putString("explanation", it).apply() },
                    { guidance = it; preferences.edit().putString("guidance", it).apply() },
                )
            }
        }
    }
}

@Composable
private fun ChartCard(chart: ChartPayload) {
    Card(Modifier.fillMaxWidth().padding(top = 12.dp)) {
        Column(Modifier.padding(14.dp)) {
            Text(chart.title, fontWeight = FontWeight.Bold)
            Text("${chart.period} • ${chart.provenance}", style = MaterialTheme.typography.bodySmall)
            val points = chart.series.flatMap { it.second }
            val maximum = points.maxOfOrNull { it.value }?.takeIf { it > 0.0 } ?: 1.0
            chart.series.forEach { (name, values) ->
                Text(name, modifier = Modifier.padding(top = 8.dp), style = MaterialTheme.typography.labelLarge)
                if (chart.type == "bar") {
                    values.forEach { point ->
                        Text("${point.label}: ${"%.2f".format(point.value)} ${chart.unit}", style = MaterialTheme.typography.bodySmall)
                        LinearProgressIndicator(
                            progress = (point.value / maximum).toFloat().coerceIn(0f, 1f),
                            modifier = Modifier.fillMaxWidth().height(9.dp).padding(bottom = 4.dp),
                            color = MaterialTheme.colorScheme.primary,
                        )
                    }
                } else {
                    Row(Modifier.fillMaxWidth().height(54.dp), verticalAlignment = Alignment.Bottom) {
                        values.takeLast(24).forEach { point ->
                            Box(
                                Modifier.weight(1f)
                                    .fillMaxHeight((point.value / maximum).toFloat().coerceIn(.03f, 1f))
                                    .padding(horizontal = 1.dp)
                                    .background(MaterialTheme.colorScheme.primary, RoundedCornerShape(topStart = 3.dp, topEnd = 3.dp)),
                            )
                        }
                    }
                    values.takeLast(2).forEach { point ->
                        Text("${point.label}: ${"%.2f".format(point.value)} ${chart.unit}", style = MaterialTheme.typography.bodySmall)
                    }
                }
            }
        }
    }
}

@Composable
private fun Preferences(explanation: String, guidance: String, setExplanation: (String) -> Unit, setGuidance: (String) -> Unit) {
    Text("Explanation", modifier = Modifier.padding(top = 14.dp), fontWeight = FontWeight.Bold)
    Row {
        listOf("simple", "normal", "technical").forEach { value ->
            FilterChip(selected = explanation == value, onClick = { setExplanation(value) }, label = { Text(value) }, modifier = Modifier.padding(end = 6.dp))
        }
    }
    Text("Guidance", modifier = Modifier.padding(top = 8.dp), fontWeight = FontWeight.Bold)
    Row {
        listOf("more", "normal", "less").forEach { value ->
            FilterChip(selected = guidance == value, onClick = { setGuidance(value) }, label = { Text(value) }, modifier = Modifier.padding(end = 6.dp))
        }
    }
}

@Composable
private fun LearnArea(modifier: Modifier, usePrompt: (String) -> Unit) = Column(modifier.padding(20.dp).verticalScroll(rememberScrollState())) {
    Text("Learn FarmPi", style = MaterialTheme.typography.headlineMedium)
    Text("Ask naturally. FarmPi combines verified farm data with agricultural teaching and clearly separated source provenance.")
    listOf(
        "Getting started" to "Guide me",
        "One paddock" to "What is Paddock A's soil EC?",
        "Compare paddocks" to "Compare soil EC across all paddocks.",
        "Inspect a trend" to "Show a graph of soil moisture over the last 24 hours.",
        "Understand a measurement" to "What does soil EC mean?",
        "Learn a farming concept" to "Why do dairy cows get milk fever?",
        "Use a NZ source" to "What does DairyNZ say about irrigation scheduling?",
        "Safe boundaries" to "Should I irrigate Paddock A?",
    ).forEach { (title, prompt) ->
        Card(Modifier.fillMaxWidth().padding(top = 10.dp)) {
            Column(Modifier.padding(14.dp)) {
                Text(title, fontWeight = FontWeight.Bold)
                Text("Try this FarmPi learning question, then inspect the answer and its sources or evidence.")
                TextButton(onClick = { usePrompt(prompt) }) { Text(prompt) }
            }
        }
    }
}

private object FarmPiApi {
    private fun request(path: String, method: String = "GET", body: JSONObject? = null): JSONObject {
        val connection = (URL(BuildConfig.FARMPI_BASE_URL + path.removePrefix("/")).openConnection() as HttpsURLConnection)
        connection.requestMethod = method
        connection.connectTimeout = 5_000
        connection.readTimeout = 30_000
        connection.setRequestProperty("Accept", "application/json")
        if (body != null) {
            connection.doOutput = true
            connection.setRequestProperty("Content-Type", "application/json")
            connection.outputStream.use { it.write(body.toString().toByteArray()) }
        }
        val status = connection.responseCode
        val stream = if (status in 200..299) connection.inputStream else connection.errorStream
        val text = stream?.bufferedReader()?.use { it.readText() }.orEmpty()
        if (status !in 200..299) {
            val detail = try {
                JSONObject(text).optString("detail").takeIf { it.isNotBlank() }
            } catch (_: Exception) {
                null
            }
            throw FarmPiApiException(detail ?: "FarmPi returned HTTP $status.")
        }
        return JSONObject(text)
    }

    suspend fun status(): Boolean = withContext(Dispatchers.IO) {
        request("api/status").optString("status") == "running"
    }

    suspend fun guidance(level: String): Pair<String, List<String>> = withContext(Dispatchers.IO) {
        val json = request("api/guidance?guidance_level=$level")
        json.optString("welcome") to json.optJSONArray("suggestions").strings()
    }

    suspend fun normalise(transcript: String, alternatives: List<String>): SpeechResult = withContext(Dispatchers.IO) {
        val array = JSONArray()
        alternatives.forEach { array.put(JSONObject().put("transcript", it)) }
        val json = request("api/speech/normalize", "POST", JSONObject().put("transcript", transcript).put("alternatives", array))
        SpeechResult(
            json.getString("raw_transcript"),
            json.getString("normalized_transcript"),
            json.getBoolean("correction_applied") || json.getBoolean("alternative_selected"),
        )
    }

    suspend fun ask(question: String, explanation: String, guidance: String, conversationId: String?): AskResult = withContext(Dispatchers.IO) {
        val body = JSONObject()
            .put("question", question)
            .put("preferences", JSONObject().put("explanation_level", explanation).put("guidance_level", guidance))
        if (conversationId != null) body.put("conversation_id", conversationId)
        val json = request("api/ask", "POST", body)
        AskResult(
            json.getString("answer"),
            json.optString("spoken_answer", json.getString("answer")),
            json.optJSONArray("suggestions").strings(),
            json.optString("intent"),
            json.optString("conversation_id").takeIf { it.isNotBlank() },
            json.optJSONObject("chart")?.chart(),
            json.optJSONArray("evidence")?.objectsAsStrings() ?: emptyList(),
            json.optJSONArray("provenance")?.objectsAsStrings() ?: emptyList(),
        )
    }

    private fun JSONObject.chart(): ChartPayload {
        val entries = optJSONArray("series") ?: JSONArray()
        val series = (0 until entries.length()).map { index ->
            val item = entries.getJSONObject(index)
            val points = item.optJSONArray("data") ?: JSONArray()
            item.optString("name") to (0 until points.length()).map { point ->
                points.getJSONObject(point).let { ChartPoint(it.optString("x"), it.optDouble("y")) }
            }
        }
        return ChartPayload(optString("type"), optString("title"), optString("unit"), optString("source_period"), optString("provenance"), series)
    }

    private fun JSONArray?.strings(): List<String> = if (this == null) emptyList() else (0 until length()).map { getString(it) }
    private fun JSONArray.objectsAsStrings(): List<String> = (0 until length()).map { index -> getJSONObject(index).toString() }
}
