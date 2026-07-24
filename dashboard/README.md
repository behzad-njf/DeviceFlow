# DeviceFlow Dashboard

React + TypeScript + Vite control plane for DeviceFlow (English / فارسی).

## Setup

```bash
cd dashboard
npm install
cp .env.example .env   # optional; or set VITE_API_BASE_URL in the repo root .env
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). The API must be running (default `http://localhost:8000/api/v1`).

```bash
# .env
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

## Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Local Vite server with HMR |
| `npm run build` | Production build to `dist/` |
| `npm run preview` | Serve the production build |
| `npm run lint` | Oxlint |

## What it talks to

- REST: JWT login, devices, messages, projects, routing, analytics, …
- WebSocket: live device / command / SMS events (same origin or API host)

Full stack instructions: [../README.md](../README.md).
