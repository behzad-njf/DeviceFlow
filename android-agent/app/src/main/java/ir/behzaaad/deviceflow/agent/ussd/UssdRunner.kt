package ir.behzaaad.deviceflow.agent.ussd

import android.Manifest
import android.accessibilityservice.AccessibilityService
import android.accessibilityservice.AccessibilityServiceInfo
import android.annotation.SuppressLint
import android.app.Activity
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.provider.Settings
import android.telecom.PhoneAccountHandle
import android.telecom.TelecomManager
import android.telephony.SubscriptionManager
import android.telephony.TelephonyManager
import android.text.TextUtils
import android.util.Log
import android.view.Gravity
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo
import android.widget.LinearLayout
import android.widget.ProgressBar
import android.widget.TextView
import androidx.core.app.NotificationCompat
import androidx.core.content.ContextCompat
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicInteger
import java.util.concurrent.atomic.AtomicReference

data class UssdResult(
    val ok: Boolean,
    val request: String,
    val response: String,
    val awaitingInput: Boolean,
    val errorCode: Int? = null,
    val simSlot: Int? = null,
)

/**
 * Foreground host that dials USSD via the system dialer (works on MIUI/Xiaomi where
 * TelephonyManager.sendUssdRequest almost always returns -1 for 3rd-party apps).
 */
class UssdHostActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val code = intent.getStringExtra(EXTRA_CODE).orEmpty()
        val simSlot =
            if (intent.hasExtra(EXTRA_SIM_SLOT)) intent.getIntExtra(EXTRA_SIM_SLOT, 1) else null
        val requestId = intent.getStringExtra(EXTRA_REQUEST_ID).orEmpty()

        val status = TextView(this).apply {
            text = getString(ir.behzaaad.deviceflow.agent.R.string.ussd_host_status, code)
            textSize = 16f
            setPadding(48, 48, 48, 24)
            gravity = Gravity.CENTER
        }
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER
            setBackgroundColor(0xF0FFFFFF.toInt())
            addView(ProgressBar(this@UssdHostActivity))
            addView(status)
        }
        setContentView(root)

        window.decorView.post {
            Thread {
                Thread.sleep(250)
                val result = UssdRunner.executeFromHost(this, code, simSlot)
                UssdRunner.completePending(requestId, result)
                runOnUiThread { finish() }
            }.start()
        }
    }

    companion object {
        const val EXTRA_CODE = "ussd_code"
        const val EXTRA_SIM_SLOT = "sim_slot"
        const val EXTRA_REQUEST_ID = "request_id"
    }
}

/**
 * Scrapes system USSD dialog text after dialing.
 * Enable in Settings → Accessibility → DeviceFlow USSD.
 */
class UssdAccessibilityService : AccessibilityService() {
    override fun onServiceConnected() {
        serviceInfo = serviceInfo?.apply {
            eventTypes =
                AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED or
                    AccessibilityEvent.TYPE_WINDOW_CONTENT_CHANGED or
                    AccessibilityEvent.TYPE_NOTIFICATION_STATE_CHANGED
            feedbackType = AccessibilityServiceInfo.FEEDBACK_GENERIC
            notificationTimeout = 80
            flags = flags or AccessibilityServiceInfo.FLAG_REPORT_VIEW_IDS or
                AccessibilityServiceInfo.FLAG_RETRIEVE_INTERACTIVE_WINDOWS
        }
        Log.i(TAG, "USSD accessibility connected")
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        if (event == null) return
        val armedGen = armedGeneration.get()
        if (armedGen <= 0) return

        val root = rootInActiveWindow ?: return
        val text = normalize(collectText(root))
        if (text.length < 3) return
        if (!looksLikeUssdDialog(text)) return

        // Ignore baseline (previous step dialog still on screen for a moment).
        val baseline = baselineText.get()
        if (!baseline.isNullOrBlank() && similar(text, baseline)) return

        lastResponse.set(Captured(text, armedGen, System.currentTimeMillis()))
        Log.i(TAG, "Captured USSD gen=$armedGen (${text.length} chars)")
    }

    override fun onInterrupt() = Unit

