package ir.behzaaad.deviceflow.agent.data

import org.json.JSONArray
import org.json.JSONObject
import java.io.BufferedReader
import java.io.InputStreamReader
import java.io.OutputStreamWriter
import java.net.HttpURLConnection
import java.net.URL

class DeviceFlowApi(private val baseUrl: String, private val deviceToken: String? = null) {
    fun pair(code: String, deviceInfo: JSONObject): JSONObject {
        val body = JSONObject()
            .put("pairing_code", code)
            .put("device_info", deviceInfo)
        return request("POST", "/agent/pair/", body, authed = false)
    }

    fun heartbeat(payload: JSONObject): JSONObject =
        request("POST", "/agent/heartbeat/", payload)

    fun pendingCommands(): JSONArray {
        val result = request("GET", "/agent/commands/pending/", null)
        return result.optJSONArray("results") ?: JSONArray()
    }

    fun reportStatus(messageId: String, payload: JSONObject): JSONObject =
        request("POST", "/agent/messages/$messageId/status/", payload)

    fun postInbound(payload: JSONObject): JSONObject =
        request("POST", "/agent/inbound/", payload)

    fun ackCommand(commandId: String, payload: JSONObject): JSONObject =
        request("POST", "/agent/commands/$commandId/ack/", payload)

    private fun request(
        method: String,
        path: String,
        body: JSONObject?,
        authed: Boolean = true,
    ): JSONObject {
        val url = URL(baseUrl.trimEnd('/') + path)
        val conn = (url.openConnection() as HttpURLConnection).apply {
            requestMethod = method
            connectTimeout = 15000
            readTimeout = 15000
            setRequestProperty("Accept", "application/json")
            if (authed && !deviceToken.isNullOrBlank()) {
                setRequestProperty("Authorization", "Device $deviceToken")
            }
            if (body != null) {
                doOutput = true
                setRequestProperty("Content-Type", "application/json")
            }
        }
        if (body != null) {
            OutputStreamWriter(conn.outputStream).use { it.write(body.toString()) }
        }
        val code = conn.responseCode
        val stream = if (code in 200..299) conn.inputStream else conn.errorStream
        val text = BufferedReader(InputStreamReader(stream)).use { it.readText() }
        if (code !in 200..299) {
            throw IllegalStateException("HTTP $code: $text")
        }
        return if (text.isBlank()) JSONObject() else JSONObject(text)
    }
}
