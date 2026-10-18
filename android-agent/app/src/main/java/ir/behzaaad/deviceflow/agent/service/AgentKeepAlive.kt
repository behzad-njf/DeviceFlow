package ir.behzaaad.deviceflow.agent.service

import android.app.AlarmManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.SystemClock
import ir.behzaaad.deviceflow.agent.data.AgentPreferences

/**
 * Schedules a cheap repeating alarm so the foreground agent can be restarted
 * after OEM process kills even when START_STICKY is ignored.
 */
object AgentKeepAlive {
    private const val REQUEST_CODE = 7101
    private const val INTERVAL_MS = 15 * 60 * 1000L

    fun schedule(context: Context) {
        val prefs = AgentPreferences(context)
        if (!prefs.isPaired) {
            cancel(context)
            return
        }
        val am = context.getSystemService(AlarmManager::class.java) ?: return
        val pi = pendingIntent(context)
        val triggerAt = SystemClock.elapsedRealtime() + INTERVAL_MS
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            am.setAndAllowWhileIdle(AlarmManager.ELAPSED_REALTIME_WAKEUP, triggerAt, pi)
        } else {
            @Suppress("DEPRECATION")
            am.set(AlarmManager.ELAPSED_REALTIME_WAKEUP, triggerAt, pi)
        }
    }

    fun cancel(context: Context) {
        val am = context.getSystemService(AlarmManager::class.java) ?: return
        am.cancel(pendingIntent(context))
    }

    fun ensureRunning(context: Context) {
        val prefs = AgentPreferences(context)
        if (!prefs.isPaired) return
        if (!AgentService.isRunning()) {
            AgentService.start(context)
        }
        schedule(context)
    }

    private fun pendingIntent(context: Context): PendingIntent {
        val intent = Intent(context, WatchdogReceiver::class.java).setAction(WatchdogReceiver.ACTION_TICK)
        return PendingIntent.getBroadcast(
            context.applicationContext,
            REQUEST_CODE,
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
    }
}
