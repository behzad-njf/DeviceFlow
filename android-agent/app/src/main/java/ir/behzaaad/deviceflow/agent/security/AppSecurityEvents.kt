package ir.behzaaad.deviceflow.agent.security

import android.content.Context
import android.content.Intent
import androidx.core.content.ContextCompat

/**
 * Notifies the foreground UI when remote (or local) security prefs change
 * so lock/unlock can apply without waiting for ON_RESUME.
 */
object AppSecurityEvents {
    const val ACTION = "ir.behzaaad.deviceflow.agent.SECURITY_CHANGED"

    fun notifyChanged(context: Context) {
        val intent = Intent(ACTION).setPackage(context.packageName)
        context.sendBroadcast(intent)
    }

    fun register(
        context: Context,
        onChanged: () -> Unit,
    ): android.content.BroadcastReceiver {
        val receiver =
            object : android.content.BroadcastReceiver() {
                override fun onReceive(ctx: Context?, intent: Intent?) {
                    onChanged()
                }
            }
        ContextCompat.registerReceiver(
            context,
            receiver,
            android.content.IntentFilter(ACTION),
            ContextCompat.RECEIVER_NOT_EXPORTED,
        )
        return receiver
    }
}
