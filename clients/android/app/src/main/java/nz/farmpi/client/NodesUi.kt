package nz.farmpi.client

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.launch
import org.json.JSONObject

@Composable
internal fun NodesArea(modifier: Modifier = Modifier) {
    val scope = rememberCoroutineScope()
    var token by remember { mutableStateOf("") } // Session-only. Never persist or log.
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
                Text("Power on a new node, refresh, then open its card. Give it a friendly name and assign an existing or farmer-named location. All measurements start OFF.")
            }
        }

        error?.let { Text(it, color = MaterialTheme.colorScheme.error) }

        data?.let { response ->
            val nodes = response.getJSONArray("nodes")
            val all = (0 until nodes.length()).map { nodes.getJSONObject(it) }
            val selected = all.firstOrNull { it.getInt("id") == selectedId }

            if (selectedId != null && selected != null) {
                key(selected.getInt("id"), selected.toString()) {
                    NodeDetailCard(selected, response, busy) { body, approve ->
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
    val location = if (node.isNull("paddock_name")) "Unassigned location" else node.getString("paddock_name")
    Card(
        onClick = open,
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
    ) {
        Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text(if (registered) location else "New node detected", style = MaterialTheme.typography.titleMedium)
            if (registered) {
                Text(node.getString("node_uid") + " · " + node.getString("name"), style = MaterialTheme.typography.bodySmall)
            } else {
                Text(node.getString("hardware_uid"), style = MaterialTheme.typography.bodySmall)
            }
            StatusChip(
                if (registered) node.getString("sync_state").lowercase().replaceFirstChar { it.uppercase() }
                else "Pending registration"
            )
            val lastContact = if (node.isNull("last_seen")) "Never" else node.getString("last_seen") + " UTC"
            Text("Last contact: " + lastContact, style = MaterialTheme.typography.bodySmall)
            Text("Open details and settings", style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.primary)
        }
    }
}

@Composable
private fun NodeDetailCard(node: JSONObject, response: JSONObject, busy: Boolean, save: (JSONObject, Boolean) -> Unit) {
    val registered = node.getBoolean("registered")
    var name by remember { mutableStateOf(node.getString("name")) }
    var location by remember { mutableStateOf(if (node.isNull("paddock_id")) 0 else node.getInt("paddock_id")) }
    var newLocation by remember { mutableStateOf("") }
    var technical by remember { mutableStateOf(false) }

    val sensors = node.getJSONArray("sensors")
    var modes by remember {
        mutableStateOf(
            (0 until sensors.length())
                .map { sensors.getJSONObject(it) }
                .filter { it.getBoolean("supported") }
                .associate { item -> item.getString("key") to item.optString("mode", "OFF") }
        )
    }

    val locations = response.getJSONArray("locations")
    val displayLocation = if (node.isNull("paddock_name")) "Unassigned location" else node.getString("paddock_name")

    Card(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Text(if (registered) displayLocation else "Pending node", style = MaterialTheme.typography.titleLarge)
            if (registered) {
                Text(node.getString("node_uid") + " · " + name, style = MaterialTheme.typography.bodyMedium)
                StatusChip(node.getString("sync_state").lowercase().replaceFirstChar { it.uppercase() })
            } else {
                StatusChip("Pending registration")
            }

            val lastContact = if (node.isNull("last_seen")) "Never" else node.getString("last_seen") + " UTC"
            Text("Last contact: " + lastContact)

            OutlinedTextField(
                name,
                { name = it },
                label = { Text("Friendly node name") },
                supportingText = { Text("Example: Gate sensor or Weather post") },
                enabled = !busy,
                modifier = Modifier.fillMaxWidth()
            )

            Text("Assigned location", style = MaterialTheme.typography.titleSmall)
            Text("Use the farmer's normal name, such as Bob's or Down by the Trough.", style = MaterialTheme.typography.bodySmall)

            FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                FilterChip(
                    selected = location == 0 && newLocation.isBlank(),
                    onClick = { location = 0; newLocation = "" },
                    label = { Text("Unassigned") },
                    enabled = !busy
                )
                for (j in 0 until locations.length()) {
                    val item = locations.getJSONObject(j)
                    FilterChip(
                        selected = location == item.getInt("id") && newLocation.isBlank(),
                        onClick = { location = item.getInt("id"); newLocation = "" },
                        label = { Text(item.getString("name")) },
                        enabled = !busy
                    )
                }
            }

            OutlinedTextField(
                value = newLocation,
                onValueChange = { newLocation = it; if (it.isNotBlank()) location = 0 },
                label = { Text("Create / use location name") },
                supportingText = { Text("Leave blank to use the selected location above.") },
                singleLine = true,
                enabled = !busy,
                modifier = Modifier.fillMaxWidth()
            )

            if (registered) {
                HorizontalDivider()
                Text("Measurement modes", style = MaterialTheme.typography.titleSmall)
                Text(
                    "Source modes are configured from the FarmPi console during the prototype. This screen shows the current state only.",
                    style = MaterialTheme.typography.bodySmall
                )
                for (j in 0 until sensors.length()) {
                    val item = sensors.getJSONObject(j)
                    if (!item.getBoolean("supported")) continue
                    val mode = item.optString("mode", "OFF")
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        Column(Modifier.weight(1f)) {
                            Text(item.getString("label"))
                            Text(item.getString("state"), style = MaterialTheme.typography.bodySmall)
                        }
                        StatusChip(mode.lowercase().replaceFirstChar { it.uppercase() })
                    }
                }
                Text(
                    "OFF / SIMULATED / LIVE changes: use scripts/configure-node-modes on FarmPi.",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.primary
                )
            }

            TextButton(onClick = { technical = !technical }) {
                Text(if (technical) "Hide technical details" else "Technical details")
            }
            if (technical) {
                Text("Hardware UID: " + node.getString("hardware_uid"))
                Text("Firmware: " + node.optString("firmware_version", "Unknown"))
                if (registered) {
                    Text("Logical ID: " + node.getString("node_uid"))
                    Text("Desired: " + node.optString("desired_fingerprint").take(8))
                    val applied = if (node.isNull("applied_fingerprint")) "Not applied" else node.getString("applied_fingerprint").take(8)
                    Text("Applied: " + applied)
                    if (node.getString("sync_state") == "UPDATE FAILED" && !node.isNull("config_error")) {
                        Text(node.getString("config_error"), color = MaterialTheme.colorScheme.error)
                    }
                }
            }

            Button(
                enabled = !busy && name.isNotBlank(),
                onClick = {
                    val body = JSONObject().put("name", name.trim())
                    if (newLocation.isNotBlank()) body.put("location_name", newLocation.trim())
                    else body.put("paddock_id", if (location == 0) JSONObject.NULL else location)

                    if (registered) {
                        val modeObject = JSONObject()
                        modes.toSortedMap().forEach { entry -> modeObject.put(entry.key, entry.value) }
                        body.put("modes", modeObject)
                        body.put("expected_fingerprint", node.getString("desired_fingerprint"))
                    }
                    save(body, !registered)
                }
            ) {
                Text(if (registered) "Save configuration" else "Register node with all measurements OFF")
            }
        }
    }
}
