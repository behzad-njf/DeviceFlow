# UI/UX Design System — DeviceFlow

**Status:** DRAFT  
**Audience:** Dashboard (primary) · Agent UI (secondary, minimal)

---

## 1. Design Principles

1. **Clarity first** — operators must see status in < 2 seconds.
2. **One job per view** — avoid dashboard clutter and card spam.
3. **Data density with breathing room** — tables over decorative cards.
4. **RTL-native** — Persian is first-class, not mirrored as an afterthought.
5. **Status is color + text + icon** — never color alone.
6. **Trust** — enterprise calm; no playful spammy marketing chrome in ops UI.

---

## 2. Brand Signal

Product name **DeviceFlow** appears in shell topbar as primary identity.  
Console aesthetic: precise, industrial-communications — think network ops, not consumer social.

Avoid: purple-gradient AI clichés, cream-serif terracotta kitsch, newspaper dense chrome.

---

## 3. Layout

- App shell: topbar + sidebar + content
- Content max width for forms: 720px; for tables: full fluid
- Page header: title + short description + primary actions

---

## 4. Interaction

- Destructive actions: confirm modal
- Optimistic UI only when reversible
- Live data: subtle pulse on update, not constant animation noise
- Motion budget: 2–3 intentional motions (page fade, WS status, chart draw)

---

## 5. Accessibility

- WCAG AA contrast
- Focus rings visible
- Keyboard tables navigation
- `dir` and language switch preserve layout

---

## 6. Related

- [Design Tokens](./02-DESIGN-TOKENS.md)
- [Typography](./03-TYPOGRAPHY.md)
- [Color Palette](./04-COLOR-PALETTE.md)
- [Components](./05-COMPONENT-LIBRARY.md)
- [Themes](./06-THEMES.md)
- [Responsive](./07-RESPONSIVE-RULES.md)
- [Wireframes](./08-DASHBOARD-WIREFRAMES.md)
