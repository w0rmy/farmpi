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
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
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

private data class SpeechResult(val heard: String, val interpreted: String, val changed: Boolean)

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent { MaterialTheme { FarmPiApp() } }
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
    var learnTab by remember { mutableStateOf(false) }
    var asking by remember { mutableStateOf(false) }
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
            val result = FarmPiApi.ask(routedQuestion, explanation, guidance)
            answer = result.first; suggestions = result.second; connection = "FarmPi connected"; speak(result.first)
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
    Scaffold(bottomBar = { NavigationBar {
        NavigationBarItem(selected = !learnTab, onClick = { learnTab = false }, icon = { Text("💬") }, label = { Text("Ask") })
        NavigationBarItem(selected = learnTab, onClick = { learnTab = true }, icon = { Text("✓") }, label = { Text("Learn") })
    } }) { padding ->
        if (learnTab) LearnArea(Modifier.padding(padding)) else Column(
            modifier = Modifier.padding(padding).padding(20.dp).fillMaxSize().verticalScroll(rememberScrollState()),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text("FarmPi", style = MaterialTheme.typography.headlineLarge, fontWeight = FontWeight.Bold)
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
            Preferences(explanation, guidance, { explanation = it }, { guidance = it })
            if (heard != null) Text("Heard: $heard", modifier = Modifier.fillMaxWidth().padding(top = 14.dp), style = MaterialTheme.typography.bodySmall)
            if (interpreted != null) Text("Interpreted: $interpreted", modifier = Modifier.fillMaxWidth(), style = MaterialTheme.typography.bodySmall, fontWeight = FontWeight.Bold)
            Card(modifier = Modifier.fillMaxWidth().padding(top = 14.dp)) { Text(answer, modifier = Modifier.padding(16.dp), style = MaterialTheme.typography.bodyLarge) }
            suggestions.forEach { suggestion -> TextButton(onClick = { question = suggestion; ask(suggestion) }) { Text(suggestion, textAlign = TextAlign.Start) } }
        }
    }
}

@Composable
private fun Preferences(explanation: String, guidance: String, setExplanation: (String) -> Unit, setGuidance: (String) -> Unit) {
    Text("Explanation", modifier = Modifier.padding(top = 14.dp), fontWeight = FontWeight.Bold)
    Row { listOf("simple", "normal", "technical").forEach { value -> FilterChip(selected = explanation == value, onClick = { setExplanation(value) }, label = { Text(value) }, modifier = Modifier.padding(end = 6.dp)) } }
    Text("Guidance", modifier = Modifier.padding(top = 8.dp), fontWeight = FontWeight.Bold)
    Row { listOf("more", "normal", "less").forEach { value -> FilterChip(selected = guidance == value, onClick = { setGuidance(value) }, label = { Text(value) }, modifier = Modifier.padding(end = 6.dp)) } }
}

@Composable
private fun LearnArea(modifier: Modifier) = Column(modifier.padding(20.dp).verticalScroll(rememberScrollState())) {
    Text("Learn FarmPi", style = MaterialTheme.typography.headlineMedium)
    Text("Short teach-by-doing tasks use only verified FarmPi information.")
    listOf("Getting started — use Guide me, then ask one question.", "One paddock — ask for Paddock A's soil EC.", "Compare paddocks — ask which paddock is driest.", "Understand data — ask about a unit and simulated provenance.", "Unavailable answers — ask for irrigation advice and see the safe boundary.").forEach { task -> Card(Modifier.fillMaxWidth().padding(top = 10.dp)) { Text(task, Modifier.padding(14.dp)) } }
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
    suspend fun ask(question: String, explanation: String, guidance: String): Pair<String, List<String>> = withContext(Dispatchers.IO) {
        val body = JSONObject().put("question", question).put("preferences", JSONObject().put("explanation_level", explanation).put("guidance_level", guidance)); val json = request("api/ask", "POST", body)
        json.getString("answer") to json.optJSONArray("suggestions").strings()
    }
    private fun JSONArray?.strings(): List<String> = if (this == null) emptyList() else (0 until length()).map { getString(it) }
}
