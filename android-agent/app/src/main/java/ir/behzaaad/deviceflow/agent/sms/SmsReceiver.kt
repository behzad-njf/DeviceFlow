package ir.behzaaad.deviceflow.agent.sms

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.provider.Telephony
import ir.behzaaad.deviceflow.agent.data.AgentPreferences
import ir.behzaaad.deviceflow.agent.data.DeviceFlowApi
import org.json.JSONObject
import java.util.concurrent.Executors

class SmsReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != Telephony.Sms.Intents.SMS_RECEIVED_ACTION) return
        val prefs = AgentPreferences(context)
        val token = prefs.deviceToken ?: return
        val messages = Telephony.Sms.Intents.getMessagesFromIntent(intent) ?: return
        val from = messages.firstOrNull()?.displayOriginatingAddress ?: return
        val body = messages.joinToString(separator = "") { it.displayMessageBody ?: "" }
        val pending = goAsync()
        Executors.newSingleThreadExecutor().execute {
            try {
                val api = DeviceFlowApi(prefs.serverUrl, token)
                api.postInbound(
                    JSONObject()
                        .put("from", from)
                        .put("body", body)
                        .put("sim_slot", 1),
                )
                prefs.recordInbound(from, body)
            } catch (_: Exception) {
                // Inbound will be retried in a later phase via local queue.
            } finally {
                pending.finish()
            }
        }
    }
}
