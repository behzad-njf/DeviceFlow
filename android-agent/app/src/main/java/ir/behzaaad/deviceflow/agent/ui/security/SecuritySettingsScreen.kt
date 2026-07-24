package ir.behzaaad.deviceflow.agent.ui.security

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import ir.behzaaad.deviceflow.agent.R
import ir.behzaaad.deviceflow.agent.data.AgentPreferences
import ir.behzaaad.deviceflow.agent.security.LauncherVisibility
import ir.behzaaad.deviceflow.agent.ui.components.SectionCard
import ir.behzaaad.deviceflow.agent.ui.components.StatusPill

@Composable
fun SecuritySettingsScreen(
    onLocked: () -> Unit,
    onBack: () -> Unit,
) {
    val context = LocalContext.current
    val prefs = remember { AgentPreferences(context) }
    var launcherHidden by remember { mutableStateOf(prefs.launcherHidden) }
    var passcodeSet by remember { mutableStateOf(prefs.passcodeSet) }
    var dialerCode by remember { mutableStateOf(prefs.dialerCode) }
    var dialerDraft by remember { mutableStateOf(prefs.dialerCode) }
    var currentPin by remember { mutableStateOf("") }
    var newPin by remember { mutableStateOf("") }
    var confirmPin by remember { mutableStateOf("") }
    var message by remember { mutableStateOf<String?>(null) }
    var error by remember { mutableStateOf<String?>(null) }

    fun refresh() {
        launcherHidden = prefs.launcherHidden
        passcodeSet = prefs.passcodeSet
        dialerCode = prefs.dialerCode
        dialerDraft = prefs.dialerCode
    }

    Surface(modifier = Modifier.fillMaxSize()) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            Text(
                text = stringResource(R.string.security_title),
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Bold,
            )
            Text(
                text = stringResource(R.string.security_subtitle),
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f),
            )

            SectionCard(title = stringResource(R.string.security_launcher_title)) {
                StatusPill(
                    label = if (launcherHidden) {
                        stringResource(R.string.security_launcher_hidden)
                    } else {
                        stringResource(R.string.security_launcher_visible)
                    },
                    ok = !launcherHidden,
                )
                Text(
                    text = stringResource(R.string.security_dialer_hint, dialerCode),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.65f),
                )
                OutlinedTextField(
                    value = dialerDraft,
                    onValueChange = { if (it.length <= 8 && it.all(Char::isDigit)) dialerDraft = it },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                    label = { Text(stringResource(R.string.security_dialer_code_label)) },
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                    supportingText = {
                        Text(stringResource(R.string.security_dialer_format, dialerDraft.ifBlank { dialerCode }))
                    },
                )
                OutlinedButton(
                    onClick = {
                        error = null
                        message = null
                        if (!prefs.setDialerCode(dialerDraft)) {
                            error = context.getString(R.string.security_dialer_invalid)
                            return@OutlinedButton
                        }
                        dialerCode = prefs.dialerCode
                        dialerDraft = dialerCode
                        message = context.getString(R.string.security_dialer_saved, dialerCode)
                    },
                    modifier = Modifier.fillMaxWidth(),
                    enabled = dialerDraft != dialerCode && dialerDraft.length in 3..8,
                ) {
                    Text(stringResource(R.string.security_dialer_save))
                }
                if (launcherHidden) {
                    Button(
                        onClick = {
                            prefs.launcherHidden = false
                            LauncherVisibility.setHidden(context, false)
                            refresh()
                            message = context.getString(R.string.security_launcher_shown_msg)
                            error = null
                        },
                        modifier = Modifier.fillMaxWidth(),
                    ) {
                        Text(stringResource(R.string.security_show_launcher))
                    }
                } else {
                    OutlinedButton(
                        onClick = {
                            prefs.launcherHidden = true
                            LauncherVisibility.setHidden(context, true)
                            refresh()
                            message = context.getString(
                                R.string.security_launcher_hidden_msg,
                                prefs.dialerCode,
                            )
                            error = null
                        },
                        modifier = Modifier.fillMaxWidth(),
                    ) {
                        Text(stringResource(R.string.security_hide_launcher))
                    }
                }
            }

            SectionCard(title = stringResource(R.string.security_passcode_title)) {
                StatusPill(
                    label = if (passcodeSet) {
                        stringResource(R.string.security_passcode_on)
                    } else {
                        stringResource(R.string.security_passcode_off)
                    },
                    ok = passcodeSet,
                )
                if (passcodeSet) {
                    OutlinedTextField(
                        value = currentPin,
                        onValueChange = { if (it.length <= 8 && it.all(Char::isDigit)) currentPin = it },
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true,
                        label = { Text(stringResource(R.string.security_current_passcode)) },
                        visualTransformation = PasswordVisualTransformation(),
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.NumberPassword),
                    )
                }
                OutlinedTextField(
                    value = newPin,
                    onValueChange = { if (it.length <= 8 && it.all(Char::isDigit)) newPin = it },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                    label = { Text(stringResource(R.string.security_new_passcode)) },
                    visualTransformation = PasswordVisualTransformation(),
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.NumberPassword),
                )
                OutlinedTextField(
                    value = confirmPin,
                    onValueChange = { if (it.length <= 8 && it.all(Char::isDigit)) confirmPin = it },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                    label = { Text(stringResource(R.string.security_confirm_passcode)) },
                    visualTransformation = PasswordVisualTransformation(),
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.NumberPassword),
                )
                Button(
                    onClick = {
                        error = null
                        message = null
                        if (passcodeSet && !prefs.verifyPasscode(currentPin)) {
                            error = context.getString(R.string.lock_wrong)
                            return@Button
                        }
                        if (newPin != confirmPin) {
                            error = context.getString(R.string.security_pin_mismatch)
                            return@Button
                        }
                        if (!prefs.setPasscode(newPin)) {
                            error = context.getString(R.string.security_pin_invalid)
                            return@Button
                        }
                        currentPin = ""
                        newPin = ""
                        confirmPin = ""
                        refresh()
                        message = context.getString(R.string.security_pin_saved)
                        onLocked()
                    },
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Text(
                        if (passcodeSet) {
                            stringResource(R.string.security_change_passcode)
                        } else {
                            stringResource(R.string.security_set_passcode)
                        },
                    )
                }
                if (passcodeSet) {
                    OutlinedButton(
                        onClick = {
                            prefs.lockUi()
                            onLocked()
                        },
                        modifier = Modifier.fillMaxWidth(),
                    ) {
                        Text(stringResource(R.string.security_lock_now))
                    }
                    OutlinedButton(
                        onClick = {
                            error = null
                            message = null
                            if (!prefs.verifyPasscode(currentPin)) {
                                error = context.getString(R.string.lock_wrong)
                                return@OutlinedButton
                            }
                            prefs.clearPasscode()
                            currentPin = ""
                            newPin = ""
                            confirmPin = ""
                            refresh()
                            message = context.getString(R.string.security_pin_cleared)
                        },
                        modifier = Modifier.fillMaxWidth(),
                    ) {
                        Text(stringResource(R.string.security_clear_passcode))
                    }
                }
            }

            message?.let {
                Text(text = it, color = MaterialTheme.colorScheme.primary)
            }
            error?.let {
                Text(text = it, color = MaterialTheme.colorScheme.error)
            }

            Button(onClick = onBack, modifier = Modifier.fillMaxWidth()) {
                Text(stringResource(R.string.action_back))
            }
        }
    }
}
