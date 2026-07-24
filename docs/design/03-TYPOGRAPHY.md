# Typography — Vazirmatn — DeviceFlow

**Status:** DRAFT

---

## 1. Font Families

| Role | FA | EN |
|------|----|----|
| Primary UI | **Vazirmatn** | Vazirmatn (excellent Latin) or **IBM Plex Sans** as optional EN pairing |
| Mono (IDs, JSON) | **JetBrains Mono** / **IBM Plex Mono** | same |

Load Vazirmatn via self-host (variable font preferred) for performance and RTL integrity.

---

## 2. Type Scale

| Token | Size | Weight | Line height | Use |
|-------|------|--------|-------------|-----|
| `display` | 32 | 700 | 1.2 | rare page heroes |
| `h1` | 24 | 700 | 1.3 | page title |
| `h2` | 20 | 600 | 1.35 | section |
| `h3` | 16 | 600 | 1.4 | card/section sub |
| `body` | 14 | 400 | 1.5 | default |
| `body-sm` | 13 | 400 | 1.45 | table secondary |
| `caption` | 12 | 500 | 1.4 | labels, meta |
| `mono` | 12–13 | 400 | 1.4 | IDs |

Ops UI defaults to **14px body** for density.

---

## 3. Persian Rules

- Use Vazirmatn for all FA strings
- Avoid mixing Tahoma accidental fallbacks
- Numbers: prefer tabular lining in tables (`font-variant-numeric: tabular-nums`)
- Message bodies may contain mixed scripts — preserve unicode

---

## 4. Related

- [Design System](./01-UI-UX-DESIGN-SYSTEM.md)
- [Themes](./06-THEMES.md)
