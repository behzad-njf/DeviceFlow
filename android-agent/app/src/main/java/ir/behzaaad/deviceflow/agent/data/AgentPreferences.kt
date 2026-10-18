package ir.behzaaad.deviceflow.agent.data

import android.content.Context
import androidx.core.content.edit
import java.security.MessageDigest
import java.security.SecureRandom

class AgentPreferences(context: Context) {
    private val appContext = context.applicationContext
    private val prefs = appContext.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    var serverUrl: String
        get() = prefs.getString(KEY_SERVER, "http://10.0.2.2:8000/api/v1") ?: "http://10.0.2.2:8000/api/v1"
        set(value) = prefs.edit { putString(KEY_SERVER, value.trimEnd('/')) }

    var deviceToken: String?
        get() = prefs.getString(KEY_TOKEN, null)
        set(value) = prefs.edit { putString(KEY_TOKEN, value) }

    var deviceId: String?
        get() = prefs.getString(KEY_DEVICE_ID, null)
        set(value) = prefs.edit { putString(KEY_DEVICE_ID, value) }

    var deviceName: String?
        get() = prefs.getString(KEY_NAME, null)
        set(value) = prefs.edit { putString(KEY_NAME, value) }

    var verboseLogs: Boolean
        get() = prefs.getBoolean(KEY_VERBOSE_LOGS, false)
        set(value) = prefs.edit { putBoolean(KEY_VERBOSE_LOGS, value) }

    var localQueueSize: Int
        get() = prefs.getInt(KEY_LOCAL_QUEUE, 0)
        set(value) = prefs.edit { putInt(KEY_LOCAL_QUEUE, value.coerceAtLeast(0)) }

    /** One-time first-launch prompt that points users to the permissions guide. */
    var permissionsGuidePromptShown: Boolean
        get() = prefs.getBoolean(KEY_PERM_GUIDE_PROMPT, false)
        set(value) = prefs.edit { putBoolean(KEY_PERM_GUIDE_PROMPT, value) }

    var smsSentCount: Int
        get() = prefs.getInt(KEY_SMS_SENT, 0)
        set(value) = prefs.edit { putInt(KEY_SMS_SENT, value.coerceAtLeast(0)) }

    var smsFailedCount: Int
        get() = prefs.getInt(KEY_SMS_FAILED, 0)
        set(value) = prefs.edit { putInt(KEY_SMS_FAILED, value.coerceAtLeast(0)) }

    var smsReceivedCount: Int
        get() = prefs.getInt(KEY_SMS_RECEIVED, 0)
        set(value) = prefs.edit { putInt(KEY_SMS_RECEIVED, value.coerceAtLeast(0)) }

    var lastHeartbeatAtMs: Long
        get() = prefs.getLong(KEY_LAST_HB_AT, 0L)
        set(value) = prefs.edit { putLong(KEY_LAST_HB_AT, value) }

    var lastHeartbeatOk: Boolean
        get() = prefs.getBoolean(KEY_LAST_HB_OK, false)
        set(value) = prefs.edit { putBoolean(KEY_LAST_HB_OK, value) }

    var lastSyncError: String
        get() = prefs.getString(KEY_LAST_SYNC_ERR, "") ?: ""
        set(value) = prefs.edit { putString(KEY_LAST_SYNC_ERR, value.take(240)) }

    var launcherHidden: Boolean
        get() = prefs.getBoolean(KEY_LAUNCHER_HIDDEN, false)
        set(value) {
            prefs.edit { putBoolean(KEY_LAUNCHER_HIDDEN, value) }
            notifySecurityChanged()
        }

    var uiLocked: Boolean
        get() = prefs.getBoolean(KEY_UI_LOCKED, false)
        set(value) {
            prefs.edit { putBoolean(KEY_UI_LOCKED, value) }
            notifySecurityChanged()
        }

    /** Digits dialed as *#*#CODE#*#* to reopen the app when the launcher icon is hidden. */
    var dialerCode: String
        get() {
            val stored = prefs.getString(KEY_DIALER_CODE, null)?.trim().orEmpty()
            return if (isValidDialerCode(stored)) stored else DEFAULT_DIALER_CODE
        }
        set(value) {
            val code = value.trim()
            require(isValidDialerCode(code)) { "invalid_dialer_code" }
            prefs.edit { putString(KEY_DIALER_CODE, code) }
            notifySecurityChanged()
        }

    fun setDialerCode(code: String): Boolean {
        val normalized = code.trim()
        if (!isValidDialerCode(normalized)) return false
        dialerCode = normalized
        return true
    }

    val passcodeSet: Boolean
        get() = !prefs.getString(KEY_PASSCODE_HASH, null).isNullOrBlank()

