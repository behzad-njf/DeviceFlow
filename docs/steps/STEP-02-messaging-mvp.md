# STEP-02 — Messaging MVP Checklist

- [x] `devices` + `projects` + `messaging` models
- [x] Pairing code issue + agent pair endpoint
- [x] Device token auth
- [x] Agent heartbeat (REST and/or WS)
- [x] Message create + states queued→sending→sent/failed
- [x] Agent send SMS + status callback
- [x] Inbound SMS ingest
- [x] Dual SIM fields
- [x] Basic retry worker
- [x] Dashboard: devices, messages, pair modal
- [ ] Manual E2E on device (user: Android Studio build / mock agent)

**Exit:** PH-02 exit criteria met (API + mock agent path verified by tests; physical device pending user build).
