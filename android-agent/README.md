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

## Build

```bash
cd android-agent
./gradlew assembleDebug
```

Debug APK:

`app/build/outputs/apk/debug/app-debug.apk`

Or open this folder in Android Studio → **Sync Project with Gradle Files** → Run.

## Pair and stay online

1. Start the DeviceFlow API and dashboard; create a pairing code under **Devices**.
2. On the phone, enter `https://your-host/api/v1` (or `http://LAN_IP:8000/api/v1` for local) and the code.
3. Grant SMS, Phone, Notifications, and related permissions; disable battery optimization when prompted.
4. Start the agent service. Home should show **Online** / **Synced** when heartbeats succeed.

Default poll interval is about **3 seconds**; heartbeat about **15 seconds**.

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
