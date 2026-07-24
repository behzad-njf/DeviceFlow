# Docker & Docker Compose — DeviceFlow

**Status:** DRAFT

---

## 1. Purpose

One-command local stack for developers and simple VPS deploys.

---

## 2. Services (compose)

```yaml
services:
  postgres:
  redis:
  api:          # Django ASGI/WSGI
  worker:       # Celery worker
  beat:         # Celery beat
  dashboard:    # nginx serving built SPA (or vite in override)
  # optional: prometheus, grafana, mailhog
```

Networks: `internal`. Volumes: `pgdata`, `redisdata`, `media`.

---

## 3. Images

| Image | Context |
|-------|---------|
| `deviceflow-api` | `backend/Dockerfile` |
| `deviceflow-dashboard` | `dashboard/Dockerfile` |

Multi-stage builds; non-root user.

---

## 4. Env File

`.env.example` documents all vars — never commit real `.env`.

---

## 5. Commands (planned)

```bash
docker compose up -d
docker compose exec api python manage.py migrate
docker compose exec api python manage.py createsuperuser
```

---

## 6. Related

- [Kubernetes](./05-KUBERNETES.md)
- [Folder Structure](../structure/01-FOLDER-STRUCTURE.md)
