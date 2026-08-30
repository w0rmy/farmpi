package nz.farmpi.client

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp

internal data class CourseOutcome(val id: String, val statement: String)
internal data class CourseTry(val id: String, val title: String, val instruction: String, val exampleQuestion: String, val successIntents: Set<String>)
internal data class CourseCheck(val prompt: String, val reflectionHint: String)
internal data class CourseModule(
    val id: String,
    val title: String,
    val learningOutcomes: List<String>,
    val learnContent: String,
    val tryActivity: CourseTry,
    val aiQuickPrompts: List<String>,
    val understandingCheck: CourseCheck,
    val continueContent: String,
    val nextModuleId: String?,
    val responseIntents: Set<String>,
)
internal data class CoursePayload(val title: String, val aim: String, val outcomes: List<CourseOutcome>, val modules: List<CourseModule>)
internal data class CourseProgress(
    val currentModuleId: String?,
    val completedTryIds: Set<String>,
    val completedCheckIds: Set<String>,
    val completedModuleIds: Set<String>,
)

@Composable
internal fun CourseArea(
    modifier: Modifier,
    course: CoursePayload?,
    loading: Boolean,
    error: String?,
    selectedModuleId: String?,
    progress: CourseProgress,
    onSelectModule: (String?) -> Unit,
    onLaunchTry: (CourseModule) -> Unit,
    onLaunchAsk: (CourseModule, String) -> Unit,
    onCompleteCheck: (CourseModule) -> Unit,
    onContinue: (CourseModule) -> Unit,
    onRetry: () -> Unit,
) = Column(modifier.padding(20.dp).verticalScroll(rememberScrollState())) {
    when {
        loading -> Text("Loading the FarmPi course…")
        error != null -> {
            Text(error)
            TextButton(onClick = onRetry) { Text("Try loading the course again") }
        }
        course == null -> Text("The FarmPi course is not available yet.")
        selectedModuleId != null -> {
            val module = course.modules.firstOrNull { it.id == selectedModuleId }
            if (module == null) {
                Text("That course module is no longer available.")
                TextButton(onClick = { onSelectModule(null) }) { Text("Back to course") }
            } else {
                ModuleArea(module, course.outcomes, progress, onSelectModule, onLaunchTry, onLaunchAsk, onCompleteCheck, onContinue)
            }
        }
        else -> CourseOverview(course, progress, onSelectModule)
    }
}

@Composable
private fun CourseOverview(course: CoursePayload, progress: CourseProgress, onSelectModule: (String?) -> Unit) {
    Text(course.title, style = MaterialTheme.typography.headlineSmall)
    Text("Course aim", modifier = Modifier.padding(top = 12.dp), fontWeight = FontWeight.Bold)
    Text(course.aim)
    Text("Learning outcomes", modifier = Modifier.padding(top = 16.dp), fontWeight = FontWeight.Bold)
    course.outcomes.forEach { outcome -> Text("${outcome.id}: ${outcome.statement}", modifier = Modifier.padding(top = 5.dp)) }
    val completed = progress.completedModuleIds.size.coerceAtMost(course.modules.size)
    Text("Progress: $completed of ${course.modules.size} modules completed", modifier = Modifier.padding(top = 18.dp), fontWeight = FontWeight.Bold)
    progress.currentModuleId?.let { current ->
        course.modules.firstOrNull { it.id == current }?.let { module ->
            TextButton(onClick = { onSelectModule(module.id) }) { Text("Continue course: ${module.title}") }
        }
    }
    Text("Modules", modifier = Modifier.padding(top = 10.dp), fontWeight = FontWeight.Bold)
    course.modules.forEachIndexed { index, module ->
        val complete = module.id in progress.completedModuleIds
        Card(Modifier.fillMaxWidth().padding(top = 10.dp)) {
            Column(Modifier.padding(14.dp)) {
                Text("${index + 1}. ${module.title}${if (complete) " ✓" else ""}", fontWeight = FontWeight.Bold)
                Text("${module.learningOutcomes.joinToString()} • Learn → Try → Ask → Check → Continue", style = MaterialTheme.typography.bodySmall)
                TextButton(onClick = { onSelectModule(module.id) }) { Text(if (index == 0 || complete) "Open module" else "Open module (you may explore in any order)") }
            }
        }
    }
}

@Composable
private fun ModuleArea(
    module: CourseModule,
    outcomes: List<CourseOutcome>,
    progress: CourseProgress,
    onSelectModule: (String?) -> Unit,
    onLaunchTry: (CourseModule) -> Unit,
    onLaunchAsk: (CourseModule, String) -> Unit,
    onCompleteCheck: (CourseModule) -> Unit,
    onContinue: (CourseModule) -> Unit,
) {
    TextButton(onClick = { onSelectModule(null) }) { Text("← All modules") }
    Text(module.title, style = MaterialTheme.typography.headlineSmall)
    Text(module.learningOutcomes.joinToString { id -> outcomes.firstOrNull { it.id == id }?.let { "$id" } ?: id }, style = MaterialTheme.typography.bodySmall)
    CourseStep("Learn", module.learnContent)
    CourseStep("Try", module.tryActivity.instruction)
    TextButton(onClick = { onLaunchTry(module) }) { Text("Try: ${module.tryActivity.exampleQuestion}") }
    if (module.id in progress.completedTryIds) Text("Try activity recognised from a real FarmPi response ✓", style = MaterialTheme.typography.bodySmall)
    CourseStep("Ask", "Use an example or ask your own follow-up. Your module context stays attached while you explore.")
    module.aiQuickPrompts.forEach { prompt -> TextButton(onClick = { onLaunchAsk(module, prompt) }) { Text(prompt) } }
    CourseStep("Check", module.understandingCheck.prompt)
    Text(module.understandingCheck.reflectionHint, style = MaterialTheme.typography.bodySmall)
    OutlinedButton(onClick = { onCompleteCheck(module) }, modifier = Modifier.padding(top = 8.dp)) {
        Text(if (module.id in progress.completedCheckIds) "Reflection noted" else "I have considered this")
    }
    CourseStep("Continue", module.continueContent)
    Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.padding(top = 8.dp)) {
        OutlinedButton(onClick = { onSelectModule(null) }) { Text("Course overview") }
        TextButton(onClick = { onContinue(module) }) { Text(if (module.nextModuleId == null) "Finish course" else "Next module") }
    }
    Spacer(Modifier.height(20.dp))
}

@Composable
private fun CourseStep(title: String, body: String) {
    Text(title, modifier = Modifier.padding(top = 18.dp), fontWeight = FontWeight.Bold)
    Text(body)
}
