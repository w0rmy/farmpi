package nz.farmpi.client

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Bundle
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.speech.tts.TextToSpeech
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.background
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.Density
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

private data class SpeechResult(val heard: String, val interpreted: String, val changed: Boolean)
private data class ChartPoint(val label: String, val value: Double)
private data class ChartPayload(val type: String, val title: String, val unit: String, val period: String, val provenance: String, val series: List<Pair<String, List<ChartPoint>>>)
private data class AskResult(val answer: String, val spokenAnswer: String, val suggestions: List<String>, val intent: String, val conversationId: String?, val chart: ChartPayload?, val evidence: List<String>, val sourceTier: String)

private val NeutralColours = darkColorScheme(
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
private fun FarmPiTheme(theme: String, displayDensity: String, content: @Composable () -> Unit) {
    val colours = when (theme) {
        "nz" -> lightColorScheme(
            primary = Color(0xFF003F7F), onPrimary = Color.White, secondary = Color(0xFFC8102E), onSecondary = Color.White,
            background = Color(0xFFF8F9FC), onBackground = Color(0xFF172033), surface = Color.White, onSurface = Color(0xFF172033),
            surfaceVariant = Color(0xFFE5ECF6), onSurfaceVariant = Color(0xFF263A5A),
        )
        "natural" -> lightColorScheme(
            primary = Color(0xFF2F6B3C), onPrimary = Color.White, secondary = Color(0xFF7B5E2F), onSecondary = Color.White,
            background = Color(0xFFF7FAF4), onBackground = Color(0xFF1A271C), surface = Color(0xFFFFFFFF), onSurface = Color(0xFF1A271C),
            surfaceVariant = Color(0xFFE2ECDD), onSurfaceVariant = Color(0xFF314735),
        )
        "high-contrast" -> darkColorScheme(
            primary = Color(0xFFFFFFFF), onPrimary = Color.Black, secondary = Color(0xFF00E5FF), onSecondary = Color.Black,
            background = Color.Black, onBackground = Color.White, surface = Color(0xFF121212), onSurface = Color.White,
            surfaceVariant = Color(0xFF2B2B2B), onSurfaceVariant = Color.White,
        )
        "high-visibility" -> darkColorScheme(
            primary = Color(0xFFFFFF00), onPrimary = Color.Black, secondary = Color(0xFFFFFF00), onSecondary = Color.Black,
            background = Color.Black, onBackground = Color(0xFFFFFF00), surface = Color(0xFF111111), onSurface = Color(0xFFFFFF00),
            surfaceVariant = Color(0xFF252500), onSurfaceVariant = Color(0xFFFFFF00),
        )
        "muted" -> lightColorScheme(
            primary = Color(0xFF5C6170), onPrimary = Color.White, secondary = Color(0xFF7B7085), onSecondary = Color.White,
            background = Color(0xFFF3F1F0), onBackground = Color(0xFF29282D), surface = Color(0xFFF9F7F6), onSurface = Color(0xFF29282D),
            surfaceVariant = Color(0xFFE5E1E0), onSurfaceVariant = Color(0xFF5A5559),
        )
        else -> NeutralColours
    }
    val density = LocalDensity.current
    val fontScale = when (displayDensity) { "compact" -> 0.90f; "large" -> 1.25f; else -> 1.0f }
    CompositionLocalProvider(LocalDensity provides Density(density.density, fontScale)) {
        MaterialTheme(colorScheme = colours, content = content)
    }
}

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent { FarmPiApp() }
    }
}

