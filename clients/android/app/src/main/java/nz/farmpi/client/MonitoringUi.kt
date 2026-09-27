package nz.farmpi.client

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import org.json.JSONObject
import kotlinx.coroutines.launch

@Composable
internal fun StatusChip(text: String) {
    val palette = farmPiStatusPalette(text)
    Surface(shape = MaterialTheme.shapes.small, color = palette.background, contentColor = palette.foreground) {
        Text(
            text,
            Modifier.padding(horizontal = 10.dp, vertical = 5.dp),
            style = MaterialTheme.typography.labelMedium,
            fontWeight = FontWeight.SemiBold,
        )
    }
}

@Composable
private fun InfoCard(title: String, detail: String, content: @Composable ColumnScope.() -> Unit = {}) {
    Card(Modifier.fillMaxWidth(), colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)) {
        Column(Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Text(title, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.SemiBold)
            Text(detail, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
            content()
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun LocationSelector(
    label: String,
    locations: List<OverviewLocation>,
    selected: String,
    onSelect: (String) -> Unit,
    allowFarmWide: Boolean = false,
) {
    var expanded by remember { mutableStateOf(false) }
    val displayValue = selected.ifBlank { if (allowFarmWide) "Across the farm" else "Select location" }
    ExposedDropdownMenuBox(
        expanded = expanded,
        onExpandedChange = { expanded = !expanded },
    ) {
        OutlinedTextField(
            value = displayValue,
            onValueChange = {},
            readOnly = true,
            label = { Text(label) },
            trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = expanded) },
            modifier = Modifier.fillMaxWidth().menuAnchor(),
            singleLine = true,
        )
        ExposedDropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
            if (allowFarmWide) {
                DropdownMenuItem(
                    text = { Text("Across the farm") },
                    onClick = { onSelect(""); expanded = false },
                )
            }
            locations.forEach { item ->
                DropdownMenuItem(
                    text = {
                        Column {
                            Text(item.name)
                            Text(
                                if (item.hasReading) ageLabel(item.ageSeconds) else "No stored reading yet",
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                            )
                        }
                    },
                    onClick = { onSelect(item.name); expanded = false },
                )
            }
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
internal fun MonitoringArea(
    destination: String, connection: String, checkedAt: String, health: JSONObject?, location: String, explanation: String, guidance: String,
    modifier: Modifier = Modifier, navigate: (String) -> Unit, selectLocation: (String) -> Unit,
    openSettings: () -> Unit, refresh: () -> Unit, ask: (String) -> Unit,
) {
    val scope = rememberCoroutineScope()
    var result by remember(destination, location) { mutableStateOf<AskResult?>(null) }
    var loading by remember(destination, location) { mutableStateOf(false) }
    var requestError by remember(destination, location) { mutableStateOf<String?>(null) }
    var requested by remember(destination, location) { mutableStateOf("") }
    var receivedAt by remember(destination, location) { mutableStateOf("") }
    fun query(text: String) {
        if (loading) return
        loading = true; result = null; requestError = null; requested = text
        scope.launch {
            try { result = queryMonitoring(text, explanation, guidance); receivedAt = java.time.LocalTime.now().withNano(0).toString() }
            catch (e: Exception) { requestError = e.message ?: "FarmPi could not provide this information. Try again." }
            finally { loading = false }
        }
    }
    var overview by remember { mutableStateOf<MonitoringOverview?>(null) }
    var overviewLoading by remember { mutableStateOf(false) }
    var overviewError by remember { mutableStateOf<String?>(null) }

    fun refreshOverview() {
        if (overviewLoading) return
        overviewLoading = true
        overviewError = null
        scope.launch {
            try {
                overview = fetchMonitoringOverview()
            } catch (e: Exception) {
                overviewError = if (e.message?.contains("HTTP 404") == true) {
                    "This FarmPi server does not expose the monitoring overview API yet. Update and restart the FarmPi server, then try again."
                } else {
                    e.message ?: "FarmPi could not load the monitoring overview."
                }
            } finally {
                overviewLoading = false
            }
        }
    }

    var locationA by remember { mutableStateOf(location) }
    var locationB by remember { mutableStateOf("") }
    var measurement by remember { mutableStateOf("Soil moisture") }
    var period by remember { mutableStateOf("1 day") }
    var filter by remember { mutableStateOf("Active") }
    var details by remember { mutableStateOf(false) }
    LaunchedEffect(location) { locationA = location }
    LaunchedEffect(destination) {
        if (destination in setOf("Dashboard", "Location Detail", "Compare", "History")) refreshOverview()
    }
    LaunchedEffect(overview, location) {
        if (locationA.isBlank() && location.isNotBlank()) {
            overview?.locations?.firstOrNull { it.name.equals(location, ignoreCase = true) }?.let { locationA = it.name }
        }
    }
    Column(modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(20.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
        Text(destination, style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
        when (destination) {
            "Dashboard" -> {
                if (overviewLoading && overview == null) {
                    LinearProgressIndicator(Modifier.fillMaxWidth())
                    Text("Loading FarmPi monitoring data…")
                }
                overviewError?.let {
                    InfoMessageCard("Monitoring overview unavailable", it)
                    OutlinedButton(onClick = { refreshOverview() }) { Text("Try again") }
                }
                overview?.let { current ->
                    FarmOverviewHeader(
                        overview = current,
                        connection = connection,
                        checkedAt = checkedAt,
                        refresh = { refresh(); refreshOverview() },
                    )

                    Text("Latest measurements", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.SemiBold)
                    val moistureSparkline = current.featuredChart?.series?.firstOrNull()?.second.orEmpty()
                    MeasurementGrid(current.farmMeasurements, moistureSparkline)

                    current.featuredChart?.let { chart ->
                        Text("Recent trend", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.SemiBold)
                        EnhancedChartCard(
                            chart.title,
                            chart.unit,
                            chart.period,
                            chart.provenance,
                            chart.type,
                            chart.series.map { (name, points) -> GraphSeries(name, points.map { GraphPoint(it.label, it.value) }) },
                        )
                    }

                    Text("Locations", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.SemiBold)
                    if (current.locations.isEmpty()) {
                        InfoMessageCard("No locations configured", "Create and assign a farmer-named location from Nodes before monitoring data can appear here.")
                    } else {
                        current.locations.forEach { item ->
                            LocationOverviewCard(item) { selectLocation(item.name) }
                        }
                    }

                    InfoCard("Explore your farm", "Use the deterministic comparison/history tools or discuss the verified data with Ask FarmPi.") {
                        Button(onClick = { navigate("Compare") }) { Text("Compare locations") }
                        OutlinedButton(onClick = { navigate("History") }) { Text("History / Graphs") }
                        OutlinedButton(onClick = { ask("Summarise current conditions across the farm") }) { Text("Ask FarmPi") }
                    }
                }
            }
            "Location Detail" -> {
                if (overviewLoading && overview == null) {
                    LinearProgressIndicator(Modifier.fillMaxWidth())
                    Text("Loading location measurements…")
                }
                val selected = overview?.locations?.firstOrNull { it.name.equals(location, ignoreCase = true) }
                if (selected != null) {
                    LocationMeasurementSection(selected)
                    InfoCard("Explore ${selected.name}", "Use the same verified readings in history, comparison and Ask FarmPi.") {
                        Button(onClick = { navigate("History") }) { Text("View history") }
                        OutlinedButton(onClick = { navigate("Compare") }) { Text("Compare") }
                        OutlinedButton(onClick = { ask("Summarise current conditions for ${selected.name}") }) { Text("Ask about this location") }
                    }
                } else if (!overviewLoading && overviewError == null) {
                    InfoMessageCard("Location unavailable", "FarmPi does not have a configured location matching “$location” in the current overview.")
                }
                overviewError?.let {
                    InfoMessageCard("Location data unavailable", it)
                    OutlinedButton(onClick = { refreshOverview() }) { Text("Try again") }
                }
            }
            "Compare", "History" -> {
                InfoCard(if (destination == "Compare") "Compare two locations" else "Explore a measurement", "Results below use the server's calculation, chart and evidence. Missing or unsupported data is reported by FarmPi.") {
                    OutlinedTextField(locationA, { locationA = it }, label = { Text(if (destination == "Compare") "Location A" else "Location (leave blank for farm)") }, modifier = Modifier.fillMaxWidth(), singleLine = true)
                    if (destination == "Compare") OutlinedTextField(locationB, { locationB = it }, label = { Text("Location B") }, modifier = Modifier.fillMaxWidth(), singleLine = true)
                    Text("Measurement", style = MaterialTheme.typography.labelLarge)
                    FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        listOf("Soil moisture", "Soil temperature", "Air temperature", "Humidity", "Light", "Pressure").forEach { name ->
                            FilterChip(selected = measurement == name, onClick = { measurement = name }, label = { Text(name) })
                        }
                    }
                    Text("Period", style = MaterialTheme.typography.labelLarge)
                    FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        listOf("1 day", "7 days").forEach { name -> FilterChip(selected = period == name, onClick = { period = name }, label = { Text(name) }) }
                    }
                    Text("1 month · 3 months · Custom — Coming later. Current history is limited to seven days.", style = MaterialTheme.typography.bodySmall)
                    Button(enabled = !loading && (destination == "History" || (locationA.isNotBlank() && locationB.isNotBlank() && !locationA.trim().equals(locationB.trim(), true))), onClick = {
                        query(if (destination == "Compare") "Compare $measurement between ${locationA.trim()} and ${locationB.trim()} over the last $period" else "Show a graph of $measurement ${if (locationA.isBlank()) "across the farm" else "for ${locationA.trim()}"} over the last $period")
                    }) { Text(if (destination == "Compare") "Show comparison" else "Show history") }
                }
            }
            "Alerts" -> {
                FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) { listOf("Active", "Acknowledged", "All").forEach { name -> FilterChip(selected = filter == name, onClick = { filter = name }, label = { Text(name) }) } }
                InfoCard("Alerts are coming later", "Persistent alerts and acknowledgement are not connected yet. This is not a statement that the farm has no alerts.") {
                    StatusChip("Prototype · Not available yet")
                    Text("Each alert will show its location, measurement or source, reason, time and state.")
                }
                InfoCard("Location thresholds", "Low and high limits per measurement are planned. Threshold editing is not available yet.") {
                    OutlinedButton(onClick = {}, enabled = false) { Text("Configure thresholds — Coming later") }
                }
            }
            "More" -> {
                listOf("History", "Nodes", "System Status").forEach { name -> InfoCard(name, when(name) { "Nodes" -> "Manage physical nodes and pending registration"; "History" -> "Explore recorded measurements and graphs"; else -> "Check server and service availability" }) { OutlinedButton(onClick = { navigate(name) }) { Text("Open $name") } } }
                InfoCard("Settings", "Text size, explanation, guidance and voice preferences") { OutlinedButton(onClick = openSettings) { Text("Open settings") } }
            }
            "System Status" -> {
                InfoCard("Is FarmPi working?", connection) {
                    Text("Last successful check: $checkedAt")
                    fun availability(key: String): String = health?.optJSONObject(key)?.let { if (it.optBoolean("available")) "Available" else "Unavailable" } ?: "Not checked"
                    StatusChip("Database · ${availability("database")}")
                    StatusChip("AI service · ${availability("llm")}")
                    if (health?.optJSONObject("database")?.optBoolean("available") == true && health.optJSONObject("llm")?.optBoolean("available") == false) Text("The database is available. AI explanations are unavailable; some natural-language requests may fail.")
                    Button(onClick = refresh) { Text("Try again") }
                    TextButton(onClick = { details = !details }) { Text(if (details) "Hide technical details" else "Technical details") }
                    if (details) Text(health?.toString(2) ?: "No current status response.", style = MaterialTheme.typography.bodySmall)
                }
                InfoCard("Connection help", "FarmPi connects automatically over the local FarmPi network. If it is unavailable, check that this device is on FarmLAN and that the FarmPi certificate is trusted.") {
                    Text("Application ${BuildConfig.VERSION_NAME} · Prototype")
                    Text("The server address is fixed by the local FarmPi installation and is not a user setting.")
                    Text("Sensor reporting totals and independent network diagnostics: Not available yet.")
                }
            }
        }
        if (loading) { LinearProgressIndicator(Modifier.fillMaxWidth()); Text("Retrieving verified FarmPi information…") }
        requestError?.let { InfoCard("Information unavailable", it) { Button(onClick = { query(requested) }) { Text("Try again") } } }
        result?.let { response ->
            InfoCard("FarmPi result", requested) {
                Text(response.answer, style = MaterialTheme.typography.bodyLarge)
                StatusChip(sourceLabel(response.sourceCategory))
                Text("Response received: $receivedAt · Reading times are shown in the evidence.", style = MaterialTheme.typography.bodySmall)
                response.chart?.let { chart -> EnhancedChartCard(chart.title, chart.unit, chart.period, chart.provenance, chart.type, chart.series.map { (name, points) -> GraphSeries(name, points.map { GraphPoint(it.label, it.value) }) }) }
                EvidenceSummary(response.evidence)
                if (response.provenance.isNotEmpty()) {
                    Text("Sources", style = MaterialTheme.typography.titleSmall)
                    response.provenance.forEach { Text(it, style = MaterialTheme.typography.bodySmall) }
                }
                OutlinedButton(onClick = { ask(requested) }) { Text("Discuss in Ask FarmPi") }
            }
        }
    }
}

internal fun sourceLabel(category: String): String = when (category) {
    "observational" -> "Farm data"
    "calculated" -> "Calculated by FarmPi"
    "authoritative", "educational" -> "Reviewed information"
    "general" -> "General information"
    "combined" -> "Combined sources — inspect evidence"
    else -> "Source not provided"
}

@Composable
internal fun EvidenceSummary(evidence: List<String>) {
    if (evidence.isEmpty()) return
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text("Reading evidence", style = MaterialTheme.typography.titleSmall)
        Text("Timestamps are supplied by FarmPi in UTC. Freshness is described in the answer; a new response does not make an old reading current.", style = MaterialTheme.typography.bodySmall)
        evidence.take(24).forEach { raw ->
            val item = runCatching { JSONObject(raw) }.getOrNull()
            if (item == null) Text(raw, style = MaterialTheme.typography.bodySmall)
            else Surface(shape = MaterialTheme.shapes.medium, color = MaterialTheme.colorScheme.surfaceVariant) {
                Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text(item.optString("paddock", "Farm"), fontWeight = FontWeight.SemiBold)
                    Text("Observed / recorded: ${item.optString("timestamp", "Not provided")} UTC", style = MaterialTheme.typography.bodySmall)
                    if (!item.isNull("sensor")) Text("Source: ${item.optString("sensor")}", style = MaterialTheme.typography.bodySmall)
                    if (item.optBoolean("simulated")) StatusChip("Simulated")
                }
            }
        }
    }
}


