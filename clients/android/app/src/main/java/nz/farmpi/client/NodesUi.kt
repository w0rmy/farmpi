package nz.farmpi.client

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.launch
import org.json.JSONArray
import org.json.JSONObject

@Composable
internal fun NodesArea(modifier: Modifier = Modifier) {
    val scope = rememberCoroutineScope()
    // Session-only: never persist or log administrator credentials.
    var token by remember { mutableStateOf("") }
    var data by remember { mutableStateOf<JSONObject?>(null) }
    var error by remember { mutableStateOf<String?>(null) }
    var busy by remember { mutableStateOf(false) }
    var selectedId by remember { mutableStateOf<Int?>(null) }
    var pending by remember { mutableStateOf(false) }

    androidx.activity.compose.BackHandler(enabled = selectedId != null) { selectedId = null }

    fun refresh() {
        scope.launch {
            busy = true
            try {
                data = fetchNodes(token)
                error = null
            } catch (e: Exception) {
                data = null
                error = e.message ?: "Unable to load nodes."
            } finally {
                busy = false
            }
        }
    }

    Column(
        modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Text(if (selectedId == null) "Nodes" else "Node Detail", style = MaterialTheme.typography.headlineMedium)
        if (selectedId != null) {
            TextButton(onClick = { selectedId = null }, enabled = !busy) { Text("Back to nodes") }
        }

        if (selectedId == null) {
            OutlinedTextField(
                value = token,
                onValueChange = { token = it; data = null },
                label = { Text("Administrator token") },
                visualTransformation = PasswordVisualTransformation(),
                singleLine = true,
                enabled = !busy,
                modifier = Modifier.fillMaxWidth()
            )
            Button(onClick = { refresh() }, enabled = !busy && token.isNotBlank()) {
                Text(if (busy) "Updating…" else "Refresh nodes")
            }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                FilterChip(selected = !pending, onClick = { pending = false }, label = { Text("Registered") })
                FilterChip(selected = pending, onClick = { pending = true }, label = { Text("Pending nodes") })
            }
            if (pending) {
                Text("Power on a new node, refresh, then open its card to approve it. Give it a friendly name and assign any farmer-defined location. Sensor modes start OFF.")
            }
        }

        error?.let { Text(it, color = MaterialTheme.colorScheme.error) }

        data?.let { response ->
            val nodes = response.getJSONArray("nodes")
            val all = (0 until nodes.length()).map { nodes.getJSONObject(it) }
            val selected = all.firstOrNull { it.getInt("id") == selectedId }

            if (selectedId != null && selected != null) {
                key(selected.getInt("id"), selected.toString()) {
                    NodeDetail(
                        node = selected,
                        locations = response.getJSONArray("locations"),
                        busy = busy,
                        createLocation = { locationName ->
                            scope.launch {
                                busy = true
                                try {
                                    createManagedLocation(token, locationName)
                                    data = fetchNodes(token)
                                    error = null
                                } catch (e: Exception) {
                                    error = e.message ?: "Unable to create location."
                                } finally {
                                    busy = false
                                }
                            }
                        },
                        save = { body, approve ->
                            scope.launch {
                                busy = true
                                try {
                                    saveManagedNode(token, selected.getInt("id"), approve, body)
                                    data = fetchNodes(token)
                                    error = null
                                } catch (e: Exception) {
                                    error = e.message ?: "Unable to save node. Refresh before trying again."
                                } finally {
                                    busy = false
                                }
                            }
                        }
                    )
                }
                OutlinedButton(onClick = { refresh() }, enabled = !busy) { Text("Refresh node status") }
            } else {
                val visible = all.filter { it.getBoolean("registered") != pending }
                if (visible.isEmpty()) {
                    Text(if (pending) "No pending nodes in the latest response." else "No registered physical nodes in the latest response.")
                }
                visible.forEach { node ->
                    NodeListCard(node) { selectedId = node.getInt("id") }
                }
            }
        }
    }
}

@Composable
private fun NodeListCard(node: JSONObject, open: () -> Unit) {
    val registered = node.getBoolean("registered")
    val locationName = if (node.isNull("paddock_name")) "Unassigned location" else node.getString("paddock_name")
    Card(
        onClick = open,
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
    ) {
        Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text(
                if (registered) locationName else "New node detected",
                style = MaterialTheme.typography.titleLarge,
                fontWeight = FontWeight.SemiBold
            )
            if (registered) {
                Text(
                    "${node.optString("name", "Node")} · ${node.getString("node_uid")}",
                    style = MaterialTheme.typography.bodySmall
                )
            } else {
                Text("Hardware ${node.getString("hardware_uid")}", style = MaterialTheme.typography.bodySmall)
            }
            StatusChip(
                if (registered) node.getString("sync_state").lowercase().replaceFirstChar { it.uppercase() }
                else "Pending registration"
            )
            Text(
                "Last contact: ${if (node.isNull("last_seen")) "Never" else node.getString("last_seen") + " UTC"}",
                style = MaterialTheme.typography.bodySmall
            )
            Text("Open details and settings", style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.primary)
        }
    }
}

