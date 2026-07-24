package com.k1lllagt.fileforge

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
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExposedDropdownMenuBox
import androidx.compose.material3.ExposedDropdownMenuDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.core.content.FileProvider
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File

/**
 * FileForge Android — a thin Compose UI over the shared Python engine, run
 * on-device via Chaquopy. Flow: pick a file -> choose an output format the
 * engine advertises -> convert off the main thread -> share the result.
 */
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        if (!Python.isStarted()) Python.start(AndroidPlatform(this))
        setContent {
            MaterialTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    ConverterScreen()
                }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ConverterScreen() {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val bridge = remember { Python.getInstance().getModule("ffbridge") }

    var sourceFile by remember { mutableStateOf<File?>(null) }
    var sourceName by remember { mutableStateOf("") }
    var targets by remember { mutableStateOf<List<String>>(emptyList()) }
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
        val t = bridge.callAttr("targets_for", ext).asList().map { it.toString() }
        targets = t
        selectedTarget = t.firstOrNull() ?: ""
        status = if (t.isEmpty()) "No conversions available for .$ext"
        else "${t.size} output format(s) available"
    }

    fun runConversion() {
        val src = sourceFile ?: return
        if (selectedTarget.isEmpty()) return
        busy = true
        status = "Converting…"
        scope.launch {
            try {
                val outName = src.nameWithoutExtension + "." + selectedTarget
                val outPath = File(context.cacheDir, outName).absolutePath
                val result = withContext(Dispatchers.IO) {
                    bridge.callAttr("convert", src.absolutePath, outPath).toString()
                }
                outputFile = File(result)
                status = "Done: ${outputFile?.name}"
            } catch (e: Exception) {
                status = "Error: ${e.message}"
            } finally {
                busy = false
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
        Text("FileForge", style = MaterialTheme.typography.headlineMedium)
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
                    targets.forEach { fmt ->
                        DropdownMenuItem(
                            text = { Text(fmt) },
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
