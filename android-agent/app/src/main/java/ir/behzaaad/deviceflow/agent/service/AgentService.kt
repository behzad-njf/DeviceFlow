package ir.behzaaad.deviceflow.agent.service

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.IBinder
import android.util.Log
import androidx.core.app.NotificationCompat
import androidx.core.content.ContextCompat
import ir.behzaaad.deviceflow.agent.BuildConfig
import ir.behzaaad.deviceflow.agent.MainActivity
import ir.behzaaad.deviceflow.agent.R
import ir.behzaaad.deviceflow.agent.data.AgentPreferences
import ir.behzaaad.deviceflow.agent.data.DeviceFlowApi
import ir.behzaaad.deviceflow.agent.device.DeviceHealth
import ir.behzaaad.deviceflow.agent.device.DeviceLocation
import ir.behzaaad.deviceflow.agent.security.LauncherVisibility
import ir.behzaaad.deviceflow.agent.sms.SmsSender
import ir.behzaaad.deviceflow.agent.ussd.UssdRunner
import org.json.JSONArray
import org.json.JSONObject
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicBoolean

class AgentService : Service() {
    private val executor = Executors.newSingleThreadExecutor()

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == ACTION_STOP) {
            stopSelf()
            return START_NOT_STICKY
        }
        startForeground(NOTIFICATION_ID, buildNotification(getString(R.string.notif_running)))
        DeviceLocation.start(this)
        val prefs = AgentPreferences(this)
        LauncherVisibility.apply(this, prefs)
        if (running.compareAndSet(false, true)) {
            executor.execute { loop() }
        }
        return START_STICKY
    }

    override fun onDestroy() {
        running.set(false)
        DeviceLocation.stop(this)
        super.onDestroy()
    }

    private fun loop() {
        val prefs = AgentPreferences(this)
        val sender = SmsSender(this)
        while (running.get()) {
            val token = prefs.deviceToken
            if (token.isNullOrBlank()) {
                Thread.sleep(3000)
                continue
            }
            try {
                val api = DeviceFlowApi(prefs.serverUrl, token)
                val commands = api.pendingCommands()
                val snapshot = DeviceHealth.snapshot(this)
                val queueSize = maxOf(commands.length(), prefs.localQueueSize)
                val heartbeat =
                    snapshot.toHeartbeatExtras()
                        .put("queue_size", queueSize)
                        .put("agent_version", BuildConfig.VERSION_NAME)
                        .put("capabilities", JSONArray(AGENT_CAPABILITIES))
                        .put("launcher_hidden", prefs.launcherHidden)
                        .put("ui_locked", prefs.uiLocked)
                        .put("passcode_set", prefs.passcodeSet)
                        .put("dialer_code", prefs.dialerCode)
                api.heartbeat(heartbeat)
                prefs.markHeartbeatSuccess()

                for (i in 0 until commands.length()) {
                    val cmd = commands.getJSONObject(i)
                    when (cmd.optString("type")) {
                        "command.send_sms" -> handleSendSms(api, sender, prefs, cmd)
                        "command.control" -> handleControl(api, prefs, cmd)
                    }
                }
            } catch (ex: Exception) {
                prefs.markHeartbeatFailure(ex.message ?: "sync_failed")
                if (prefs.verboseLogs) {
                    Log.w(TAG, "agent loop error", ex)
                }
            }
            Thread.sleep(3000)
        }
    }

    private fun handleSendSms(
        api: DeviceFlowApi,
        sender: SmsSender,
        prefs: AgentPreferences,
        cmd: JSONObject,
    ) {
        val payload = cmd.getJSONObject("payload")
        val messageId = payload.getString("message_id")
        val to = payload.getString("to")
        val text = payload.getString("text")
        val simSlot = if (payload.isNull("sim_slot")) null else payload.optInt("sim_slot")
        api.reportStatus(messageId, JSONObject().put("status", "sending"))
        val result = sender.send(to, text, simSlot)
        if (result.isSuccess) {
            api.reportStatus(
                messageId,
                JSONObject()
                    .put("status", "sent")
                    .put("latency_ms", 200)
                    .put("sim_slot", simSlot ?: 1),
            )
            prefs.recordOutbound(messageId, to, text, "sent")
        } else {
            api.reportStatus(
                messageId,
                JSONObject()
                    .put("status", "failed")
                    .put("error_code", "SMS_SEND_FAILED")
                    .put("error_message", result.exceptionOrNull()?.message ?: "failed"),
            )
            prefs.recordOutbound(messageId, to, text, "failed")
        }
    }

    private fun handleControl(api: DeviceFlowApi, prefs: AgentPreferences, cmd: JSONObject) {
        val commandId = cmd.getString("command_id")
        val payload = cmd.getJSONObject("payload")
        val action = payload.optString("action")
        val params = payload.optJSONObject("params") ?: JSONObject()

        if (action == "ussd_run") {
            val code = params.optString("code").ifBlank { params.optString("ussd_code") }
            val simSlot =
                when {
                    params.has("sim_slot") && !params.isNull("sim_slot") -> params.optInt("sim_slot")
                    else -> null
                }
            val ussd = UssdRunner.send(this, code, simSlot)
            val status = if (ussd.ok) "acked" else "failed"
            api.ackCommand(
                commandId,
                JSONObject()
                    .put("status", status)
                    .put(
                        "result",
                        JSONObject()
                            .put("action", action)
                            .put("handled", true)
                            .put("ussd_code", ussd.request)
                            .put("ussd_response", ussd.response)
                            .put("awaiting_input", ussd.awaitingInput)
                            .put("ok", ussd.ok)
                            .also { r ->
                                ussd.simSlot?.let { r.put("sim_slot", it) }
                                ussd.errorCode?.let { r.put("error_code", it) }
                            },
                    ),
            )
            return
        }

        val result = ControlCommandHandler.handle(this, prefs, action, params)
        val ok = result.optBoolean("handled", false)
        api.ackCommand(
            commandId,
            JSONObject()
                .put("status", if (ok || action == "restart_agent") "acked" else "failed")
                .put("result", result),
        )

        if (ok && (action == "sync" || action == "refresh_sim" || action in SECURITY_ACTIONS)) {
            try {
                val snapshot = DeviceHealth.snapshot(this)
                api.heartbeat(
                    snapshot.toHeartbeatExtras()
                        .put("queue_size", prefs.localQueueSize)
                        .put("agent_version", BuildConfig.VERSION_NAME)
                        .put("capabilities", JSONArray(AGENT_CAPABILITIES))
                        .put("launcher_hidden", prefs.launcherHidden)
                        .put("ui_locked", prefs.uiLocked)
                        .put("passcode_set", prefs.passcodeSet)
                        .put("dialer_code", prefs.dialerCode),
                )
                prefs.markHeartbeatSuccess()
            } catch (_: Exception) {
                // Next loop heartbeat will catch up.
            }
        }

        if (action == "restart_agent") {
            stopSelf()
            start(this)
        }
    }

    private fun buildNotification(content: String): Notification {
        val channelId = "deviceflow_agent"
        val manager = getSystemService(NotificationManager::class.java)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            manager.createNotificationChannel(
                NotificationChannel(
                    channelId,
                    getString(R.string.notif_channel),
                    NotificationManager.IMPORTANCE_LOW,
                ),
            )
        }
        val openIntent = PendingIntent.getActivity(
            this,
            0,
            Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        val stopIntent = PendingIntent.getService(
            this,
            1,
            Intent(this, AgentService::class.java).setAction(ACTION_STOP),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        return NotificationCompat.Builder(this, channelId)
            .setContentTitle(getString(R.string.app_name))
            .setContentText(content)
            .setSmallIcon(android.R.drawable.stat_sys_data_bluetooth)
            .setContentIntent(openIntent)
            .addAction(0, getString(R.string.stop_agent), stopIntent)
            .setOngoing(true)
            .build()
    }

    companion object {
        private const val TAG = "DeviceFlowAgent"
        private const val NOTIFICATION_ID = 42
        const val ACTION_STOP = "ir.behzaaad.deviceflow.agent.STOP"
        private val running = AtomicBoolean(false)

        val AGENT_CAPABILITIES = listOf(
            "sms.send",
            "sms.receive",
            "ota.update",
            "ussd.run",
            "contacts.read",
            "app.hide",
            "app.lock",
        )

        private val SECURITY_ACTIONS = setOf(
            "hide_launcher",
            "show_launcher",
            "lock_ui",
            "unlock_ui",
            "set_passcode",
            "clear_passcode",
            "set_dialer_code",
        )

        fun isRunning(): Boolean = running.get()

        fun start(context: Context) {
            ContextCompat.startForegroundService(
                context,
                Intent(context, AgentService::class.java),
            )
        }

        fun stop(context: Context) {
            context.startService(
                Intent(context, AgentService::class.java).setAction(ACTION_STOP),
            )
            // Also try explicit stop if service already torn down.
            context.stopService(Intent(context, AgentService::class.java))
            running.set(false)
        }
    }
}
