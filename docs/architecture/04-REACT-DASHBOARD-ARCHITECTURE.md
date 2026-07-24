# React Dashboard Architecture — DeviceFlow

**Status:** DRAFT  
**Stack:** React 19 · Vite · TypeScript · TanStack Query · Zustand (or Redux Toolkit) · React Router · Recharts · Tailwind + Design Tokens

---

## 1. Purpose

Provide a clear, bilingual (FA/EN), RTL-capable operations console for:

- Devices & health
- Messages & queues
- Projects & API keys
- Analytics
- Users & audit
- Live monitoring

---

## 2. App Structure

```
dashboard/
  src/
    app/                 # providers, router, layouts
    pages/               # route-level screens
    features/            # domain modules
      devices/
      messages/
      projects/
      analytics/
      settings/
      auth/
    shared/
      ui/                # design system components
      api/               # fetch client, endpoints
      ws/                # websocket client
      i18n/
      lib/
    styles/              # tokens, themes
```

Feature-first: each feature owns components, hooks, types.

---

## 3. Routing (sketch)

| Path | Page |
|------|------|
| `/login` | Auth |
| `/` | Overview / Live Monitor |
| `/devices` | Device list |
| `/devices/:id` | Device detail + timeline |
| `/messages` | Message explorer |
| `/messages/:id` | Message detail |
| `/inbox` | Inbound (Phase 2+) |
| `/queues` | Queue inspector |
| `/projects` | Projects |
| `/projects/:id` | Project settings, keys, webhooks |
| `/analytics` | Charts |
| `/users` | RBAC |
| `/audit` | Audit log |
| `/playground` | API playground |
| `/settings` | Tenant settings, notifications |

---

## 4. State Strategy

| Concern | Tool |
|---------|------|
| Server state | TanStack Query |
| Auth session | Secure cookie/memory + refresh |
| UI prefs (theme, locale) | Zustand + localStorage |
| Live overlays | WS → Query cache updates |

Avoid duplicating lists in global store.

---

## 5. API Client

- Base URL from env
- Interceptors: Bearer JWT, 401 → refresh → retry
- Error toast mapping via `error.code`
- OpenAPI-generated types optional later

---

## 6. WebSocket Integration

Connect after login:

1. Subscribe `tenant.{id}.dashboard`
2. On `device.health` → patch device query cache
3. On `message.updated` → patch message lists / detail
4. On `alert` → toast + notification center

Reconnect with exponential backoff; show connection pill in shell.

---

## 7. i18n & RTL

- `i18next` (or similar) with `fa` / `en`
- `dir="rtl"` when FA
- Vazirmatn for FA; pair Latin for EN (see Typography doc)
- All user-facing strings via keys — no hard-coded Persian/English in components

---

## 8. Layout Shell

```
┌──────────────────────────────────────────────┐
│ Topbar: brand, tenant switcher, WS status,   │
│         theme, locale, user menu             │
├──────────┬───────────────────────────────────┤
│ Sidebar  │  Page content                     │
│ nav      │                                   │
│          │                                   │
└──────────┴───────────────────────────────────┘
```

Dense data UI: tables first; cards only for interactive device tiles on Live Monitor.

---

## 9. Performance

- Virtualize long message tables
- Defer analytics charts
- Route-based code splitting
- Prefer server pagination

---

## 10. Related

- [Design System](../design/01-UI-UX-DESIGN-SYSTEM.md)
- [Wireframes](../design/08-DASHBOARD-WIREFRAMES.md)
- [WebSocket Protocol](../api/02-WEBSOCKET-PROTOCOL.md)
- [Folder Structure](../structure/01-FOLDER-STRUCTURE.md)
