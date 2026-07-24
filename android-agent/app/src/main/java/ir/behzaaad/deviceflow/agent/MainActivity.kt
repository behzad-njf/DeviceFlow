package ir.behzaaad.deviceflow.agent

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.compose.ui.res.stringResource
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import ir.behzaaad.deviceflow.agent.data.AgentPreferences
import ir.behzaaad.deviceflow.agent.security.AppSecurityEvents
import ir.behzaaad.deviceflow.agent.security.LauncherVisibility
import ir.behzaaad.deviceflow.agent.ui.battery.BatteryOptimizationScreen
import ir.behzaaad.deviceflow.agent.ui.help.HelpScreen
import ir.behzaaad.deviceflow.agent.ui.help.HelpTopic
import ir.behzaaad.deviceflow.agent.ui.help.HelpTopicScreen
import ir.behzaaad.deviceflow.agent.ui.home.HomeScreen
import ir.behzaaad.deviceflow.agent.ui.lock.LockScreen
import ir.behzaaad.deviceflow.agent.ui.messages.MessageHistoryScreen
import ir.behzaaad.deviceflow.agent.ui.pairing.PairingScreen
import ir.behzaaad.deviceflow.agent.ui.permissions.PermissionsScreen
import ir.behzaaad.deviceflow.agent.ui.security.SecuritySettingsScreen
import ir.behzaaad.deviceflow.agent.ui.theme.DeviceFlowTheme
import kotlinx.coroutines.delay

private sealed class AppScreen {
    data object Home : AppScreen()
    data object Pairing : AppScreen()
    data object Permissions : AppScreen()
    data object Battery : AppScreen()
    data object Help : AppScreen()
    data object Messages : AppScreen()
    data object Security : AppScreen()
    data class HelpDetail(val topic: HelpTopic) : AppScreen()
}

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        val prefsBootstrap = AgentPreferences(this)
        LauncherVisibility.apply(this, prefsBootstrap)
        setContent {
            DeviceFlowTheme {
                // Keep content clear of status bar + gesture/nav bar with edge-to-edge.
                Surface(
                    modifier = Modifier
                        .fillMaxSize()
                        .safeDrawingPadding(),
                ) {
                    val context = LocalContext.current
                    val prefs = remember { AgentPreferences(this) }
                    val lifecycleOwner = LocalLifecycleOwner.current
                    var screen by remember {
                        mutableStateOf<AppScreen>(
                            if (prefs.isPaired) AppScreen.Home else AppScreen.Pairing,
                        )
                    }
                    var locked by remember { mutableStateOf(prefs.uiLocked && prefs.passcodeSet) }
                    var showPermissionsIntro by remember {
                        mutableStateOf(!prefs.permissionsGuidePromptShown)
                    }
                    val canRequestPermissions = !showPermissionsIntro

                    fun refreshLockState() {
                        locked = prefs.uiLocked && prefs.passcodeSet
                    }

                    DisposableEffect(lifecycleOwner) {
                        val observer = LifecycleEventObserver { _, event ->
                            if (event == Lifecycle.Event.ON_RESUME) {
                                refreshLockState()
                            }
                        }
                        lifecycleOwner.lifecycle.addObserver(observer)
                        onDispose { lifecycleOwner.lifecycle.removeObserver(observer) }
                    }

                    // Remote lock/unlock from AgentService → prefs → broadcast.
                    DisposableEffect(Unit) {
                        val receiver = AppSecurityEvents.register(context) { refreshLockState() }
                        onDispose { context.unregisterReceiver(receiver) }
                    }

                    // Fallback poll so lock state never stays stale if a broadcast is missed.
                    LaunchedEffect(Unit) {
                        while (true) {
                            delay(750)
                            refreshLockState()
                        }
                    }

                    if (locked) {
                        LockScreen(
                            prefs = prefs,
                            onUnlocked = { locked = false },
                        )
                    } else {
                        when (val current = screen) {
                            AppScreen.Home ->
                                HomeScreen(
                                    onOpenPermissions = { screen = AppScreen.Permissions },
                                    onOpenBattery = { screen = AppScreen.Battery },
                                    onOpenHelp = { screen = AppScreen.Help },
                                    onOpenMessages = { screen = AppScreen.Messages },
                                    onOpenSecurity = { screen = AppScreen.Security },
                                    onLockNow = { locked = true },
                                    onUnpair = { screen = AppScreen.Pairing },
                                )
                            AppScreen.Pairing ->
                                PairingScreen(
                                    canRequestPermissions = canRequestPermissions,
                                    onPaired = { screen = AppScreen.Home },
                                    onOpenPermissions = { screen = AppScreen.Permissions },
                                    onOpenHelp = { screen = AppScreen.Help },
                                )
                            AppScreen.Permissions ->
                                PermissionsScreen(
                                    onBack = {
                                        screen = if (prefs.isPaired) AppScreen.Home else AppScreen.Pairing
                                    },
                                )
                            AppScreen.Battery ->
                                BatteryOptimizationScreen(
                                    onBack = { screen = AppScreen.Home },
                                )
                            AppScreen.Help ->
                                HelpScreen(
                                    onOpenTopic = { screen = AppScreen.HelpDetail(it) },
                                    onBack = {
                                        screen = if (prefs.isPaired) AppScreen.Home else AppScreen.Pairing
                                    },
                                )
                            AppScreen.Messages ->
                                MessageHistoryScreen(
                                    onBack = { screen = AppScreen.Home },
                                )
                            AppScreen.Security ->
                                SecuritySettingsScreen(
                                    onLocked = { locked = true },
                                    onBack = { screen = AppScreen.Home },
                                )
                            is AppScreen.HelpDetail ->
                                HelpTopicScreen(
                                    topic = current.topic,
                                    onBack = { screen = AppScreen.Help },
                                )
                        }
                    }

                    if (!locked && showPermissionsIntro) {
                        AlertDialog(
                            onDismissRequest = {
                                prefs.permissionsGuidePromptShown = true
                                showPermissionsIntro = false
                            },
                            title = { Text(stringResource(R.string.permissions_intro_title)) },
                            text = { Text(stringResource(R.string.permissions_intro_body)) },
                            confirmButton = {
                                TextButton(
                                    onClick = {
                                        prefs.permissionsGuidePromptShown = true
                                        showPermissionsIntro = false
                                        screen = AppScreen.Permissions
                                    },
                                ) {
                                    Text(stringResource(R.string.permissions_intro_read))
                                }
                            },
                            dismissButton = {
                                TextButton(
                                    onClick = {
                                        prefs.permissionsGuidePromptShown = true
                                        showPermissionsIntro = false
                                    },
                                ) {
                                    Text(stringResource(R.string.permissions_intro_later))
                                }
                            },
                        )
                    }
                }
            }
        }
    }
}
