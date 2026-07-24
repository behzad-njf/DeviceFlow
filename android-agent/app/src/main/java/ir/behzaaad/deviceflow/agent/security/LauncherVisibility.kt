package ir.behzaaad.deviceflow.agent.security

import android.content.ComponentName
import android.content.Context
import android.content.pm.PackageManager
import ir.behzaaad.deviceflow.agent.data.AgentPreferences

/**
 * Toggles the launcher icon via activity-alias [ir.behzaaad.deviceflow.agent.LauncherAlias].
 * MainActivity itself stays launchable from notifications / secret dialer code.
 */
object LauncherVisibility {
    const val ALIAS_CLASS = "ir.behzaaad.deviceflow.agent.LauncherAlias"

    fun apply(context: Context, prefs: AgentPreferences) {
        setHidden(context, prefs.launcherHidden)
    }

    fun setHidden(context: Context, hidden: Boolean) {
        val pm = context.packageManager
        val component = ComponentName(context, ALIAS_CLASS)
        val newState =
            if (hidden) {
                PackageManager.COMPONENT_ENABLED_STATE_DISABLED
            } else {
                PackageManager.COMPONENT_ENABLED_STATE_ENABLED
            }
        pm.setComponentEnabledSetting(
            component,
            newState,
            PackageManager.DONT_KILL_APP,
        )
    }

    fun isHidden(context: Context): Boolean {
        val pm = context.packageManager
        val state = pm.getComponentEnabledSetting(ComponentName(context, ALIAS_CLASS))
        return when (state) {
            PackageManager.COMPONENT_ENABLED_STATE_DISABLED -> true
            PackageManager.COMPONENT_ENABLED_STATE_ENABLED -> false
            else -> false // default enabled in manifest
        }
    }
}
