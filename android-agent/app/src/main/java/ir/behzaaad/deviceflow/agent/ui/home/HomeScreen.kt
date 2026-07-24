package ir.behzaaad.deviceflow.agent.ui.home

import android.os.SystemClock
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material3.Button
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import ir.behzaaad.deviceflow.agent.BuildConfig
import ir.behzaaad.deviceflow.agent.R
import ir.behzaaad.deviceflow.agent.data.AgentPreferences
import ir.behzaaad.deviceflow.agent.data.LocalMessage
import ir.behzaaad.deviceflow.agent.service.AgentService
import ir.behzaaad.deviceflow.agent.ui.components.SectionCard
import ir.behzaaad.deviceflow.agent.ui.components.StatTile
import ir.behzaaad.deviceflow.agent.ui.components.StatusPill
import java.text.DateFormat
import java.util.Date

@Composable
fun HomeScreen(
    onOpenPermissions: () -> Unit,
    onOpenBattery: () -> Unit,
    onOpenHelp: () -> Unit,
    onOpenMessages: () -> Unit,
    onOpenSecurity: () -> Unit,
    onLockNow: () -> Unit,
    onUnpair: () -> Unit,
) {
    val context = LocalContext.current
    val prefs = remember { AgentPreferences(context) }
    val lifecycleOwner = LocalLifecycleOwner.current
    var tick by remember { mutableLongStateOf(0L) }
    var serviceRunning by remember { mutableStateOf(AgentService.isRunning()) }
    var messages by remember { mutableStateOf(prefs.recentMessages()) }
    var passcodeSet by remember { mutableStateOf(prefs.passcodeSet) }

    DisposableEffect(lifecycleOwner) {
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_RESUME) {
                tick = SystemClock.elapsedRealtime()
                serviceRunning = AgentService.isRunning()
                messages = prefs.recentMessages()
                passcodeSet = prefs.passcodeSet
            }
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose { lifecycleOwner.lifecycle.removeObserver(observer) }
    }

    @Suppress("UNUSED_EXPRESSION")
    tick

    val hbAgeMs = System.currentTimeMillis() - prefs.lastHeartbeatAtMs
    val syncedRecently = prefs.lastHeartbeatOk && prefs.lastHeartbeatAtMs > 0 && hbAgeMs < 20_000
    val online = serviceRunning && syncedRecently

    Surface(modifier = Modifier.fillMaxSize()) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = prefs.deviceName ?: stringResource(R.string.home_title),
                        style = MaterialTheme.typography.headlineSmall,
                        fontWeight = FontWeight.Bold,
                    )
                    Text(
                        text = stringResource(R.string.home_subtitle, BuildConfig.VERSION_NAME),
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f),
                    )
                }
                IconButton(
                    onClick = {
                        if (prefs.passcodeSet) {
                            prefs.lockUi()
                            onLockNow()
                        } else {
                            onOpenSecurity()
                        }
                    },
                ) {
                    Icon(
                        imageVector = Icons.Filled.Lock,
                        contentDescription = stringResource(
                            if (passcodeSet) R.string.home_lock_cd else R.string.home_lock_setup_cd,
                        ),
                        tint = if (passcodeSet) {
                            MaterialTheme.colorScheme.primary
                        } else {
                            MaterialTheme.colorScheme.onSurface.copy(alpha = 0.45f)
                        },
                    )
                }
            }

            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                StatusPill(
                    label = if (online) {
                        stringResource(R.string.status_online)
                    } else if (serviceRunning) {
                        stringResource(R.string.status_service_on)
                    } else {
                        stringResource(R.string.status_offline)
                    },
                    ok = online || serviceRunning,
                )
                StatusPill(
                    label = if (syncedRecently) {
                        stringResource(R.string.status_synced)
                    } else {
                        stringResource(R.string.status_not_synced)
                    },
                    ok = syncedRecently,
                )
            }

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(10.dp),
            ) {
                StatTile(
                    title = stringResource(R.string.stat_sent),
                    value = prefs.smsSentCount.toString(),
                    modifier = Modifier.weight(1f),
                )
                StatTile(
                    title = stringResource(R.string.stat_failed),
                    value = prefs.smsFailedCount.toString(),
                    modifier = Modifier.weight(1f),
                )
                StatTile(
                    title = stringResource(R.string.stat_received),
                    value = prefs.smsReceivedCount.toString(),
                    modifier = Modifier.weight(1f),
                )
            }

            SectionCard(title = stringResource(R.string.home_service_title)) {
                Text(
                    text = if (serviceRunning) {
                        stringResource(R.string.home_service_running)
                    } else {
                        stringResource(R.string.home_service_stopped)
                    },
                    style = MaterialTheme.typography.bodyMedium,
                )
                if (prefs.lastHeartbeatAtMs > 0) {
                    Text(
                        text = stringResource(
                            R.string.home_last_sync,
                            DateFormat.getDateTimeInstance(DateFormat.SHORT, DateFormat.MEDIUM)
                                .format(Date(prefs.lastHeartbeatAtMs)),
                        ),
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.65f),
                    )
                }
                if (!prefs.lastHeartbeatOk && prefs.lastSyncError.isNotBlank()) {
                    Text(
                        text = prefs.lastSyncError,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.error,
                    )
                }
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    if (serviceRunning) {
                        OutlinedButton(
                            onClick = {
                                AgentService.stop(context)
                                serviceRunning = false
                            },
                            modifier = Modifier.weight(1f),
                        ) {
                            Text(stringResource(R.string.stop_agent))
                        }
                    } else {
                        Button(
                            onClick = {
                                AgentService.start(context)
                                serviceRunning = true
                            },
                            modifier = Modifier.weight(1f),
                        ) {
                            Text(stringResource(R.string.start_agent))
                        }
                    }
                    OutlinedButton(
                        onClick = {
                            tick = SystemClock.elapsedRealtime()
                            serviceRunning = AgentService.isRunning()
                            messages = prefs.recentMessages()
                        },
                        modifier = Modifier.weight(1f),
                    ) {
                        Text(stringResource(R.string.refresh_status))
                    }
                }
            }

            SectionCard(title = stringResource(R.string.home_recent_title)) {
                if (messages.isEmpty()) {
                    Text(
                        text = stringResource(R.string.home_recent_empty),
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.65f),
                    )
                } else {
                    messages.forEach { msg ->
                        MessageRow(msg)
                        Spacer(modifier = Modifier.height(6.dp))
                    }
                }
                OutlinedButton(onClick = onOpenMessages, modifier = Modifier.fillMaxWidth()) {
                    Text(stringResource(R.string.nav_messages))
                }
            }

            SectionCard(title = stringResource(R.string.home_setup_title)) {
                OutlinedButton(onClick = onOpenSecurity, modifier = Modifier.fillMaxWidth()) {
                    Text(stringResource(R.string.nav_security))
                }
                OutlinedButton(onClick = onOpenPermissions, modifier = Modifier.fillMaxWidth()) {
                    Text(stringResource(R.string.nav_permissions))
                }
                OutlinedButton(onClick = onOpenBattery, modifier = Modifier.fillMaxWidth()) {
                    Text(stringResource(R.string.nav_battery))
                }
                OutlinedButton(onClick = onOpenHelp, modifier = Modifier.fillMaxWidth()) {
                    Text(stringResource(R.string.nav_help))
                }
                OutlinedButton(
                    onClick = {
                        AgentService.stop(context)
                        prefs.clearPairing()
                        onUnpair()
                    },
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Text(stringResource(R.string.unpair))
                }
            }
        }
    }
}

@Composable
private fun MessageRow(message: LocalMessage) {
    val dir = if (message.direction == "in") {
        stringResource(R.string.msg_in)
    } else {
        stringResource(R.string.msg_out)
    }
    val whenText = DateFormat.getTimeInstance(DateFormat.SHORT).format(Date(message.atMs))
    Column(modifier = Modifier.fillMaxWidth()) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
        ) {
            Text(
                text = "$dir · ${message.peer}",
                style = MaterialTheme.typography.labelLarge,
                fontWeight = FontWeight.SemiBold,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
                modifier = Modifier.weight(1f),
            )
            Text(
                text = "${message.status} · $whenText",
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f),
            )
        }
        Text(
            text = message.body.ifBlank { "—" },
            style = MaterialTheme.typography.bodySmall,
            maxLines = 2,
            overflow = TextOverflow.Ellipsis,
            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.8f),
        )
    }
}
