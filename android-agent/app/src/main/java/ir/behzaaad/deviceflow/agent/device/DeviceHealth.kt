package ir.behzaaad.deviceflow.agent.device

import android.Manifest
import android.annotation.SuppressLint
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.PackageManager
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import android.net.wifi.WifiManager
import android.os.BatteryManager
import android.os.Build
import android.os.StatFs
import android.telephony.CellInfoCdma
import android.telephony.CellInfoGsm
import android.telephony.CellInfoLte
import android.telephony.CellInfoNr
import android.telephony.CellInfoWcdma
import android.telephony.SubscriptionManager
import android.telephony.TelephonyManager
import androidx.core.content.ContextCompat
import org.json.JSONArray
import org.json.JSONObject

data class BatteryStatus(
    /** Percent 0–100, or null if unavailable. */
    val level: Int?,
    val charging: Boolean,
)

data class SimInfo(
    val slotIndex: Int,
    val operator: String,
    val phoneNumber: String,
)

data class DeviceSnapshot(
    val battery: BatteryStatus,
    /** Qualitative label: excellent / good / fair / poor / none / unknown */
    val signal: String,
    /** wifi / cellular / ethernet / none / unknown */
    val network: String,
    /** Free internal storage in bytes (capped to Int.MAX_VALUE for API). */
    val storageFree: Int?,
    val permissions: Map<String, Boolean>,
    val sims: List<SimInfo>,
    val location: LocationFix? = null,
) {
    fun toHeartbeatExtras(): JSONObject =
        JSONObject()
            .put("battery", battery.level)
            .put("charging", battery.charging)
            .put("signal", signal)
            .put("network", network)
            .put("storage_free", storageFree)
            .put(
                "permissions",
                JSONObject().also { obj ->
                    permissions.forEach { (k, v) -> obj.put(k, v) }
                },
            )
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
            .also { obj ->
                location?.let {
                    obj.put("lat", it.lat)
                    obj.put("lng", it.lng)
                    it.accuracyMeters?.let { acc -> obj.put("accuracy_m", acc.toDouble()) }
                    obj.put("location_updated_at_ms", it.updatedAtMs)
                }
            }
}

object DeviceHealth {
    private val SIGNAL_LABELS = arrayOf("none", "poor", "fair", "good", "excellent")

    fun snapshot(context: Context): DeviceSnapshot {
        val network = networkType(context)
        DeviceLocation.start(context)
        return DeviceSnapshot(
            battery = battery(context),
            signal = signalLabel(context, network),
            network = network,
            storageFree = storageFreeBytes(context),
            permissions = permissions(context),
            sims = sims(context),
            location = DeviceLocation.current(context),
        )
    }

    fun battery(context: Context): BatteryStatus {
        val manager = context.getSystemService(BatteryManager::class.java)
        val capacity = manager?.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY)
        val level =
            if (capacity != null && capacity in 0..100) {
                capacity
            } else {
                val intent =
                    context.registerReceiver(null, IntentFilter(Intent.ACTION_BATTERY_CHANGED))
                val raw = intent?.getIntExtra(BatteryManager.EXTRA_LEVEL, -1) ?: -1
                val scale = intent?.getIntExtra(BatteryManager.EXTRA_SCALE, 100) ?: 100
                if (raw >= 0 && scale > 0) {
                    ((raw * 100f) / scale).toInt().coerceIn(0, 100)
                } else {
                    null
                }
            }

        val charging =
            manager?.isCharging
                ?: run {
                    val intent =
                        context.registerReceiver(null, IntentFilter(Intent.ACTION_BATTERY_CHANGED))
                    val status =
                        intent?.getIntExtra(BatteryManager.EXTRA_STATUS, -1)
                            ?: BatteryManager.BATTERY_STATUS_UNKNOWN
                    status == BatteryManager.BATTERY_STATUS_CHARGING ||
                        status == BatteryManager.BATTERY_STATUS_FULL
                }

