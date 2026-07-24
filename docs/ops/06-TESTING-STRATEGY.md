# Testing Strategy — DeviceFlow

**Status:** DRAFT

---

## 1. Pyramid

```
       E2E (few)
    Integration (some)
  Unit tests (many)
```

---

## 2. Backend

| Type | Tools | Focus |
|------|-------|-------|
| Unit | pytest | routing, rate limit, state machine |
| API | pytest-django / DRF | endpoints, authz |
| Task | celery eager | retries, webhooks |
| Contract | schemathesis optional | OpenAPI |

Coverage target: critical paths ≥ 80%.

---

## 3. Dashboard

| Type | Tools |
|------|-------|
| Unit | vitest + testing-library |
| Visual | optional Playwright component |
| E2E | Playwright against staging |

---

## 4. Android

| Type | Tools |
|------|-------|
| Unit | JUnit | queue, parsers |
| Instrumented | Espresso | pairing UI |
| Manual | device lab | real SMS |

Fake `SmsGateway` interface for CI.

---

## 5. E2E Scenarios (must-pass before release)

1. Pair device (mock agent OK for CI)
2. Send SMS → status updates
3. Rate limit returns 429
4. RBAC denies viewer send
5. Webhook signed delivery (wiremock)

---

## 6. Related

- [CI/CD](./03-CICD.md)
- [Performance](./07-PERFORMANCE.md)