    companion object {
        private const val TAG = "DeviceFlowUssdA11y"

        private data class Captured(val text: String, val generation: Int, val atMs: Long)

        private val lastResponse = AtomicReference<Captured?>(null)
        private val baselineText = AtomicReference<String?>(null)
        private val generation = AtomicInteger(0)
        private val armedGeneration = AtomicInteger(0)

        fun isEnabled(context: Context): Boolean {
            val expected = ComponentName(context, UssdAccessibilityService::class.java).flattenToString()
            val enabled = Settings.Secure.getString(
                context.contentResolver,
                Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES,
            ) ?: return false
            val splitter = TextUtils.SimpleStringSplitter(':')
            splitter.setString(enabled)
            while (splitter.hasNext()) {
                if (splitter.next().equals(expected, ignoreCase = true)) return true
            }
            return false
        }

        /** Snapshot current screen as "old" so the next wait ignores it. */
        fun beginStep() {
            val current = lastResponse.get()?.text ?: peekScreenHeuristic()
            baselineText.set(current)
            lastResponse.set(null)
            val gen = generation.incrementAndGet()
            armedGeneration.set(gen)
            Log.i(TAG, "beginStep gen=$gen baselineLen=${current?.length ?: 0}")
        }

        fun endStep() {
            armedGeneration.set(0)
        }

        fun peekLatestForGeneration(gen: Int): String? {
            val cap = lastResponse.get() ?: return null
            if (cap.generation != gen) return null
            return cap.text
        }

        fun currentGeneration(): Int = armedGeneration.get()

        fun openSettings(context: Context) {
            context.startActivity(
                Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS)
                    .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK),
            )
        }

        private fun peekScreenHeuristic(): String? = lastResponse.get()?.text

        private fun normalize(raw: String): String =
            raw.lines().map { it.trim() }.filter { it.isNotEmpty() }.joinToString("\n")

        private fun similar(a: String, b: String): Boolean {
            if (a == b) return true
            val na = normalize(a)
            val nb = normalize(b)
            if (na == nb) return true
            // Same menu with tiny changes (focus / clock) — treat as same if high overlap.
            val la = na.lowercase()
            val lb = nb.lowercase()
            if (la.length < 12 || lb.length < 12) return la == lb
            val shorter = if (la.length <= lb.length) la else lb
            val longer = if (la.length <= lb.length) lb else la
            return longer.contains(shorter) || shorter.contains(longer.take(shorter.length))
        }

        private fun collectText(node: AccessibilityNodeInfo?): String {
            if (node == null) return ""
            val sb = StringBuilder()
            node.text?.let { if (it.isNotBlank()) sb.append(it).append('\n') }
            node.contentDescription?.let { if (it.isNotBlank()) sb.append(it).append('\n') }
            for (i in 0 until node.childCount) {
                sb.append(collectText(node.getChild(i)))
            }
            return sb.toString()
        }

        fun looksLikeUssdDialog(text: String): Boolean {
            val lower = text.lowercase()
            if (lower.length > 800) return false
            if (lower.contains("deviceflow is dialing")) return false
            if (lower.contains("running ussd")) return false
            if (lower.contains("enable ussd reply")) return false
            val hints =
                listOf(
                    "ussd",
                    "mmi",
                    "balance",
                    "ریال",
                    "تومان",
                    "موجودی",
                    "اعتبار",
                    "بسته",
                    "پاسخ",
                    "گزینه",
                    "انتخاب",
                    "ارسال",
                    "reply",
                    "enter",
                    "select",
                    "menu",
                    "please",
                    "لطفا",
                )
            if (hints.any { lower.contains(it) }) return true
            return Regex("""(?m)^\s*\d+[\).:\-]""").containsMatchIn(text) && text.length in 6..800
        }
    }
}

object UssdRunner {
    private const val TAG = "DeviceFlowUssd"
    private const val NOTIF_CHANNEL = "deviceflow_ussd"
    private const val NOTIF_ID = 77

    private val pending = AtomicReference<PendingUssd?>(null)

    private data class PendingUssd(
        val requestId: String,
        val latch: CountDownLatch,
        val box: AtomicReference<UssdResult>,
    )

    fun send(context: Context, code: String, simSlot: Int? = null, timeoutSec: Long = 80): UssdResult {
        val cleaned = code.trim()
        if (cleaned.isEmpty()) {
            return UssdResult(false, code, "Empty USSD code", false, simSlot = simSlot)
        }

        val callGranted =
            ContextCompat.checkSelfPermission(context, Manifest.permission.CALL_PHONE) ==
                PackageManager.PERMISSION_GRANTED
        if (!callGranted) {
            return UssdResult(
                false,
                cleaned,
                "CALL_PHONE permission not granted — open the agent app and allow Phone / Call permission",
                false,
                simSlot = simSlot,
            )
        }

        val requestId = System.nanoTime().toString()
        val latch = CountDownLatch(1)
        val box = AtomicReference<UssdResult>()
        pending.set(PendingUssd(requestId, latch, box))

        val appCtx = context.applicationContext
        val launch = Intent(appCtx, UssdHostActivity::class.java)
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP)
            .putExtra(UssdHostActivity.EXTRA_CODE, cleaned)
            .putExtra(UssdHostActivity.EXTRA_REQUEST_ID, requestId)
        if (simSlot != null) {
            launch.putExtra(UssdHostActivity.EXTRA_SIM_SLOT, simSlot)
        }