@Composable
private fun FarmPiApp() {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var question by remember { mutableStateOf("") }
    var answer by remember { mutableStateOf("Ask FarmPi about a paddock to begin.") }
    var connection by remember { mutableStateOf("Checking FarmPi…") }
    var heard by remember { mutableStateOf<String?>(null) }
    var interpreted by remember { mutableStateOf<String?>(null) }
    var suggestions by remember { mutableStateOf(listOf<String>()) }
    var explanation by remember { mutableStateOf("normal") }
    var guidance by remember { mutableStateOf("normal") }
    var theme by remember { mutableStateOf("neutral") }
    var displayDensity by remember { mutableStateOf("standard") }
    var showSettings by remember { mutableStateOf(false) }
    var learnTab by remember { mutableStateOf(false) }
    var asking by remember { mutableStateOf(false) }
    var chart by remember { mutableStateOf<ChartPayload?>(null) }
    var evidence by remember { mutableStateOf(emptyList<String>()) }
    var sourceTier by remember { mutableStateOf<String?>(null) }
    var showEvidence by remember { mutableStateOf(false) }
    var conversationId by remember { mutableStateOf<String?>(null) }
    val preferences = remember { context.getSharedPreferences("farmpi-learning", 0) }
    LaunchedEffect(Unit) {
        explanation = preferences.getString("explanation", "normal") ?: "normal"
        guidance = preferences.getString("guidance", "normal") ?: "normal"
        theme = preferences.getString("theme", "neutral") ?: "neutral"
        displayDensity = preferences.getString("display_density", "standard") ?: "standard"
    }
    val tts = remember { TextToSpeech(context) { } }
    DisposableEffect(Unit) { onDispose { tts.shutdown() } }

    fun speak(text: String) { tts.language = Locale("en", "NZ"); tts.speak(text, TextToSpeech.QUEUE_FLUSH, null, "farmpi-answer") }
    fun checkStatus() = scope.launch {
        connection = "Checking FarmPi…"
        connection = try { if (FarmPiApi.status()) "FarmPi connected" else "FarmPi is unavailable" } catch (_: Exception) { "FarmPi is unavailable" }
    }
    fun ask(text: String, speechAlternatives: List<String> = emptyList()) = scope.launch {
        if (text.isBlank() || asking) return@launch
        asking = true; answer = "Asking FarmPi…"
        try {
            val speech = if (speechAlternatives.isEmpty()) null else FarmPiApi.normalise(text, speechAlternatives)
            val routedQuestion = speech?.interpreted ?: text
            heard = speech?.heard; interpreted = speech?.interpreted?.takeIf { speech.changed }
            question = routedQuestion
            val result = FarmPiApi.ask(routedQuestion, explanation, guidance, conversationId)
            conversationId = result.conversationId ?: conversationId
            answer = result.answer; suggestions = result.suggestions; chart = result.chart; evidence = result.evidence; sourceTier = result.sourceTier; showEvidence = false; connection = "FarmPi connected"; speak(result.spokenAnswer)
        } catch (_: Exception) { answer = "FarmPi is unavailable. Check the local connection and certificate trust."; connection = "FarmPi is unavailable" }
        asking = false
    }
    fun guideMe() = scope.launch {
        try { val guide = FarmPiApi.guidance(guidance); answer = guide.first; suggestions = guide.second; speak(guide.first) }
        catch (_: Exception) { answer = "FarmPi guidance is unavailable." }
    }

    val recordAudio = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        if (!granted) answer = "Microphone permission is needed for voice questions. You can still type a question."
    }
    val recognizer = remember {
        SpeechRecognizer.createSpeechRecognizer(context).also { recognizer ->
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
    DisposableEffect(Unit) { onDispose { recognizer.destroy() } }
    fun listen() {
        if (ContextCompat.checkSelfPermission(context, Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) { recordAudio.launch(Manifest.permission.RECORD_AUDIO); return }
        recognizer.startListening(Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
            putExtra(RecognizerIntent.EXTRA_LANGUAGE, "en-NZ")
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 5)
        })
    }

    LaunchedEffect(Unit) { checkStatus() }
    FarmPiTheme(theme, displayDensity) {
    Scaffold(
        topBar = { TopAppBar(title = { Text("FarmPi") }, actions = { IconButton(onClick = { showSettings = true }) { Text("⚙", style = MaterialTheme.typography.titleLarge) } }) },
        bottomBar = { NavigationBar {
            NavigationBarItem(selected = !learnTab, onClick = { learnTab = false }, icon = { Text("💬") }, label = { Text("Ask") })
            NavigationBarItem(selected = learnTab, onClick = { learnTab = true }, icon = { Text("✓") }, label = { Text("Learn") })
        } },
    ) { padding ->
        if (learnTab) LearnArea(Modifier.padding(padding)) { prompt -> learnTab = false; question = prompt; ask(prompt) } else Column(
            modifier = Modifier.padding(padding).padding(20.dp).fillMaxSize().verticalScroll(rememberScrollState()),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text(connection, style = MaterialTheme.typography.bodyMedium)
            Spacer(Modifier.height(18.dp))
            OutlinedTextField(value = question, onValueChange = { question = it }, modifier = Modifier.fillMaxWidth(), label = { Text("Ask about your farm data") }, minLines = 3)
            Spacer(Modifier.height(10.dp))
            Button(onClick = { listen() }, modifier = Modifier.size(132.dp), enabled = !asking) { Text("🎤\nSpeak", textAlign = TextAlign.Center, style = MaterialTheme.typography.titleLarge) }
            Spacer(Modifier.height(10.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(onClick = { ask(question) }, enabled = !asking) { Text("Ask FarmPi") }
                OutlinedButton(onClick = { guideMe() }) { Text("Guide me") }
            }
            if (heard != null) Text("Heard: $heard", modifier = Modifier.fillMaxWidth().padding(top = 14.dp), style = MaterialTheme.typography.bodySmall)
            if (interpreted != null) Text("Interpreted: $interpreted", modifier = Modifier.fillMaxWidth(), style = MaterialTheme.typography.bodySmall, fontWeight = FontWeight.Bold)
            Card(modifier = Modifier.fillMaxWidth().padding(top = 14.dp)) { Text(answer, modifier = Modifier.padding(16.dp), style = MaterialTheme.typography.bodyLarge) }
            sourceTier?.let { Text("Evidence: ${it.replace('-', ' ')}", modifier = Modifier.fillMaxWidth().padding(top = 6.dp), style = MaterialTheme.typography.bodySmall) }
            chart?.let { ChartCard(it) }
            if (evidence.isNotEmpty()) {
                TextButton(onClick = { showEvidence = !showEvidence }) { Text(if (showEvidence) "Hide evidence" else "Show evidence / data") }
                if (showEvidence) Card(Modifier.fillMaxWidth()) { Column(Modifier.padding(12.dp)) { Text("Evidence used", fontWeight = FontWeight.Bold); evidence.take(12).forEach { Text(it, style = MaterialTheme.typography.bodySmall) } } }
            }
            suggestions.forEach { suggestion -> TextButton(onClick = { question = suggestion; ask(suggestion) }) { Text(suggestion, textAlign = TextAlign.Start) } }
        }
    }
    if (showSettings) SettingsDialog(
        explanation, guidance, theme, displayDensity,
        setExplanation = { explanation = it; preferences.edit().putString("explanation", it).apply() },
        setGuidance = { guidance = it; preferences.edit().putString("guidance", it).apply() },
        setTheme = { theme = it; preferences.edit().putString("theme", it).apply() },
        setDisplayDensity = { displayDensity = it; preferences.edit().putString("display_density", it).apply() },
        close = { showSettings = false },
    )
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
                if (chart.type == "bar") values.forEach { point ->
                    Text("${point.label}: ${"%.2f".format(point.value)} ${chart.unit}", style = MaterialTheme.typography.bodySmall)
                    LinearProgressIndicator(progress = (point.value / maximum).toFloat().coerceIn(0f, 1f), modifier = Modifier.fillMaxWidth().height(9.dp).padding(bottom = 4.dp), color = MaterialTheme.colorScheme.primary)
                } else {
                    // Each point is an actual backend-supplied, timestamped value;
                    // the connected markers form a compact native line/spark view.
                    Row(Modifier.fillMaxWidth().height(54.dp), verticalAlignment = Alignment.Bottom) { values.takeLast(24).forEach { point -> Box(Modifier.weight(1f).fillMaxHeight((point.value / maximum).toFloat().coerceIn(.03f, 1f)).padding(horizontal = 1.dp).background(MaterialTheme.colorScheme.primary, RoundedCornerShape(topStart = 3.dp, topEnd = 3.dp))) } }
                    values.takeLast(2).forEach { point -> Text("${point.label}: ${"%.2f".format(point.value)} ${chart.unit}", style = MaterialTheme.typography.bodySmall) }
                }
            }
        }
    }
}

