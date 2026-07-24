package ir.behzaaad.deviceflow.agent.contacts

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.provider.ContactsContract
import androidx.core.content.ContextCompat
import org.json.JSONArray
import org.json.JSONObject

/**
 * Read device phonebook entries for server-side import preview.
 * One row per phone number (contacts with multiple numbers expand).
 */
object ContactsReader {
    data class Result(
        val ok: Boolean,
        val contacts: JSONArray = JSONArray(),
        val errorCode: String? = null,
        val truncated: Boolean = false,
    )

    fun read(context: Context, limit: Int = 3000): Result {
        if (
            ContextCompat.checkSelfPermission(context, Manifest.permission.READ_CONTACTS) !=
            PackageManager.PERMISSION_GRANTED
        ) {
            return Result(ok = false, errorCode = "CONTACTS_PERMISSION_DENIED")
        }

        val out = JSONArray()
        val seen = HashSet<String>()
        var truncated = false

        try {
            val projection =
                arrayOf(
                    ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME,
                    ContactsContract.CommonDataKinds.Phone.NUMBER,
                )
            context.contentResolver.query(
                ContactsContract.CommonDataKinds.Phone.CONTENT_URI,
                projection,
                null,
                null,
                "${ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME} ASC",
            )?.use { cursor ->
                val nameIdx = cursor.getColumnIndex(ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME)
                val numberIdx = cursor.getColumnIndex(ContactsContract.CommonDataKinds.Phone.NUMBER)
                while (cursor.moveToNext()) {
                    if (out.length() >= limit) {
                        truncated = true
                        break
                    }
                    val name = if (nameIdx >= 0) cursor.getString(nameIdx).orEmpty().trim() else ""
                    val phone = if (numberIdx >= 0) cursor.getString(numberIdx).orEmpty().trim() else ""
                    if (phone.isBlank()) continue
                    val key = phone.filter { it.isDigit() || it == '+' }
                    if (key.isBlank() || !seen.add(key)) continue
                    out.put(
                        JSONObject()
                            .put("name", name)
                            .put("phone", phone),
                    )
                }
            }
        } catch (exc: SecurityException) {
            return Result(ok = false, errorCode = "CONTACTS_PERMISSION_DENIED")
        } catch (_: Exception) {
            return Result(ok = false, errorCode = "CONTACTS_READ_FAILED")
        }

        return Result(ok = true, contacts = out, truncated = truncated)
    }
}