    val isPaired: Boolean
        get() = !deviceToken.isNullOrBlank()

    fun clearPairing() {
        prefs.edit {
            remove(KEY_TOKEN)
            remove(KEY_DEVICE_ID)
            remove(KEY_NAME)
        }
    }

    fun setPasscode(passcode: String): Boolean {
        val pin = passcode.trim()
        if (!pin.matches(Regex("^\\d{4,8}$"))) return false
        val salt = ByteArray(16).also { SecureRandom().nextBytes(it) }
        val hash = hashPasscode(pin, salt)
        prefs.edit {
            putString(KEY_PASSCODE_SALT, salt.toHex())
            putString(KEY_PASSCODE_HASH, hash)
            putBoolean(KEY_UI_LOCKED, true)
        }
        notifySecurityChanged()
        return true
    }

    fun verifyPasscode(passcode: String): Boolean {
        val saltHex = prefs.getString(KEY_PASSCODE_SALT, null) ?: return false
        val expected = prefs.getString(KEY_PASSCODE_HASH, null) ?: return false
        val salt = saltHex.fromHex() ?: return false
        return hashPasscode(passcode.trim(), salt) == expected
    }

    fun clearPasscode() {
        prefs.edit {
            remove(KEY_PASSCODE_HASH)
            remove(KEY_PASSCODE_SALT)
            putBoolean(KEY_UI_LOCKED, false)
        }
        notifySecurityChanged()
    }

    fun lockUi() {
        if (passcodeSet) {
            uiLocked = true
        }
    }

    fun unlockUi() {
        uiLocked = false
    }

    private fun notifySecurityChanged() {
        ir.behzaaad.deviceflow.agent.security.AppSecurityEvents.notifyChanged(appContext)
    }

    fun markHeartbeatSuccess() {
        prefs.edit {
            putLong(KEY_LAST_HB_AT, System.currentTimeMillis())
            putBoolean(KEY_LAST_HB_OK, true)
            putString(KEY_LAST_SYNC_ERR, "")
        }
    }

    fun markHeartbeatFailure(message: String) {
        prefs.edit {
            putLong(KEY_LAST_HB_AT, System.currentTimeMillis())
            putBoolean(KEY_LAST_HB_OK, false)
            putString(KEY_LAST_SYNC_ERR, message.take(240))
        }
    }

    fun recordOutbound(messageId: String, to: String, body: String, status: String) {
        if (status == "sent") {
            smsSentCount += 1
        } else if (status == "failed") {
            smsFailedCount += 1
        }
    }

    fun recordInbound(from: String, body: String) {
        smsReceivedCount += 1
    }

    private fun hashPasscode(passcode: String, salt: ByteArray): String {
        val digest = MessageDigest.getInstance("SHA-256")
        digest.update(salt)
        digest.update(passcode.toByteArray(Charsets.UTF_8))
        return digest.digest().toHex()
    }

    private fun ByteArray.toHex(): String = joinToString("") { "%02x".format(it) }

    private fun String.fromHex(): ByteArray? {
        if (length % 2 != 0) return null
        return try {
            ByteArray(length / 2) { i ->
                substring(i * 2, i * 2 + 2).toInt(16).toByte()
            }
        } catch (_: Exception) {
            null
        }
    }

    companion object {
        private const val PREFS = "deviceflow_agent"
        private const val KEY_SERVER = "server_url"
        private const val KEY_TOKEN = "device_token"
        private const val KEY_DEVICE_ID = "device_id"
        private const val KEY_NAME = "device_name"
        private const val KEY_VERBOSE_LOGS = "verbose_logs"
        private const val KEY_LOCAL_QUEUE = "local_queue_size"
        private const val KEY_PERM_GUIDE_PROMPT = "permissions_guide_prompt_shown"
        private const val KEY_SMS_SENT = "sms_sent_count"
        private const val KEY_SMS_FAILED = "sms_failed_count"
        private const val KEY_SMS_RECEIVED = "sms_received_count"
        private const val KEY_LAST_HB_AT = "last_heartbeat_at"
        private const val KEY_LAST_HB_OK = "last_heartbeat_ok"
        private const val KEY_LAST_SYNC_ERR = "last_sync_error"
        private const val KEY_LAUNCHER_HIDDEN = "launcher_hidden"
        private const val KEY_UI_LOCKED = "ui_locked"
        private const val KEY_PASSCODE_HASH = "passcode_hash"
        private const val KEY_PASSCODE_SALT = "passcode_salt"
        private const val KEY_DIALER_CODE = "dialer_code"
        const val DEFAULT_DIALER_CODE = "3323"

        fun isValidDialerCode(code: String): Boolean =
            code.matches(Regex("^\\d{3,8}$"))
    }
}
