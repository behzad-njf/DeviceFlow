# DeviceFlow Android Agent

<p align="center">
  <img src="../Images/Icon.png" alt="DeviceFlow agent icon" width="96" />
</p>

Kotlin + Jetpack Compose app that turns a phone into a DeviceFlow SMS / automation agent.

## Capabilities

- Pair with a dashboard pairing code and server URL
- Foreground service: heartbeat + poll pending SMS / control commands
- Send and receive SMS; ack command results
- USSD (with Accessibility on some OEMs), contacts read, OTA hook
- App security: hide launcher icon, UI passcode, customizable dialer reopen code (`*#*#CODE#*#*`)

## Requirements

- Android Studio (or JDK 11+ for CLI Gradle)
- Physical device recommended (SMS + dialer secret codes)
- API reachable from the phone (LAN IP or public HTTPS host)

## Build (debug)

```bash
cd android-agent
./gradlew assembleDebug
```

Output APK:

`app/build/outputs/apk/debug/app-debug.apk`

Or open this folder in Android Studio → **Sync Project with Gradle Files** → Run.

## Signed release build

1. Create a keystore (once — keep it safe; losing it blocks Play updates):

```bash
cd android-agent
mkdir -p keystore
keytool -genkeypair -v \
  -keystore keystore/deviceflow-release.jks \
  -keyalg RSA -keysize 2048 -validity 10000 \
  -alias deviceflow
```

2. Add credentials (gitignored):

```bash
cp keystore.properties.example keystore.properties
# edit storePassword / keyAlias / keyPassword
```

`keystore.properties` example:

```properties
storeFile=keystore/deviceflow-release.jks
storePassword=YOUR_STORE_PASSWORD
keyAlias=deviceflow
keyPassword=YOUR_KEY_PASSWORD
```

3. Build signed APK or App Bundle:

```bash
./gradlew assembleRelease          # APK
./gradlew bundleRelease            # AAB (Play Store)
```

Outputs:

- `app/build/outputs/apk/release/app-release.apk`
- `app/build/outputs/bundle/release/app-release.aab`

Never commit `keystore.properties`, `*.jks`, or `*.keystore`.

## Pair and stay online

1. Start the DeviceFlow API and dashboard; create a pairing code under **Devices**.
2. On the phone, enter `https://your-host/api/v1` (or `http://LAN_IP:8000/api/v1` for local) and the code.
3. Grant SMS, Phone, Notifications, and related permissions; disable battery optimization when prompted.
4. On Xiaomi/Huawei/Oppo, enable **Autostart** and lock the app in Recents. The agent starts after reboot and a 15‑minute watchdog restarts the foreground service if the OS kills it.
5. Start the agent service. Home should show **Online** / **Synced** when heartbeats succeed.

Default poll interval is about **3 seconds**; heartbeat about **15 seconds**.

### 0.3.1

- Removed local "last 10 messages" history UI (counters remain).
- Boot receiver + task-removed / destroy restart + AlarmManager watchdog for background survival.
- Optional per-customer `route_key` routing is handled server-side; agent unchanged for send payload.

## Hide icon / reopen

When the launcher icon is hidden (from the app or dashboard):

- Dial `*#*#CODE#*#*` in the Phone app (default `CODE` is `3323`).
- Change `CODE` under **App security** on the phone or **Change dialer code** in the dashboard.
- Or use **Show launcher** from the dashboard.

The foreground notification can still open the app; the agent service keeps running while the UI is locked.

## Sync with the backend

| Direction | Mechanism |
|-----------|-----------|
| Phone → server | `POST /agent/heartbeat/` (health, SIMs, GPS, security flags) |
| Server → phone | `GET /agent/commands/pending/` then `POST .../ack/` |
| SMS status | Agent reports sent / failed / inbound to the API |

See the root [README.md](../README.md) for running the full stack.