@Composable
internal fun PreviousExchange(prompt: String, response: AskResult) {
    var expanded by remember(prompt, response) { mutableStateOf(false) }
    Column(Modifier.fillMaxWidth().padding(bottom = 16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Surface(Modifier.fillMaxWidth(.88f).align(androidx.compose.ui.Alignment.End), shape = MaterialTheme.shapes.medium, color = MaterialTheme.colorScheme.primaryContainer) {
            Text(prompt, Modifier.padding(16.dp))
        }
        Card(Modifier.fillMaxWidth(), colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)) {
            Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("FarmPi · Previous response", style = MaterialTheme.typography.labelLarge)
                Text(response.answer)
                StatusChip(sourceLabel(response.sourceCategory))
                TextButton(onClick = { expanded = !expanded }) { Text(if (expanded) "Hide supporting information" else "Sources and chart") }
                if (expanded) {
                    response.chart?.let { chart -> EnhancedChartCard(chart.title, chart.unit, chart.period, chart.provenance, chart.type, chart.series.map { (name, points) -> GraphSeries(name, points.map { GraphPoint(it.label, it.value) }) }) }
                    EvidenceSummary(response.evidence)
                    response.provenance.forEach { Text(it, style = MaterialTheme.typography.bodySmall) }
                }
            }
        }
    }
}
