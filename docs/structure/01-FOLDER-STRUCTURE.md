# Folder Structure — DeviceFlow

**Status:** DRAFT  
**Note:** Target structure for implementation phases (repo is docs-only now).

---

## 1. Monorepo Layout

```
SMSGateway/
├── README.md
├── docs/                          # ← you are here (blueprint)
├── prompts/                       # top-level shortcut prompts (optional)
├── backend/
│   ├── manage.py
│   ├── pyproject.toml / requirements/
│   ├── Dockerfile
│   ├── config/
│   │   ├── settings/
│   │   ├── urls.py
│   │   ├── asgi.py
│   │   ├── celery.py
│   │   └── wsgi.py
│   └── apps/
│       ├── accounts/
│       ├── tenants/
│       ├── projects/
│       ├── devices/
│       ├── messaging/
│       ├── routing/
│       ├── analytics/
│       ├── notifications/
│       ├── webhooks/
│       ├── audit/
│       ├── plugins/
│       └── common/
├── dashboard/
│   ├── package.json
│   ├── vite.config.ts
│   ├── index.html
│   ├── Dockerfile
│   └── src/
│       ├── app/
│       ├── pages/
│       ├── features/
│       ├── shared/
│       └── styles/
├── android-agent/
│   ├── settings.gradle.kts
│   ├── build.gradle.kts
│   └── app/
│       └── src/main/java/.../ 
├── deploy/
│   ├── docker-compose.yml
│   ├── docker-compose.override.yml
│   └── k8s/
├── scripts/
└── .github/workflows/
```

---

## 2. Docs Layout (current)

```
docs/
├── 00-INDEX.md
├── 01-VISION-AND-PRODUCT-STRATEGY.md
├── 02-PRD.md
├── architecture/
├── api/
├── security/
├── ops/
├── design/
├── structure/
├── roadmap/
│   └── phases/
├── agents/
│   └── prompts/
└── steps/
```

---

## 3. Naming Conventions

| Area | Convention |
|------|------------|
| Python | `snake_case` modules |
| TS | `PascalCase` components, `camelCase` hooks |
| Kotlin | package `com.deviceflow.agent` |
| DB tables | `app_model` Django default |

---

## 4. Related

- [Backend Architecture](../architecture/02-BACKEND-ARCHITECTURE.md)
- [Android Agent](../architecture/03-ANDROID-AGENT-ARCHITECTURE.md)
- [React Dashboard](../architecture/04-REACT-DASHBOARD-ARCHITECTURE.md)