@Composable
private fun SettingsDialog(
    explanation: String, guidance: String, theme: String, displayDensity: String,
    setExplanation: (String) -> Unit, setGuidance: (String) -> Unit, setTheme: (String) -> Unit,
    setDisplayDensity: (String) -> Unit, close: () -> Unit,
) = AlertDialog(
    onDismissRequest = close,
    title = { Text("Display and learning settings") },
    text = { Column(Modifier.verticalScroll(rememberScrollState())) {
        Text("Explanation depth", fontWeight = FontWeight.Bold)
        SettingChips(listOf("simple", "normal", "technical"), explanation, setExplanation)
        Text("Guidance prompts", modifier = Modifier.padding(top = 10.dp), fontWeight = FontWeight.Bold)
        SettingChips(listOf("more", "normal", "less"), guidance, setGuidance)
        Text("Presentation theme", modifier = Modifier.padding(top = 10.dp), fontWeight = FontWeight.Bold)
        listOf("neutral" to "Neutral", "nz" to "NZ red, white and blue", "natural" to "Green / natural", "high-contrast" to "Dark high contrast", "high-visibility" to "Yellow / black", "muted" to "Muted / low stimulation").forEach { (key, label) ->
            FilterChip(selected = theme == key, onClick = { setTheme(key) }, label = { Text(label) }, modifier = Modifier.padding(end = 6.dp, bottom = 4.dp))
        }
        Text("Text size and density", modifier = Modifier.padding(top = 10.dp), fontWeight = FontWeight.Bold)
        SettingChips(listOf("compact", "standard", "large"), displayDensity, setDisplayDensity)
    } },
    confirmButton = { TextButton(onClick = close) { Text("Done") } },
)

