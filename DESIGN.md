# DESIGN.md

Base design system for Persian (RTL) websites: deep-navy surfaces, soft cards, one green accent, one blue "attention" accent, pill controls and a big, heavy page title. Extracted from the reference at https://s.v1x.ir/.

This file is project-agnostic. Project-specific components live in separate files that extend it, e.g. DESIGN-vision.md.

---

## 1. Principles

1. Calm and readable. Low-contrast chrome, high-contrast content.
2. RTL-first. Persian is the primary language; layouts are authored right-to-left, not mirrored afterwards.
3. Mobile-first. Design for ~360px, then scale up.
4. Glanceable. The most useful fact (current status, coverage) is visible without interaction.
5. One screen, one job. No competing calls to action.

### The feel, in 8 rules

1. Dark navy page, with cards one step lighter and inner rows one step lighter again (tone, not shadows, creates depth).
2. Hairline borders on cards and controls; no drop shadows in dark mode.
3. Generous rounding: cards approx 1.5rem, inner rows approx 0.75rem, controls and badges fully pill-shaped.
4. Green marks identity and positive state (icons, status dot, title underline, filled indicators).
5. Blue marks attention (the next/active item), usually with a striped fill and a badge.
6. One oversized, heavy page title with a soft green underline bar.
7. Small muted metadata, bold primary text; Persian digits throughout.
8. Compact outlined pill controls (sample load, theme switcher) in the top bar.

## 2. Page setup

```html
<html lang="fa" dir="rtl">
<meta name="color-scheme" content="light dark">
<meta name="theme-color" media="(prefers-color-scheme: light)" content="#E9EFF5">
<meta name="theme-color" media="(prefers-color-scheme: dark)"  content="#0E1522">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
```

## 3. Color tokens

### Dark theme

| Token | Value | Use |
|---|---|---|
| --bg | #0E1522 | Page background |
| --surface | #151D2E | Cards |
| --surface-inset | #1E293D | Rows / items inside a card |
| --border | #243046 | Card and control outlines |
| --text | #F1F5F9 | Titles, primary text |
| --text-muted | #8B98AD | Metadata, labels, subtitle |
| --accent-green | #6FD0A0 | Icons, status dot, filled indicators, title underline |
| --accent-blue | #7F9BFF | Attention state: border, badge, highlighted text |
| --fill-muted | #2A3447 | Empty / inactive indicator fills |

### Light theme

| Token | Value | Use |
|---|---|---|
| --bg | #E9EFF5 | Page background |
| --surface | #FFFFFF | Cards |
| --surface-inset | #F1F5F9 | Rows / items inside a card |
| --border | #D3DDE8 | Card and control outlines |
| --text | #14202E | Titles, primary text |
| --text-muted | #5B6B7C | Metadata, labels, subtitle |
| --accent-green | #187A50 | Icons, status dot, filled indicators, title underline |
| --accent-blue | #3D5FD6 | Attention state: border, badge, highlighted text |
| --fill-muted | #D3DDE8 | Empty / inactive indicator fills |

```css
:root {
  --bg: #E9EFF5;
  --surface: #FFFFFF;
  --surface-inset: #F1F5F9;
  --border: #D3DDE8;
  --text: #14202E;
  --text-muted: #5B6B7C;
  --accent-green: #187A50;
  --accent-blue: #3D5FD6;
  --fill-muted: #D3DDE8;
}
:root[data-theme="dark"] {
  --bg: #0E1522;
  --surface: #151D2E;
  --surface-inset: #1E293D;
  --border: #243046;
  --text: #F1F5F9;
  --text-muted: #8B98AD;
  --accent-green: #6FD0A0;
  --accent-blue: #7F9BFF;
  --fill-muted: #2A3447;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #0E1522;
    --surface: #151D2E;
    --surface-inset: #1E293D;
    --border: #243046;
    --text: #F1F5F9;
    --text-muted: #8B98AD;
    --accent-green: #6FD0A0;
    --accent-blue: #7F9BFF;
    --fill-muted: #2A3447;
  }
}
```

## 4. Typography

- Font: Vazirmatn Persian sans; fallback system-ui, Tahoma, sans-serif.
- Numerals: Persian digits in all visible text; Latin digits in HTML attributes only.
- Line height: approx 1.7.

## 5. Accessibility & Motion

- Tap targets >= 44x44px.
- Visible :focus-visible on all interactive elements.
- State not encoded by color alone; text labels and badges included.
- Micro-interactions only: 150ms ease-out on hover / focus / press. No page-load animation.
