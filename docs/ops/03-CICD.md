# CI/CD Pipeline — DeviceFlow

**Status:** DRAFT

---

## 1. Goals

- Every commit: lint + unit tests
- Main branch: build images + deploy staging
- Tags: production release with approval

---

## 2. Pipelines by Component

### Backend

1. ruff / black check
2. mypy (optional gradual)
3. pytest
4. Docker build `deviceflow-api`
5. Migrate job on deploy

### Dashboard

1. eslint / tsc
2. vitest
3. build
4. Docker/nginx image or static upload

### Android

1. unit tests
2. assembleRelease (signing secrets in CI)
3. Publish APK to GitHub Releases / private store

---

## 3. Suggested GitHub Actions Workflows

- `ci-backend.yml`
- `ci-dashboard.yml`
- `ci-android.yml`
- `cd-staging.yml` (on main)
- `cd-prod.yml` (on tag `v*`)

---

## 4. Environments

| Env | Trigger | Notes |
|-----|---------|-------|
| Preview | PR | optional compose |
| Staging | main | auto |
| Production | tag + approval | manual gate |

---

## 5. Secrets

Never in repo: `DATABASE_URL`, `SECRET_KEY`, keystore passwords, Sentry DSN write tokens.

---

## 6. Related

- [Docker](./04-DOCKER.md)
- [Testing](./06-TESTING-STRATEGY.md)
