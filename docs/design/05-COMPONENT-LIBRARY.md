# Component Library — DeviceFlow

**Status:** DRAFT

---

## 1. Foundations

- Button (primary, secondary, ghost, danger; sm/md)
- Input, Textarea, Select, Checkbox, Switch
- FormField (label, hint, error)
- Badge / StatusChip
- Icon (Lucide or similar)
- Tooltip, Modal, Drawer, Dropdown
- Toast
- Tabs
- Table (sortable, filterable, virtualized)
- Pagination
- EmptyState
- Skeleton
- PageHeader
- Stat (for analytics — not hero clutter)

---

## 2. Domain Components

| Component | Description |
|-----------|-------------|
| `DeviceStatusDot` | online/offline/busy |
| `DeviceCard` | Live monitor tile (interactive → allowed card) |
| `HealthScore` | 0–100 + stars |
| `SimBadge` | operator + slot |
| `MessageStatusChip` | lifecycle states |
| `QueueMeter` | pending/sending bars |
| `EventTimeline` | device activity |
| `JsonViewer` | playground / payload |
| `ApiKeyReveal` | show-once pattern |
| `LiveConnectionPill` | WS connected |
| `TenantSwitcher` | |
| `CommandPalette` | optional Ctrl+K |

---

## 3. Charts

Wrap Recharts: Line, Bar, Area with token colors; no default Inter look — inherit Vazirmatn.

---

## 4. Do / Don’t

- **Do** use tables for messages
- **Don’t** wrap every metric in a shadowed card grid on first paint of Live Monitor beyond device tiles
- **Don’t** use emoji as primary status indicators (icons OK)

---

## 5. Related

- [Wireframes](./08-DASHBOARD-WIREFRAMES.md)
- [Design Tokens](./02-DESIGN-TOKENS.md)
