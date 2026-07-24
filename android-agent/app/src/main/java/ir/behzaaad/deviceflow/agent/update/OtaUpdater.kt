package ir.behzaaad.deviceflow.agent.update

/**
 * OTA helper stub for Phase 9.
 *
 * Backend sends DeviceCommand action = "install_update" with params:
 *   version, download_url, checksum_sha256, release_id
 *
 * Implement PackageInstaller flow here when building the Android agent.
 * Until then, use scripts/mock_agent.py which applies the version on ack.
 */
object OtaUpdater {
    data class UpdateRequest(
        val version: String,
        val downloadUrl: String,
        val checksumSha256: String = "",
    )

    fun parse(params: Map<String, Any?>): UpdateRequest? {
        val version = params["version"]?.toString() ?: return null
        val url = params["download_url"]?.toString() ?: return null
        return UpdateRequest(
            version = version,
            downloadUrl = url,
            checksumSha256 = params["checksum_sha256"]?.toString().orEmpty(),
        )
    }
}