        postFullScreenLaunch(appCtx, launch)
        try {
            appCtx.startActivity(launch)
        } catch (ex: Exception) {
            Log.w(TAG, "startActivity for USSD failed", ex)
        }

        val finished = latch.await(timeoutSec, TimeUnit.SECONDS)
        val cur = pending.get()
        if (cur?.requestId == requestId) pending.compareAndSet(cur, null)
        dismissUssdNotification(appCtx)

        if (!finished) {
            return UssdResult(false, cleaned, "USSD timed out waiting for phone UI", false, simSlot = simSlot)
        }
        return box.get()
            ?: UssdResult(false, cleaned, "No USSD response", false, simSlot = simSlot)
    }

    fun completePending(requestId: String, result: UssdResult) {
        val cur = pending.get() ?: return
        if (cur.requestId != requestId) return
        cur.box.set(result)
        cur.latch.countDown()
    }

    fun executeFromHost(activity: Activity, code: String, simSlot: Int?): UssdResult {
        val cleaned = code.trim()

        // MIUI almost always fails sendUssdRequest with -1; only probe briefly on non-Xiaomi.
        if (!isLikelyMiuiOem()) {
            val api = trySendUssdRequest(activity, cleaned, simSlot, timeoutSec = 3)
            if (api.ok) {
                Log.i(TAG, "sendUssdRequest succeeded")
                return api
            }
            Log.w(TAG, "sendUssdRequest failed — dialer fallback")
        } else {
            Log.i(TAG, "MIUI/Xiaomi detected — skipping sendUssdRequest, dialing directly")
        }

        return dialViaCallIntent(activity, cleaned, simSlot)
    }

    private fun isLikelyMiuiOem(): Boolean {
        val man = Build.MANUFACTURER.orEmpty().lowercase()
        val brand = Build.BRAND.orEmpty().lowercase()
        return listOf("xiaomi", "redmi", "poco", "blackshark").any {
            man.contains(it) || brand.contains(it)
        }
    }

    @SuppressLint("MissingPermission")
    private fun trySendUssdRequest(
        context: Context,
        code: String,
        simSlot: Int?,
        timeoutSec: Long,
    ): UssdResult {
        val phoneStateGranted =
            ContextCompat.checkSelfPermission(context, Manifest.permission.READ_PHONE_STATE) ==
                PackageManager.PERMISSION_GRANTED
        val base = context.getSystemService(TelephonyManager::class.java)
            ?: return UssdResult(false, code, "TelephonyManager unavailable", false, simSlot = simSlot)
        val resolved = resolveTelephonyForSlot(context, base, simSlot, phoneStateGranted)
        if (resolved.error != null) {
            return UssdResult(false, code, resolved.error, false, simSlot = simSlot)
        }
        val telephony = resolved.telephony ?: base
        val usedSlot = resolved.slot
        val latch = CountDownLatch(1)
        val box = AtomicReference<UssdResult>()
        val handler = Handler(Looper.getMainLooper())
        return try {
            telephony.sendUssdRequest(
                code,
                object : TelephonyManager.UssdResponseCallback() {
                    override fun onReceiveUssdResponse(
                        tm: TelephonyManager,
                        request: String,
                        response: CharSequence,
                    ) {
                        val text = response.toString()
                        box.set(
                            UssdResult(true, request, text, looksLikeMenu(text), simSlot = usedSlot),
                        )
                        latch.countDown()
                    }

                    override fun onReceiveUssdResponseFailed(
                        tm: TelephonyManager,
                        request: String,
                        failureCode: Int,
                    ) {
                        box.set(
                            UssdResult(
                                false,
                                request,
                                "API failed code=$failureCode",
                                false,
                                errorCode = failureCode,
                                simSlot = usedSlot,
                            ),
                        )
                        latch.countDown()
                    }
                },
                handler,
            )
            if (!latch.await(timeoutSec, TimeUnit.SECONDS)) {
                UssdResult(false, code, "API timed out", false, errorCode = -1, simSlot = usedSlot)
            } else {
                box.get() ?: UssdResult(false, code, "API no response", false, simSlot = usedSlot)
            }
        } catch (ex: Exception) {
            UssdResult(false, code, ex.message ?: "API error", false, simSlot = usedSlot)
        }
    }

    @SuppressLint("MissingPermission")
    private fun dialViaCallIntent(activity: Activity, code: String, simSlot: Int?): UssdResult {
        val uri = Uri.fromParts("tel", code, null)
        val intent = Intent(Intent.ACTION_CALL, uri).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        applySimExtras(activity, intent, simSlot)

        return try {
            // Arm AFTER we know we're about to dial: treat any current dialog as baseline (old step).
            UssdAccessibilityService.beginStep()
            val gen = UssdAccessibilityService.currentGeneration()

            activity.startActivity(intent)
            Log.i(TAG, "Dialed USSD via ACTION_CALL sim=$simSlot code=$code gen=$gen")

            // Let dialer replace the previous MMI window before we accept text.
            Thread.sleep(900)
            // Re-arm so anything scraped during the transition of the OLD dialog is discarded.
            UssdAccessibilityService.beginStep()
            val waitGen = UssdAccessibilityService.currentGeneration()

            val captured =
                waitForStableNewCapture(
                    context = activity,
                    generation = waitGen,
                    timeoutMs = 35_000,
                    stableMs = 750,
                )
            UssdAccessibilityService.endStep()

            if (captured != null) {
                UssdResult(
                    ok = true,
                    request = code,
                    response = captured,
                    awaitingInput = looksLikeMenu(captured),
                    simSlot = simSlot,
                )
            } else {
                val a11yHint =
                    if (UssdAccessibilityService.isEnabled(activity)) {
                        "Dialed on phone, but no NEW dialog text was captured yet. " +
                            "If the menu is on screen, wait a moment and check the phone — " +
                            "or send the next option; the previous capture may arrive late."
                    } else {
                        "Dialed on phone. Enable Accessibility → “DeviceFlow USSD” to capture replies."
                    }
                UssdResult(
                    ok = true,
                    request = code,
                    response = a11yHint,
                    awaitingInput = true,
                    simSlot = simSlot,
                )
            }
        } catch (ex: SecurityException) {
            UssdAccessibilityService.endStep()
            UssdResult(false, code, "CALL_PHONE denied while dialing: ${ex.message}", false, simSlot = simSlot)
        } catch (ex: Exception) {
            UssdAccessibilityService.endStep()
            UssdResult(false, code, "Dial failed: ${ex.message}", false, simSlot = simSlot)
        }
    }

    /**
     * Wait until accessibility reports text for [generation] that stays unchanged for [stableMs].
     * This avoids returning the previous step's dialog (still visible for a moment after dial).
     */
    private fun waitForStableNewCapture(
        context: Context,
        generation: Int,
        timeoutMs: Long,
        stableMs: Long,
    ): String? {
        if (!UssdAccessibilityService.isEnabled(context)) {
            Thread.sleep(2_000)
            return null
        }

        val deadline = System.currentTimeMillis() + timeoutMs
        var candidate: String? = null
        var candidateSince = 0L

        while (System.currentTimeMillis() < deadline) {
            val text = UssdAccessibilityService.peekLatestForGeneration(generation)
            if (!text.isNullOrBlank()) {
                if (text == candidate) {
                    if (System.currentTimeMillis() - candidateSince >= stableMs) {
                        Log.i(TAG, "Stable USSD capture (${text.length} chars)")
                        return text
                    }
                } else {
                    candidate = text
                    candidateSince = System.currentTimeMillis()
                    Log.i(TAG, "Candidate USSD capture (${text.length} chars), waiting for stability")
                }
            }
            Thread.sleep(250)
        }
        return candidate
    }

    @SuppressLint("MissingPermission")
    private fun applySimExtras(context: Context, intent: Intent, simSlot: Int?) {
        if (simSlot == null) return
        val zeroBased = (simSlot - 1).coerceAtLeast(0)
        intent.putExtra("com.android.phone.extra.slot", zeroBased)
        intent.putExtra("slot", zeroBased)
        intent.putExtra("simSlot", zeroBased)
        intent.putExtra("SimSlot", zeroBased)
        intent.putExtra("slot_id", zeroBased)
        intent.putExtra("simId", zeroBased)

        val phoneStateGranted =
            ContextCompat.checkSelfPermission(context, Manifest.permission.READ_PHONE_STATE) ==
                PackageManager.PERMISSION_GRANTED
        if (!phoneStateGranted) return

        try {
            val subManager = context.getSystemService(SubscriptionManager::class.java)
            val info = subManager?.activeSubscriptionInfoList
                ?.firstOrNull { it.simSlotIndex + 1 == simSlot }
            if (info != null) {
                intent.putExtra("subscription", info.subscriptionId)
                intent.putExtra("sub_id", info.subscriptionId)
                intent.putExtra(SubscriptionManager.EXTRA_SUBSCRIPTION_INDEX, info.subscriptionId)
            }
            val handle = resolvePhoneAccount(context, simSlot)
            if (handle != null) {
                intent.putExtra(TelecomManager.EXTRA_PHONE_ACCOUNT_HANDLE, handle)
            }
        } catch (ex: Exception) {
            Log.w(TAG, "SIM extras incomplete", ex)
        }
    }

    @SuppressLint("MissingPermission")
    private fun resolvePhoneAccount(context: Context, simSlot: Int): PhoneAccountHandle? {
        val telecom = context.getSystemService(TelecomManager::class.java) ?: return null
        val accounts =
            try {
                telecom.callCapablePhoneAccounts
            } catch (_: SecurityException) {
                return null
            }
        if (accounts.isNullOrEmpty()) return null
        val subManager = context.getSystemService(SubscriptionManager::class.java)
        val info = subManager?.activeSubscriptionInfoList
            ?.firstOrNull { it.simSlotIndex + 1 == simSlot }
            ?: return accounts.getOrNull(simSlot - 1) ?: accounts.firstOrNull()
        return accounts.firstOrNull { it.id.contains(info.subscriptionId.toString()) }
            ?: accounts.getOrNull(simSlot - 1)
            ?: accounts.firstOrNull()
    }

    @SuppressLint("MissingPermission")
    private fun resolveTelephonyForSlot(
        context: Context,
        base: TelephonyManager,
        simSlot: Int?,
        phoneStateGranted: Boolean,
    ): ResolvedTelephony {
        if (simSlot == null || !phoneStateGranted) {
            return ResolvedTelephony(base, simSlot, null)
        }
        val subManager = context.getSystemService(SubscriptionManager::class.java)
        val list =
            try {
                subManager?.activeSubscriptionInfoList.orEmpty()
            } catch (ex: SecurityException) {
                return ResolvedTelephony(base, simSlot, "Cannot read SIM list: ${ex.message}")
            }
        val info = list.firstOrNull { it.simSlotIndex + 1 == simSlot }
            ?: return ResolvedTelephony(base, simSlot, "SIM slot $simSlot not found")
        return try {
            ResolvedTelephony(
                base.createForSubscriptionId(info.subscriptionId),
                info.simSlotIndex + 1,
                null,
            )
        } catch (ex: Exception) {
            ResolvedTelephony(base, info.simSlotIndex + 1, ex.message)
        }
    }

    private fun looksLikeMenu(text: String): Boolean {
        val lower = text.lowercase()
        if (lower.contains("reply") || lower.contains("enter") || lower.contains("select")) {
            return true
        }
        if (lower.contains("گزینه") || lower.contains("عدد") || lower.contains("انتخاب")) return true
        return Regex("""(?m)^\s*\d+[\).:\-]""").containsMatchIn(text)
    }

    private fun postFullScreenLaunch(context: Context, launch: Intent) {
        val nm = context.getSystemService(NotificationManager::class.java) ?: return
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            nm.createNotificationChannel(
                NotificationChannel(NOTIF_CHANNEL, "USSD", NotificationManager.IMPORTANCE_HIGH),
            )
        }
        val pi = PendingIntent.getActivity(
            context,
            0,
            launch,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        val notif = NotificationCompat.Builder(context, NOTIF_CHANNEL)
            .setSmallIcon(android.R.drawable.ic_menu_call)
            .setContentTitle("Running USSD")
            .setContentText("Tap if USSD UI did not open")
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setCategory(NotificationCompat.CATEGORY_CALL)
            .setAutoCancel(true)
            .setContentIntent(pi)
            .setFullScreenIntent(pi, true)
            .build()
        nm.notify(NOTIF_ID, notif)
    }

    private fun dismissUssdNotification(context: Context) {
        context.getSystemService(NotificationManager::class.java)?.cancel(NOTIF_ID)
    }

    private data class ResolvedTelephony(
        val telephony: TelephonyManager?,
        val slot: Int?,
        val error: String?,
    )
}
