# Light / Dark Theme — DeviceFlow

**Status:** DRAFT

---

## 1. Mechanism

`data-theme="light" | "dark"` on `<html>`.  
User preference stored; default follow system.

---

## 2. Token Mapping

All colors from [Color Palette](./04-COLOR-PALETTE.md) exposed as CSS variables:

```css
:root {
  --bg-canvas: ...;
  --brand-500: ...;
}
[data-theme="dark"] {
  --bg-canvas: ...;
}
```

Components consume variables only — no hard-coded hex in feature code.

---

## 3. Charts & Maps

Provide dual palettes; grid lines use `--border`.

---

## 4. Agent App

Same brand teal; support system dark mode via Compose `MaterialTheme` color scheme aligned to tokens.

---

## 5. Related

- [Design Tokens](./02-DESIGN-TOKENS.md)
- [UI/UX](./01-UI-UX-DESIGN-SYSTEM.md)
