package com.k1lllagt.fileforge

import android.net.Uri
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform

/**
 * FileForge Android entry point (skeleton).
 *
 * Picks a file via the Storage Access Framework, offers the target formats the
 * shared Python engine advertises, and runs the conversion on-device through
 * Chaquopy. Cloud/OCR/batch are gated behind the Pro upsell (see CloudClient).
 */
class MainActivity : ComponentActivity() {

    private var sourceUri by mutableStateOf<Uri?>(null)
    private var status by mutableStateOf("Pick a file to begin")

    private val picker = registerForActivityResult(
        ActivityResultContracts.GetContent()
    ) { uri -> sourceUri = uri; status = uri?.let { "Selected: $it" } ?: "No file" }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        if (!Python.isStarted()) Python.start(AndroidPlatform(this))

        setContent {
            MaterialTheme {
                Column(Modifier.padding(24.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
                    Text("FileForge", style = MaterialTheme.typography.headlineMedium)
                    Button(onClick = { picker.launch("*/*") }) { Text("Choose file") }
                    Text(status)
                    Button(onClick = ::convert, enabled = sourceUri != null) { Text("Convert") }
                }
            }
        }
    }

    /** Runs the bundled `fileforge` package to convert the selected file. */
    private fun convert() {
        val py = Python.getInstance()
        val engine = py.getModule("fileforge.core.registry")
        // Real impl: copy content:// to a cache file, resolve the converter,
        // run it off the main thread via WorkManager, then share the result.
        status = "Converting… (engine loaded: ${engine != null})"
    }
}
