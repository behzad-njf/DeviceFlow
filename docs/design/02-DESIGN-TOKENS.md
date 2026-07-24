# Design Tokens — DeviceFlow

**Status:** DRAFT

---

## 1. Spacing Scale (px)

| Token | Value |
|-------|-------|
| `space-0` | 0 |
| `space-1` | 4 |
| `space-2` | 8 |
| `space-3` | 12 |
| `space-4` | 16 |
| `space-5` | 24 |
| `space-6` | 32 |
| `space-7` | 48 |
| `space-8` | 64 |

---

## 2. Radius

| Token | Value | Use |
|-------|-------|-----|
| `radius-sm` | 4 | inputs, chips |
| `radius-md` | 8 | buttons, panels |
| `radius-lg` | 12 | modals |
| `radius-full` | 9999 | avatars only — avoid pill overload |

---

## 3. Elevation

| Token | Light | Dark |
|-------|-------|------|
| `elev-0` | none | none |
| `elev-1` | soft shadow | subtle border glow via border, not neon |
| `elev-2` | modal shadow | stronger border |

Prefer borders over multi-layer shadows.

---

## 4. Motion

| Token | Value |
|-------|-------|
| `duration-fast` | 120ms |
| `duration-normal` | 200ms |
| `duration-slow` | 320ms |
| `ease-standard` | cubic-bezier(0.2, 0, 0, 1) |

---

## 5. Z-Index

`dropdown 1000` · `sticky 1020` · `modal 1040` · `toast 1060`

---

## 6. Implementation

CSS variables in `:root` and `[data-theme="dark"]`; Tailwind maps to tokens.

See [Themes](./06-THEMES.md).
