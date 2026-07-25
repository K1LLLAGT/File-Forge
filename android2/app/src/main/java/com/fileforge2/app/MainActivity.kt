package com.fileforge2.app

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.provider.OpenableColumns
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Divider
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExposedDropdownMenuBox
import androidx.compose.material3.ExposedDropdownMenuDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Tab
import androidx.compose.material3.TabRow
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.unit.dp
import androidx.core.content.FileProvider
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * FileForge 2.0 (re-branded: com.fileforge2.app) — a Compose UI over the shared
 * Python engine via Chaquopy. Two tabs:
 *  - Convert: pick a file, pick a ranked output format (engine-supported first),
 *    convert off the main thread, share the result.
 *  - History: a persisted log of past conversions.
 *
 * Target formats come from the FileForge 2.0 suggestion layer
 * (`ffbridge.ranked_targets`), so engine-supported formats are offered ahead of
 * generic ones, which are shown but disabled.
 */
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        if (!Python.isStarted()) Python.start(AndroidPlatform(this))
        setContent {
            MaterialTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    AppScaffold()
                }
            }
        }
    }
}

/** A single conversion entry, persisted as JSON in filesDir/history.json. */
data class HistoryEntry(val source: String, val target: String, val ok: Boolean, val ts: String)

private const val HISTORY_FILE = "history.json"

private fun loadHistory(context: Context): List<HistoryEntry> {
    val f = File(context.filesDir, HISTORY_FILE)
    if (!f.exists()) return emptyList()
    return runCatching {
        val arr = JSONArray(f.readText())
        (0 until arr.length()).map { i ->
            val o = arr.getJSONObject(i)
            HistoryEntry(
                o.optString("source"), o.optString("target"),
                o.optBoolean("ok"), o.optString("ts"),
            )
        }
    }.getOrDefault(emptyList())
}

private fun appendHistory(context: Context, entry: HistoryEntry) {
    val f = File(context.filesDir, HISTORY_FILE)
    val arr = if (f.exists()) runCatching { JSONArray(f.readText()) }.getOrDefault(JSONArray())
    else JSONArray()
    arr.put(
        JSONObject()
            .put("source", entry.source)
            .put("target", entry.target)
            .put("ok", entry.ok)
            .put("ts", entry.ts)
    )
    f.writeText(arr.toString())
}

private fun clearHistory(context: Context) {
    File(context.filesDir, HISTORY_FILE).delete()
}