@Composable
private fun NodeDetail(
    node: JSONObject,
    locations: JSONArray,
    busy: Boolean,
    createLocation: (String) -> Unit,
    save: (JSONObject, Boolean) -> Unit
) {
    var name by remember { mutableStateOf(node.getString("name")) }
    var location by remember { mutableStateOf(if (node.isNull("paddock_id")) 0 else node.getInt("paddock_id")) }
    var newLocation by remember { mutableStateOf("") }
    val sensors = node.getJSONArray("sensors")
    val registered = node.getBoolean("registered")
    var technical by remember { mutableStateOf(false) }

    Card(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            val locationName = if (node.isNull("paddock_name")) "Unassigned location" else node.getString("paddock_name")
            Text(if (registered) locationName else "Unregistered node", style = MaterialTheme.typography.titleLarge)
            if (registered) Text("${node.getString("node_uid")} · ${node.optString("name", "Node")}", style = MaterialTheme.typography.bodyMedium)
            StatusChip(
                if (registered) node.getString("sync_state").lowercase().replaceFirstChar { it.uppercase() }
                else "Pending registration"
            )
            Text("Last contact: ${if (node.isNull("last_seen")) "Never" else node.getString("last_seen") + " UTC"}")

            OutlinedTextField(
                name,
                { name = it },
                label = { Text("Friendly node name") },
                supportingText = { Text("Hardware identity and FarmPi ID remain unchanged if this name changes.") },
                enabled = !busy,
                modifier = Modifier.fillMaxWidth()
            )

            Text("Assigned location", fontWeight = FontWeight.SemiBold)
            FilterChip(selected = location == 0, onClick = { location = 0 }, label = { Text("Unassigned") }, enabled = !busy)
            for (j in 0 until locations.length()) {
                val item = locations.getJSONObject(j)
                FilterChip(
                    selected = location == item.getInt("id"),
                    onClick = { location = item.getInt("id") },
                    label = { Text(item.getString("name")) },
                    enabled = !busy
                )
            }

            Text("Create a location", fontWeight = FontWeight.SemiBold)
            OutlinedTextField(
                newLocation,
                { newLocation = it },
                label = { Text("What do you call this location?") },
                supportingText = { Text("Examples: Bob's, Back Hill, Down by the Trough") },
                singleLine = true,
                enabled = !busy,
                modifier = Modifier.fillMaxWidth()
            )
            OutlinedButton(
                onClick = { createLocation(newLocation.trim()); newLocation = "" },
                enabled = !busy && newLocation.isNotBlank()
            ) { Text("Create location") }

            if (registered) {
                Text("Sensor modes", fontWeight = FontWeight.SemiBold)
                Text(
                    "OFF sends nothing. SIMULATED exercises the real telemetry path with test values. LIVE requires a supported physical sensor. Modes are managed from the FarmPi console.",
                    style = MaterialTheme.typography.bodySmall
                )
                for (j in 0 until sensors.length()) {
                    val item = sensors.getJSONObject(j)
                    Column(Modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Text(item.getString("label"))
                        if (!item.getBoolean("supported")) {
                            Text("Not supported by this firmware", style = MaterialTheme.typography.bodySmall)
                        } else {
                            Text("Mode: ${item.optString("mode", "OFF")}", style = MaterialTheme.typography.bodyMedium)
                            Text(item.optString("state"), style = MaterialTheme.typography.bodySmall)
                        }
                    }
                }
            }

            TextButton(onClick = { technical = !technical }) {
                Text(if (technical) "Hide technical details" else "Technical details")
            }
            if (technical) {
                Text("Hardware UID: ${node.getString("hardware_uid")}")
                Text("Firmware: ${node.optString("firmware_version", "Unknown")}")
                if (registered) {
                    Text("FarmPi ID: ${node.getString("node_uid")}")
                    Text(node.getString("sync_state"))
                    Text(
                        "Desired: ${node.optString("desired_fingerprint").take(8)} · Applied: ${
                            if (node.isNull("applied_fingerprint")) "Not applied" else node.getString("applied_fingerprint").take(8)
                        }"
                    )
                    if (node.getString("sync_state") == "UPDATE FAILED" && !node.isNull("config_error")) {
                        Text(node.getString("config_error"), color = MaterialTheme.colorScheme.error)
                    }
                }
            }

            Button(
                enabled = !busy && name.isNotBlank(),
                onClick = {
                    val body = JSONObject()
                        .put("name", name.trim())
                        .put("paddock_id", if (location == 0) JSONObject.NULL else location)
                    if (registered) {
                        body.put("expected_fingerprint", node.getString("desired_fingerprint"))
                    }
                    save(body, !registered)
                }
            ) {
                Text(if (registered) "Save node configuration" else "Register node with sensors off")
            }
        }
    }
}