        return BatteryStatus(level = level, charging = charging)
    }

    fun networkType(context: Context): String {
        val cm = context.getSystemService(ConnectivityManager::class.java) ?: return "unknown"
        val active = cm.activeNetwork ?: return "none"
        val caps = cm.getNetworkCapabilities(active) ?: return "none"
        return when {
            caps.hasTransport(NetworkCapabilities.TRANSPORT_WIFI) -> "wifi"
            caps.hasTransport(NetworkCapabilities.TRANSPORT_CELLULAR) -> "cellular"
            caps.hasTransport(NetworkCapabilities.TRANSPORT_ETHERNET) -> "ethernet"
            caps.hasTransport(NetworkCapabilities.TRANSPORT_BLUETOOTH) -> "bluetooth"
            else -> "other"
        }
    }

    fun signalLabel(context: Context, network: String = networkType(context)): String {
        val cellularBars = cellularSignalBars(context)
        if (cellularBars != null) {
            return SIGNAL_LABELS[cellularBars.coerceIn(0, 4)]
        }
        if (network == "wifi") {
            return wifiSignalLabel(context)
        }
        return "unknown"
    }

    fun storageFreeBytes(context: Context): Int? {
        return try {
            val stat = StatFs(context.filesDir.absolutePath)
            val free = stat.availableBytes
            free.coerceAtMost(Int.MAX_VALUE.toLong()).toInt()
        } catch (_: Exception) {
            null
        }
    }

    fun permissions(context: Context): Map<String, Boolean> {
        fun granted(permission: String): Boolean =
            ContextCompat.checkSelfPermission(context, permission) ==
                PackageManager.PERMISSION_GRANTED

        val map =
            mutableMapOf(
                "sms" to (
                    granted(Manifest.permission.SEND_SMS) &&
                        granted(Manifest.permission.RECEIVE_SMS)
                ),
                "read_sms" to granted(Manifest.permission.READ_SMS),
                "phone" to granted(Manifest.permission.READ_PHONE_STATE),
                "phone_numbers" to granted(Manifest.permission.READ_PHONE_NUMBERS),
                "call" to granted(Manifest.permission.CALL_PHONE),
                "contacts" to granted(Manifest.permission.READ_CONTACTS),
                "location" to DeviceLocation.hasPermission(context),
            )
        if (Build.VERSION.SDK_INT >= 33) {
            map["notifications"] = granted(Manifest.permission.POST_NOTIFICATIONS)
        }
        return map
    }

    @SuppressLint("MissingPermission")
    fun sims(context: Context): List<SimInfo> {
        if (
            ContextCompat.checkSelfPermission(context, Manifest.permission.READ_PHONE_STATE) !=
            PackageManager.PERMISSION_GRANTED
        ) {
            return emptyList()
        }
        return try {
            val subManager = context.getSystemService(SubscriptionManager::class.java)
            val list = subManager?.activeSubscriptionInfoList.orEmpty()
            if (list.isEmpty()) {
                emptyList()
            } else {
                list.map { info ->
                    SimInfo(
                        slotIndex = info.simSlotIndex + 1,
                        operator = info.carrierName?.toString().orEmpty(),
                        phoneNumber = resolvePhoneNumber(context, subManager, info),
                    )
                }
            }
        } catch (_: SecurityException) {
            emptyList()
        } catch (_: Exception) {
            emptyList()
        }
    }

    @SuppressLint("MissingPermission")
    private fun resolvePhoneNumber(
        context: Context,
        subManager: SubscriptionManager?,
        info: android.telephony.SubscriptionInfo,
    ): String {
        // Avoid touching phone identifiers without READ_PHONE_NUMBERS — that spams
        // TelephonyPermissions denials and can fail dual-SIM lookups on modern Android.
        val canReadNumber =
            ContextCompat.checkSelfPermission(context, Manifest.permission.READ_PHONE_NUMBERS) ==
                PackageManager.PERMISSION_GRANTED
        if (!canReadNumber) return ""

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU && subManager != null) {
            return try {
                subManager.getPhoneNumber(info.subscriptionId).orEmpty()
            } catch (_: SecurityException) {
                ""
            } catch (_: Exception) {
                ""
            }
        }
        @Suppress("DEPRECATION")
        return info.number.orEmpty()
    }

    @SuppressLint("MissingPermission")
    private fun cellularSignalBars(context: Context): Int? {
        if (
            ContextCompat.checkSelfPermission(context, Manifest.permission.READ_PHONE_STATE) !=
            PackageManager.PERMISSION_GRANTED
        ) {
            return null
        }
        val telephony = context.getSystemService(TelephonyManager::class.java) ?: return null
        return try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
                telephony.signalStrength?.level
            } else {
                barsFromCellInfo(telephony)
            }
        } catch (_: SecurityException) {
            null
        } catch (_: Exception) {
            null
        }
    }

    @SuppressLint("MissingPermission")
    private fun barsFromCellInfo(telephony: TelephonyManager): Int? {
        val cells = telephony.allCellInfo ?: return null
        for (cell in cells) {
            if (!cell.isRegistered) continue
            val level =
                when (cell) {
                    is CellInfoLte -> cell.cellSignalStrength.level
                    is CellInfoGsm -> cell.cellSignalStrength.level
                    is CellInfoWcdma -> cell.cellSignalStrength.level
                    is CellInfoCdma -> cell.cellSignalStrength.level
                    is CellInfoNr ->
                        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                            cell.cellSignalStrength.level
                        } else {
                            null
                        }
                    else -> null
                }
            if (level != null) return level
        }
        return null
    }

    @Suppress("DEPRECATION")
    private fun wifiSignalLabel(context: Context): String {
        return try {
            val wifi = context.applicationContext.getSystemService(Context.WIFI_SERVICE) as? WifiManager
                ?: return "unknown"
            val rssi = wifi.connectionInfo?.rssi ?: return "unknown"
            when {
                rssi >= -50 -> "excellent"
                rssi >= -60 -> "good"
                rssi >= -70 -> "fair"
                rssi >= -80 -> "poor"
                else -> "none"
            }
        } catch (_: Exception) {
            "unknown"
        }
    }
}