@Composable
fun AppScaffold() {
    val context = LocalContext.current
    var tab by remember { mutableStateOf(0) }
    val history = remember { mutableStateListOf<HistoryEntry>().apply { addAll(loadHistory(context)) } }

    Column(modifier = Modifier.fillMaxSize()) {
        TabRow(selectedTabIndex = tab) {
            Tab(selected = tab == 0, onClick = { tab = 0 }, text = { Text("Convert") })
            Tab(selected = tab == 1, onClick = { tab = 1 }, text = { Text("History") })
        }
        when (tab) {
            0 -> ConverterScreen(onConverted = { entry ->
                appendHistory(context, entry)
                history.add(entry)
            })
            else -> HistoryScreen(history) {
                clearHistory(context)
                history.clear()
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ConverterScreen(onConverted: (HistoryEntry) -> Unit) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val bridge = remember { Python.getInstance().getModule("ffbridge") }

    var sourceFile by remember { mutableStateOf<File?>(null) }
    var sourceName by remember { mutableStateOf("") }
    // targets: list of (label, supported)
    var targets by remember { mutableStateOf<List<Pair<String, Boolean>>>(emptyList()) }
    var selectedTarget by remember { mutableStateOf("") }
    var expanded by remember { mutableStateOf(false) }
    var status by remember { mutableStateOf("Pick a file to begin") }
    var busy by remember { mutableStateOf(false) }
    var outputFile by remember { mutableStateOf<File?>(null) }

    val picker = rememberLauncherForActivityResult(
        ActivityResultContracts.GetContent()
    ) { uri: Uri? ->
        outputFile = null
        if (uri == null) return@rememberLauncherForActivityResult
        val name = queryDisplayName(context, uri)
        val dest = File(context.cacheDir, name)
        context.contentResolver.openInputStream(uri)?.use { input ->
            dest.outputStream().use { input.copyTo(it) }
        }
        sourceFile = dest
        sourceName = name
        val ext = name.substringAfterLast('.', "")
        // Ranked target list from the FileForge 2.0 suggestion layer.
        // Each item is a [target, supported] pair.
        val ranked = bridge.callAttr("ranked_targets", ext).asList().map {
            val pair = it.asList()
            pair[0].toString() to pair[1].toBoolean()
        }
        targets = ranked
        val firstSupported = ranked.firstOrNull { it.second }?.first
        selectedTarget = firstSupported ?: ranked.firstOrNull()?.first ?: ""
        status = if (ranked.isEmpty()) "No conversions available for .$ext"
        else "${ranked.count { it.second }} engine format(s), ${ranked.count { !it.second }} more suggested"
    }

    fun runConversion() {
        val src = sourceFile ?: return
        if (selectedTarget.isEmpty()) return
        busy = true
        status = "Converting…"
        scope.launch {
            val outName = src.nameWithoutExtension + "." + selectedTarget
            var ok = false
            try {
                val outPath = File(context.cacheDir, outName).absolutePath
                val result = withContext(Dispatchers.IO) {
                    bridge.callAttr("convert", src.absolutePath, outPath).toString()
                }
                outputFile = File(result)
                ok = true
                status = "Done: ${outputFile?.name}"
            } catch (e: Exception) {
                status = "Error: ${e.message}"
            } finally {
                busy = false
                onConverted(
                    HistoryEntry(
                        source = sourceName,
                        target = outName,
                        ok = ok,
                        ts = SimpleDateFormat("yyyy-MM-dd HH:mm", Locale.US).format(Date()),
                    )
                )
            }
        }
    }

    fun shareOutput() {
        val f = outputFile ?: return
        val uri = FileProvider.getUriForFile(context, "${context.packageName}.fileprovider", f)
        val send = Intent(Intent.ACTION_SEND).apply {
            type = "*/*"
            putExtra(Intent.EXTRA_STREAM, uri)
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        }
        context.startActivity(Intent.createChooser(send, "Share converted file"))
    }

    Column(
        modifier = Modifier.fillMaxSize().padding(24.dp).verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        Text("FileForge 2.0", style = MaterialTheme.typography.headlineMedium)
        Text("Free file converter", style = MaterialTheme.typography.bodyMedium)

        Button(onClick = { picker.launch("*/*") }, enabled = !busy) {
            Text("Choose file")
        }
        if (sourceName.isNotEmpty()) Text("Selected: $sourceName")

        if (targets.isNotEmpty()) {
            ExposedDropdownMenuBox(
                expanded = expanded,
                onExpandedChange = { expanded = !expanded },
            ) {
                OutlinedTextField(
                    value = selectedTarget,
                    onValueChange = {},
                    readOnly = true,
                    label = { Text("Convert to") },
                    trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = expanded) },
                    modifier = Modifier.menuAnchor(),
                )
                ExposedDropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
                    targets.forEach { (fmt, supported) ->
                        DropdownMenuItem(
                            text = { Text(if (supported) fmt else "$fmt  (not supported yet)") },
                            enabled = supported,
                            onClick = { selectedTarget = fmt; expanded = false },
                        )
                    }
                }
            }
            Button(onClick = { runConversion() }, enabled = !busy && selectedTarget.isNotEmpty()) {
                Text(if (busy) "Working…" else "Convert")
            }
        }

        Text(status)

        if (outputFile != null) {
            Button(onClick = { shareOutput() }) { Text("Share result") }
        }
    }
}

@Composable
fun HistoryScreen(history: List<HistoryEntry>, onClear: () -> Unit) {
    Column(modifier = Modifier.fillMaxSize().padding(16.dp)) {
        Row {
            Text("Conversion history", style = MaterialTheme.typography.titleLarge)
        }
        if (history.isEmpty()) {
            Text("No conversions yet.", modifier = Modifier.padding(top = 12.dp))
            return
        }
        Button(onClick = onClear, modifier = Modifier.padding(vertical = 8.dp)) { Text("Clear") }
        LazyColumn(modifier = Modifier.fillMaxWidth()) {
            items(history.reversed()) { entry ->
                Column(modifier = Modifier.fillMaxWidth().padding(vertical = 6.dp)) {
                    Text(
                        "${entry.source}  →  ${entry.target}",
                        fontFamily = FontFamily.Monospace,
                        style = MaterialTheme.typography.bodyMedium,
                    )
                    Text(
                        "${entry.ts}   ${if (entry.ok) "✓ ok" else "✗ failed"}",
                        style = MaterialTheme.typography.bodySmall,
                    )
                    Divider(modifier = Modifier.padding(top = 6.dp))
                }
            }
        }
    }
}

@Composable
private fun Row(content: @Composable () -> Unit) {
    androidx.compose.foundation.layout.Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
    ) { content() }
}

private fun queryDisplayName(context: Context, uri: Uri): String {
    var name = "input"
    context.contentResolver.query(uri, null, null, null, null)?.use { cursor ->
        val idx = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
        if (idx >= 0 && cursor.moveToFirst()) {
            cursor.getString(idx)?.let { name = it }
        }
    }
    return name
}
