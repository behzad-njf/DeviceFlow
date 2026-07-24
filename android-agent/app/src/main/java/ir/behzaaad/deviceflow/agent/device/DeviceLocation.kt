package ir.behzaaad.deviceflow.agent.device

import android.Manifest
import android.annotation.SuppressLint
import android.content.Context
import android.content.pm.PackageManager
import android.location.Location
import android.location.LocationListener
import android.location.LocationManager
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.util.Log
import androidx.core.content.ContextCompat
import org.json.JSONObject
import java.util.concurrent.atomic.AtomicReference

data class LocationFix(
    val lat: Double,
    val lng: Double,
    val accuracyMeters: Float?,
    val updatedAtMs: Long,
) {
    fun toJson(): JSONObject =
        JSONObject()
            .put("lat", lat)
            .put("lng", lng)
            .put("accuracy_m", accuracyMeters?.toDouble())
            .put("updated_at_ms", updatedAtMs)
}

/**
 * Best-effort GPS/network location for map heartbeats.
 * Uses platform LocationManager (no Play Services).
 */
object DeviceLocation {
    private const val TAG = "DeviceFlowLocation"
    private const val MIN_TIME_MS = 20_000L
    private const val MIN_DISTANCE_M = 25f

    private val cached = AtomicReference<LocationFix?>(null)
    private var started = false
    private val listener =
        object : LocationListener {
            override fun onLocationChanged(location: Location) {
                cached.set(fromAndroid(location))
            }

            @Deprecated("Deprecated in Java")
            override fun onStatusChanged(provider: String?, status: Int, extras: Bundle?) = Unit

            override fun onProviderEnabled(provider: String) = Unit

            override fun onProviderDisabled(provider: String) = Unit
        }

    fun hasPermission(context: Context): Boolean {
        val fine =
            ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_FINE_LOCATION) ==
                PackageManager.PERMISSION_GRANTED
        val coarse =
            ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_COARSE_LOCATION) ==
                PackageManager.PERMISSION_GRANTED
        return fine || coarse
    }

    @SuppressLint("MissingPermission")
    fun start(context: Context) {
        if (!hasPermission(context)) return
        if (started) {
            refreshLastKnown(context)
            return
        }
        val lm = context.getSystemService(LocationManager::class.java) ?: return
        val appCtx = context.applicationContext
        try {
            refreshLastKnown(appCtx)
            val handler = Handler(Looper.getMainLooper())
            val providers =
                buildList {
                    if (lm.isProviderEnabled(LocationManager.GPS_PROVIDER)) add(LocationManager.GPS_PROVIDER)
                    if (lm.isProviderEnabled(LocationManager.NETWORK_PROVIDER)) {
                        add(LocationManager.NETWORK_PROVIDER)
                    }
                }
            if (providers.isEmpty()) {
                Log.w(TAG, "No location providers enabled")
                return
            }
            for (provider in providers) {
                lm.requestLocationUpdates(
                    provider,
                    MIN_TIME_MS,
                    MIN_DISTANCE_M,
                    listener,
                    handler.looper,
                )
            }
            started = true
            Log.i(TAG, "Location updates started via ${providers.joinToString()}")
        } catch (ex: SecurityException) {
            Log.w(TAG, "Location permission denied", ex)
        } catch (ex: Exception) {
            Log.w(TAG, "Location start failed", ex)
        }
    }

    fun stop(context: Context) {
        if (!started) return
        try {
            context.getSystemService(LocationManager::class.java)?.removeUpdates(listener)
        } catch (_: Exception) {
        }
        started = false
    }

    @SuppressLint("MissingPermission")
    fun current(context: Context): LocationFix? {
        if (!hasPermission(context)) return null
        refreshLastKnown(context)
        return cached.get()
    }

    @SuppressLint("MissingPermission")
    private fun refreshLastKnown(context: Context) {
        if (!hasPermission(context)) return
        val lm = context.getSystemService(LocationManager::class.java) ?: return
        try {
            val candidates =
                listOfNotNull(
                    lm.getLastKnownLocation(LocationManager.GPS_PROVIDER),
                    lm.getLastKnownLocation(LocationManager.NETWORK_PROVIDER),
                    lm.getLastKnownLocation(LocationManager.PASSIVE_PROVIDER),
                )
            val best = candidates.maxByOrNull { score(it) } ?: return
            val existing = cached.get()
            if (existing == null || best.time >= existing.updatedAtMs || score(best) > scoreExisting(existing)) {
                cached.set(fromAndroid(best))
            }
        } catch (_: SecurityException) {
        } catch (_: Exception) {
        }
    }

    private fun scoreExisting(fix: LocationFix): Double {
        val agePenalty = (System.currentTimeMillis() - fix.updatedAtMs).coerceAtLeast(0) / 60_000.0
        val acc = (fix.accuracyMeters ?: 500f).toDouble()
        return 1_000.0 / (acc + 1.0) - agePenalty
    }

    private fun score(loc: Location): Double {
        val agePenalty = (System.currentTimeMillis() - loc.time).coerceAtLeast(0) / 60_000.0
        val acc = if (loc.hasAccuracy()) loc.accuracy.toDouble() else 500.0
        return 1_000.0 / (acc + 1.0) - agePenalty
    }

    private fun fromAndroid(location: Location): LocationFix =
        LocationFix(
            lat = location.latitude,
            lng = location.longitude,
            accuracyMeters = if (location.hasAccuracy()) location.accuracy else null,
            updatedAtMs = location.time.takeIf { it > 0 } ?: System.currentTimeMillis(),
        )
}
