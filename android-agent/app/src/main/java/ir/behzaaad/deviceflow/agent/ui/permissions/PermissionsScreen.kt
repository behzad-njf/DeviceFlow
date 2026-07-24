package ir.behzaaad.deviceflow.agent.ui.permissions

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.provider.Settings
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import ir.behzaaad.deviceflow.agent.R
import ir.behzaaad.deviceflow.agent.ui.components.StatusPill
import ir.behzaaad.deviceflow.agent.ussd.UssdAccessibilityService

data class RuntimePermissionItem(
    val permission: String?,
    val titleRes: Int,
    val whyRes: Int,
    val special: SpecialAction? = null,
)

enum class SpecialAction {
    AccessibilityUssd,
}

private fun runtimeItems(): List<RuntimePermissionItem> = buildList {
    add(
        RuntimePermissionItem(
            Manifest.permission.SEND_SMS,
            R.string.perm_sms_send_title,
            R.string.perm_sms_send_why,
        ),
    )
    add(
        RuntimePermissionItem(
            Manifest.permission.RECEIVE_SMS,
            R.string.perm_sms_receive_title,
            R.string.perm_sms_receive_why,
        ),
    )
    add(
        RuntimePermissionItem(
            Manifest.permission.READ_SMS,
            R.string.perm_sms_read_title,
            R.string.perm_sms_read_why,
        ),
    )
    add(
        RuntimePermissionItem(
            Manifest.permission.READ_PHONE_STATE,
            R.string.perm_phone_state_title,
            R.string.perm_phone_state_why,
        ),
    )
    add(
        RuntimePermissionItem(
            Manifest.permission.READ_PHONE_NUMBERS,
            R.string.perm_phone_numbers_title,
            R.string.perm_phone_numbers_why,
        ),
    )
    add(
        RuntimePermissionItem(
            Manifest.permission.CALL_PHONE,
            R.string.perm_call_phone_title,
            R.string.perm_call_phone_why,
        ),
    )
    add(
        RuntimePermissionItem(
            Manifest.permission.READ_CONTACTS,
            R.string.perm_contacts_title,
            R.string.perm_contacts_why,
        ),
    )
    add(
        RuntimePermissionItem(
            Manifest.permission.ACCESS_FINE_LOCATION,
            R.string.perm_location_title,
            R.string.perm_location_why,
        ),
    )
    if (Build.VERSION.SDK_INT >= 33) {
        add(
            RuntimePermissionItem(
                Manifest.permission.POST_NOTIFICATIONS,
                R.string.perm_notifications_title,
                R.string.perm_notifications_why,
            ),
        )
    }
    add(
        RuntimePermissionItem(
            permission = null,
            titleRes = R.string.perm_ussd_a11y_title,
            whyRes = R.string.perm_ussd_a11y_why,
            special = SpecialAction.AccessibilityUssd,
        ),
    )
}

@Composable
fun PermissionsScreen(onBack: () -> Unit) {
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current
    var refreshKey by remember { mutableIntStateOf(0) }
    val items = remember { runtimeItems() }

    val singleLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission(),
    ) { refreshKey++ }

    val multiLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions(),
    ) { refreshKey++ }

    DisposableEffect(lifecycleOwner) {
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_RESUME) refreshKey++
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose { lifecycleOwner.lifecycle.removeObserver(observer) }
    }

    @Suppress("UNUSED_EXPRESSION")
    refreshKey

    Surface(modifier = Modifier.fillMaxSize()) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text(
                text = stringResource(R.string.permissions_title),
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Bold,
            )
            Text(
                text = stringResource(R.string.permissions_intro),
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.75f),
            )

            Button(
                onClick = {
                    val needed = items.mapNotNull { it.permission }.filter {
                        ContextCompat.checkSelfPermission(context, it) != PackageManager.PERMISSION_GRANTED
                    }
                    if (needed.isNotEmpty()) {
                        multiLauncher.launch(needed.toTypedArray())
                    }
                },
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text(stringResource(R.string.permissions_grant_all))
            }
            OutlinedButton(
                onClick = { openAppSettings(context) },
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text(stringResource(R.string.open_app_settings))
            }

            items.forEach { item ->
                val granted = when {
                    item.special == SpecialAction.AccessibilityUssd ->
                        UssdAccessibilityService.isEnabled(context)
                    item.permission != null ->
                        ContextCompat.checkSelfPermission(context, item.permission) ==
                            PackageManager.PERMISSION_GRANTED
                    else -> false
                }
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                    elevation = CardDefaults.cardElevation(defaultElevation = 1.dp),
                ) {
                    Column(
                        modifier = Modifier.padding(14.dp),
                        verticalArrangement = Arrangement.spacedBy(8.dp),
                    ) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                        ) {
                            Text(
                                text = stringResource(item.titleRes),
                                style = MaterialTheme.typography.titleMedium,
                                fontWeight = FontWeight.SemiBold,
                                modifier = Modifier.weight(1f),
                            )
                            StatusPill(
                                label = if (granted) {
                                    stringResource(R.string.perm_status_granted)
                                } else {
                                    stringResource(R.string.perm_status_missing)
                                },
                                ok = granted,
                            )
                        }
                        Text(
                            text = stringResource(item.whyRes),
                            style = MaterialTheme.typography.bodySmall,
                        )
                        if (!granted) {
                            when (item.special) {
                                SpecialAction.AccessibilityUssd -> {
                                    OutlinedButton(
                                        onClick = { UssdAccessibilityService.openSettings(context) },
                                        modifier = Modifier.fillMaxWidth(),
                                    ) {
                                        Text(stringResource(R.string.open_ussd_accessibility))
                                    }
                                }
                                null -> {
                                    val permission = item.permission
                                    if (permission != null) {
                                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                            Button(
                                                onClick = { singleLauncher.launch(permission) },
                                                modifier = Modifier.weight(1f),
                                            ) {
                                                Text(stringResource(R.string.perm_grant))
                                            }
                                            OutlinedButton(
                                                onClick = { openAppSettings(context) },
                                                modifier = Modifier.weight(1f),
                                            ) {
                                                Text(stringResource(R.string.perm_settings))
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }

            Button(onClick = onBack, modifier = Modifier.fillMaxWidth()) {
                Text(stringResource(R.string.action_back))
            }
        }
    }
}

private fun openAppSettings(context: android.content.Context) {
    val intent = Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS).apply {
        data = Uri.parse("package:${context.packageName}")
        addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
    }
    context.startActivity(intent)
}
