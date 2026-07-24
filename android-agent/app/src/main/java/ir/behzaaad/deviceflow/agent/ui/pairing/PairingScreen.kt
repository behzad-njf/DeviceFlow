package ir.behzaaad.deviceflow.agent.ui.pairing

import android.Manifest
import android.content.pm.PackageManager
import android.os.Build
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import ir.behzaaad.deviceflow.agent.BuildConfig
import ir.behzaaad.deviceflow.agent.R
import ir.behzaaad.deviceflow.agent.data.AgentPreferences
import ir.behzaaad.deviceflow.agent.data.DeviceFlowApi
import ir.behzaaad.deviceflow.agent.device.DeviceHealth
import ir.behzaaad.deviceflow.agent.service.AgentService
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject

@Composable
fun PairingScreen(
    canRequestPermissions: Boolean = true,
    onPaired: () -> Unit = {},
    onOpenPermissions: () -> Unit = {},
    onOpenHelp: () -> Unit = {},
) {
    val context = LocalContext.current
    val prefs = remember { AgentPreferences(context) }
    val scope = rememberCoroutineScope()

    var serverUrl by rememberSaveable {
        mutableStateOf(
            prefs.serverUrl.removeSuffix("/api/v1").ifBlank { "http://10.0.2.2:8000" },
        )
    }
    var pairingCode by rememberSaveable { mutableStateOf("") }
    var status by rememberSaveable { mutableStateOf("") }
    var busy by remember { mutableStateOf(false) }

    val permissionLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions(),
    ) { }

    LaunchedEffect(canRequestPermissions) {
        if (!canRequestPermissions) return@LaunchedEffect
        val needed = buildList {
            add(Manifest.permission.SEND_SMS)
            add(Manifest.permission.RECEIVE_SMS)
            add(Manifest.permission.READ_SMS)
            add(Manifest.permission.READ_PHONE_STATE)
            add(Manifest.permission.READ_PHONE_NUMBERS)
            add(Manifest.permission.CALL_PHONE)
            add(Manifest.permission.READ_CONTACTS)
            add(Manifest.permission.ACCESS_COARSE_LOCATION)
            add(Manifest.permission.ACCESS_FINE_LOCATION)
            if (Build.VERSION.SDK_INT >= 33) add(Manifest.permission.POST_NOTIFICATIONS)
        }.filter {
            ContextCompat.checkSelfPermission(context, it) != PackageManager.PERMISSION_GRANTED
        }
        if (needed.isNotEmpty()) {
            permissionLauncher.launch(needed.toTypedArray())
        }
    }

    Surface(modifier = Modifier.fillMaxSize()) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(24.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            Text(
                text = stringResource(R.string.pairing_title),
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Bold,
            )
            Text(
                text = stringResource(R.string.pairing_subtitle),
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f),
            )
            OutlinedTextField(
                value = serverUrl,
                onValueChange = { serverUrl = it },
                modifier = Modifier.fillMaxWidth(),
                label = { Text(stringResource(R.string.server_url)) },
                singleLine = true,
            )
            OutlinedTextField(
                value = pairingCode,
                onValueChange = { pairingCode = it },
                modifier = Modifier.fillMaxWidth(),
                label = { Text(stringResource(R.string.pairing_code)) },
                singleLine = true,
            )
            Button(
                onClick = {
                    busy = true
                    status = context.getString(R.string.pairing_in_progress)
                    scope.launch {
                        try {
                            val apiBase = normalizeApiBase(serverUrl)
                            prefs.serverUrl = apiBase
                            val api = DeviceFlowApi(apiBase)
                            val snapshot = DeviceHealth.snapshot(context)
                            val info = JSONObject()
                                .put("agent_version", BuildConfig.VERSION_NAME)
                                .put("model", Build.MODEL)
                                .put("manufacturer", Build.MANUFACTURER)
                                .put("android_version", Build.VERSION.RELEASE)
                                .put("sims", snapshot.toHeartbeatExtras().getJSONArray("sims"))
                                .put("capabilities", JSONArray(AgentService.AGENT_CAPABILITIES))
                            val result = withContext(Dispatchers.IO) {
                                api.pair(pairingCode.trim(), info)
                            }
                            prefs.deviceToken = result.getString("device_token")
                            prefs.deviceId = result.getString("device_id")
                            prefs.deviceName = result.optString("name")
                            AgentService.start(context)
                            onPaired()
                        } catch (ex: Exception) {
                            status = context.getString(
                                R.string.pairing_failed,
                                ex.message ?: "error",
                            )
                        } finally {
                            busy = false
                        }
                    }
                },
                enabled = !busy && pairingCode.isNotBlank(),
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text(stringResource(R.string.pair_action))
            }
            OutlinedButton(onClick = onOpenPermissions, modifier = Modifier.fillMaxWidth()) {
                Text(stringResource(R.string.nav_permissions))
            }
            OutlinedButton(onClick = onOpenHelp, modifier = Modifier.fillMaxWidth()) {
                Text(stringResource(R.string.nav_help))
            }
            if (status.isNotBlank()) {
                Text(text = status, style = MaterialTheme.typography.bodySmall)
            }
        }
    }
}

private fun normalizeApiBase(raw: String): String {
    val trimmed = raw.trim().trimEnd('/')
    return if (trimmed.endsWith("/api/v1")) trimmed else "$trimmed/api/v1"
}