@Composable
private fun SettingChips(values: List<String>, selected: String, setValue: (String) -> Unit) = Row {
    values.forEach { value -> FilterChip(selected = selected == value, onClick = { setValue(value) }, label = { Text(value) }, modifier = Modifier.padding(end = 6.dp)) }
}

@Composable
private fun LearnArea(modifier: Modifier, usePrompt: (String) -> Unit) = Column(modifier.padding(20.dp).verticalScroll(rememberScrollState())) {
    Text("Learn FarmPi", style = MaterialTheme.typography.headlineMedium)
    Text("Short teach-by-doing tasks use only verified FarmPi information.")
    listOf(
        "Getting started" to "Guide me",
        "One paddock" to "What is Paddock A's soil EC?",
        "Compare paddocks" to "Compare soil EC across all paddocks.",
        "Inspect a trend" to "Show a graph of soil moisture over the last 24 hours.",
        "Understand a measurement" to "What does soil EC mean?",
        "Understand provenance" to "Explain simulated data.",
        "Safe boundaries" to "Should I irrigate Paddock A?"
    ).forEach { (title, prompt) -> Card(Modifier.fillMaxWidth().padding(top = 10.dp)) { Column(Modifier.padding(14.dp)) { Text(title, fontWeight = FontWeight.Bold); Text("Try this real FarmPi task, then inspect the answer and evidence."); TextButton(onClick = { usePrompt(prompt) }) { Text(prompt) } } } }
}

private object FarmPiApi {
    private fun request(path: String, method: String = "GET", body: JSONObject? = null): JSONObject {
        val connection = (URL(BuildConfig.FARMPI_BASE_URL + path.removePrefix("/")).openConnection() as HttpsURLConnection)
        connection.requestMethod = method; connection.connectTimeout = 5_000; connection.readTimeout = 30_000; connection.setRequestProperty("Accept", "application/json")
        if (body != null) { connection.doOutput = true; connection.setRequestProperty("Content-Type", "application/json"); connection.outputStream.use { it.write(body.toString().toByteArray()) } }
        val stream = if (connection.responseCode in 200..299) connection.inputStream else connection.errorStream
        val text = stream.bufferedReader().use { it.readText() }; if (connection.responseCode !in 200..299) throw IllegalStateException(text)
        return JSONObject(text)
    }
    suspend fun status(): Boolean = withContext(Dispatchers.IO) { request("api/status").optString("status") == "running" }
    suspend fun guidance(level: String): Pair<String, List<String>> = withContext(Dispatchers.IO) { val json = request("api/guidance?guidance_level=$level"); json.optString("welcome") to json.optJSONArray("suggestions").strings() }
    suspend fun normalise(transcript: String, alternatives: List<String>): SpeechResult = withContext(Dispatchers.IO) {
        val array = JSONArray(); alternatives.forEach { array.put(JSONObject().put("transcript", it)) }; val json = request("api/speech/normalize", "POST", JSONObject().put("transcript", transcript).put("alternatives", array))
        SpeechResult(json.getString("raw_transcript"), json.getString("normalized_transcript"), json.getBoolean("correction_applied") || json.getBoolean("alternative_selected"))
    }
    suspend fun ask(question: String, explanation: String, guidance: String, conversationId: String?): AskResult = withContext(Dispatchers.IO) {
        val body = JSONObject().put("question", question).put("preferences", JSONObject().put("explanation_level", explanation).put("guidance_level", guidance)); if (conversationId != null) body.put("conversation_id", conversationId); val json = request("api/ask", "POST", body)
        AskResult(json.getString("answer"), json.optString("spoken_answer", json.getString("answer")), json.optJSONArray("suggestions").strings(), json.optString("intent"), json.optString("conversation_id").takeIf { it.isNotBlank() }, json.optJSONObject("chart")?.chart(), json.optJSONArray("evidence")?.let { evidence -> (0 until evidence.length()).map { evidence.getJSONObject(it).toString() } } ?: emptyList(), json.optString("source_tier", "first-class-trusted"))
    }
    private fun JSONObject.chart(): ChartPayload {
        val entries = optJSONArray("series") ?: JSONArray()
        val series = (0 until entries.length()).map { index ->
            val item = entries.getJSONObject(index); val points = item.optJSONArray("data") ?: JSONArray()
            item.optString("name") to (0 until points.length()).map { point -> points.getJSONObject(point).let { ChartPoint(it.optString("x"), it.optDouble("y")) } }
        }
        return ChartPayload(optString("type"), optString("title"), optString("unit"), optString("source_period"), optString("provenance"), series)
    }
    private fun JSONArray?.strings(): List<String> = if (this == null) emptyList() else (0 until length()).map { getString(it) }
}
