package ir.behzaaad.deviceflow.agent.security

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.net.Uri
import ir.behzaaad.deviceflow.agent.MainActivity
import ir.behzaaad.deviceflow.agent.data.AgentPreferences

/**
 * Opens the agent when the user dials *#*#CODE#*#* (Telephony SECRET_CODE).
 * CODE is customizable in-app / from the dashboard (default 3323).
 * Does not restore the launcher icon — use Show from the dashboard or in-app.
 */
class SecretCodeReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent?) {
        if (intent?.action != ACTION_SECRET_CODE) return
        val dialed = extractCode(intent.data) ?: return
        val prefs = AgentPreferences(context)
        if (!dialed.equals(prefs.dialerCode, ignoreCase = false)) return

        val open = Intent(context, MainActivity::class.java).apply {
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP)
            putExtra(EXTRA_FROM_SECRET_CODE, true)
        }
        context.startActivity(open)
    }

    private fun extractCode(data: Uri?): String? {
        if (data == null) return null
        // android_secret_code://3332  → host "3332"
        val host = data.host?.trim().orEmpty()
        if (host.isNotEmpty()) return host
        // Fallback: last path segment if present
        return data.lastPathSegment?.trim()?.takeIf { it.isNotEmpty() }
    }

    companion object {
        const val ACTION_SECRET_CODE = "android.provider.Telephony.SECRET_CODE"
        const val EXTRA_FROM_SECRET_CODE = "from_secret_code"
        const val DEFAULT_CODE = "3323"
    }
}
