# Responsive Rules — DeviceFlow

**Status:** DRAFT

---

## 1. Breakpoints

| Name | Min width | Shell behavior |
|------|-----------|----------------|
| `sm` | 640px | compact |
| `md` | 768px | sidebar collapsible |
| `lg` | 1024px | sidebar expanded |
| `xl` | 1280px | full density |
| `2xl` | 1536px | wide tables |

---

## 2. Rules

- **< md:** sidebar → drawer; tables → horizontal scroll or stacked key fields
- **Touch:** min hit target 40px for primary actions
- **Live Monitor:** device tiles 1 col → 2 → 3→4 grid
- **Analytics:** charts full width stacked on mobile
- Dashboard is **desktop-first** but usable on tablet for on-call ops

---

## 3. Agent App

Phone-native Compose; no desktop layout required.

---

## 4. Related

- [Wireframes](./08-DASHBOARD-WIREFRAMES.md)
