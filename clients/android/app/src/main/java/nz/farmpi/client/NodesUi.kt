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
import org.json.JSONArray
import org.json.JSONObject

@Composable
internal fun NodesArea(modifier: Modifier = Modifier) {
    val scope = rememberCoroutineScope()
    // Deliberately session-only; never store the administrative credential in
    // plain SharedPreferences, build settings or diagnostic output.
    var token by remember { mutableStateOf("") }
    var data by remember { mutableStateOf<JSONObject?>(null) }
    var error by remember { mutableStateOf<String?>(null) }
    var busy by remember { mutableStateOf(false) }
    fun refresh() { scope.launch {
        busy = true
        try { data = fetchNodes(token); error = null }
        catch (e: Exception) { error = e.message ?: "Unable to load nodes." }
        finally { busy = false }
    } }
    Column(modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text("FarmPi nodes", style = MaterialTheme.typography.headlineSmall)
        OutlinedTextField(value = token, onValueChange = { token = it; data = null }, label = { Text("Administrator token") }, visualTransformation = PasswordVisualTransformation(), singleLine = true)
        Button(onClick = { refresh() }, enabled = !busy && token.isNotBlank()) { Text(if (busy) "Updating…" else "Refresh nodes") }
        error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
        data?.let { response ->
            val nodes = response.getJSONArray("nodes")
            if (nodes.length() == 0) Text("No physical nodes detected yet. Power on an ESP32-S3 and refresh.")
            for (i in 0 until nodes.length()) {
                val node = nodes.getJSONObject(i)
                key(node.getInt("id"), node.toString()) {
                    NodeCard(node, response.getJSONArray("locations"), busy) { body, approve -> scope.launch {
                        busy = true
                        try { saveManagedNode(token, node.getInt("id"), approve, body); data = fetchNodes(token); error = null }
                        catch (e: Exception) { error = e.message ?: "Unable to save node." }
                        finally { busy = false }
                    } }
                }
            }
        }
    }
}

@Composable
private fun NodeCard(node: JSONObject, locations: JSONArray, busy: Boolean, save: (JSONObject, Boolean) -> Unit) {
    var name by remember { mutableStateOf(node.getString("name")) }
    var location by remember { mutableStateOf(if (node.isNull("paddock_id")) 0 else node.getInt("paddock_id")) }
    val sensors = node.getJSONArray("sensors")
    var enabled by remember { mutableStateOf((0 until sensors.length()).map { sensors.getJSONObject(it) }.filter { it.getBoolean("enabled") }.map { it.getString("key") }.toSet()) }
    val registered = node.getBoolean("registered")
    Card(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(if (registered) node.getString("node_uid") else "Unregistered node", style = MaterialTheme.typography.titleMedium)
            Text("Hardware: ${node.getString("hardware_uid")}")
            Text("Firmware: ${node.optString("firmware_version", "Unknown")}")
            Text("Last seen: ${if (node.isNull("last_seen")) "Never" else node.getString("last_seen") + " UTC"}")
            if (registered) {
                Text(node.getString("sync_state"))
                Text("Desired: ${node.optString("desired_fingerprint").take(8)} · Applied: ${if (node.isNull("applied_fingerprint")) "Not applied" else node.getString("applied_fingerprint").take(8)}")
                if (node.getString("sync_state") == "UPDATE FAILED" && !node.isNull("config_error")) Text(node.getString("config_error"), color = MaterialTheme.colorScheme.error)
            }
            OutlinedTextField(name, { name = it }, label = { Text("Node name") }, enabled = !busy)
            Text("Assigned location")
            FilterChip(selected = location == 0, onClick = { location = 0 }, label = { Text("Unassigned") }, enabled = !busy)
            for (j in 0 until locations.length()) {
                val item = locations.getJSONObject(j)
                FilterChip(selected = location == item.getInt("id"), onClick = { location = item.getInt("id") }, label = { Text(item.getString("name")) }, enabled = !busy)
            }
            if (registered) for (j in 0 until sensors.length()) {
                val item = sensors.getJSONObject(j)
                val id = item.getString("key")
                Row(Modifier.fillMaxWidth()) {
                    Checkbox(checked = id in enabled, onCheckedChange = { checked -> enabled = if (checked) enabled + id else enabled - id }, enabled = !busy && item.getBoolean("supported"))
                    Column {
                        Text(item.getString("label"))
                        Text(if (item.getBoolean("supported")) item.getString("state") else "Not supported by this firmware", style = MaterialTheme.typography.bodySmall)
                    }
                }
            }
            Button(enabled = !busy && name.isNotBlank(), onClick = {
                val body = JSONObject().put("name", name.trim()).put("paddock_id", if (location == 0) JSONObject.NULL else location)
                if (registered) body.put("enabled", JSONArray(enabled.sorted())).put("expected_fingerprint", node.getString("desired_fingerprint"))
                save(body, !registered)
            }) { Text(if (registered) "Save configuration" else "Register with all sensors disabled") }
        }
    }
}
