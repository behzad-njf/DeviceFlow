package ir.behzaaad.deviceflow.agent.service

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent

class WatchdogReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent?) {
        if (intent?.action != ACTION_TICK) return
        AgentKeepAlive.ensureRunning(context)
    }

    companion object {
        const val ACTION_TICK = "ir.behzaaad.deviceflow.agent.WATCHDOG_TICK"
    }
}
