package ir.behzaaad.deviceflow.agent.service

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import ir.behzaaad.deviceflow.agent.data.AgentPreferences

class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent?) {
        val action = intent?.action ?: return
        if (
            action != Intent.ACTION_BOOT_COMPLETED &&
            action != Intent.ACTION_LOCKED_BOOT_COMPLETED &&
            action != "android.intent.action.QUICKBOOT_POWERON" &&
            action != "com.htc.intent.action.QUICKBOOT_POWERON"
        ) {
            return
        }
        val prefs = AgentPreferences(context)
        if (!prefs.isPaired) return
        AgentService.start(context)
        AgentKeepAlive.schedule(context)
    }
}
