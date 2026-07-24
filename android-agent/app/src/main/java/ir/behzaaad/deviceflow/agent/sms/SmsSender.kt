package ir.behzaaad.deviceflow.agent.sms

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.telephony.SmsManager
import android.telephony.SubscriptionManager
import androidx.core.content.ContextCompat

class SmsSender(private val context: Context) {
    fun send(to: String, text: String, simSlot: Int?): Result<Unit> {
        return try {
            val smsManager = resolveSmsManager(simSlot)
            @Suppress("DEPRECATION")
            smsManager.sendTextMessage(to, null, text, null, null)
            Result.success(Unit)
        } catch (ex: Exception) {
            Result.failure(ex)
        }
    }

    @Suppress("DEPRECATION")
    private fun resolveSmsManager(simSlot: Int?): SmsManager {
        if (simSlot == null) {
            return SmsManager.getDefault()
        }
        val subManager = context.getSystemService(SubscriptionManager::class.java)
        val list = subManager.activeSubscriptionInfoList ?: emptyList()
        val info = list.firstOrNull { it.simSlotIndex + 1 == simSlot } ?: list.firstOrNull()
        return if (info != null) {
            SmsManager.getSmsManagerForSubscriptionId(info.subscriptionId)
        } else {
            SmsManager.getDefault()
        }
    }

    companion object {
        fun hasSmsPermission(context: Context): Boolean {
            val send = ContextCompat.checkSelfPermission(context, Manifest.permission.SEND_SMS)
            val receive = ContextCompat.checkSelfPermission(context, Manifest.permission.RECEIVE_SMS)
            return send == PackageManager.PERMISSION_GRANTED &&
                receive == PackageManager.PERMISSION_GRANTED
        }
    }
}
