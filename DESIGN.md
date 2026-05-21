---
name: Signal
description: Clean, data-driven identity for a developer profile rooted in precision, clarity, and quiet confidence.
version: "1.0"
colors:
  primary: "#0F172A"
  on-primary: "#F8FAFC"
  secondary: "#475569"
  accent: "#6366F1"
  accent-glow: "#818CF8"
  surface: "#1E293B"
  on-surface: "#E2E8F0"
  muted: "#64748B"
  border: "#334155"
  success: "#22C55E"
typography:
  h1:
    fontFamily: Fira Code
    fontSize: 28px
    fontWeight: 700
  h2:
    fontFamily: Fira Code
    fontSize: 22px
    fontWeight: 600
    letterSpacing: -0.02em
  body:
    fontFamily: Inter, system-ui, sans-serif
    fontSize: 16px
    lineHeight: 1.6
  caption:
    fontFamily: Inter, system-ui, sans-serif
    fontSize: 12px
    fontWeight: 500
    letterSpacing: 0.05em
  mono:
    fontFamily: Fira Code, monospace
    fontSize: 14px
rounded:
  sm: 4px
  md: 8px
  lg: 12px
  full: 9999px
spacing:
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
  "2xl": 48px
components:
  header-wave:
    backgroundColor: gradient
    height: 120px
    typography: h1
  stat-card:
    backgroundColor: transparent
    borderColor: "{colors.border}"
    rounded: "{rounded.md}"
  badge-tech:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.on-surface}"
    rounded: "{rounded.md}"
  trophy-row:
    layout: center
    gap: "{spacing.sm}"
  section-divider:
    height: 1px
    backgroundColor: "{colors.border}"
  footer-wave:
    backgroundColor: gradient
    height: 120px
---

## Overview

**Signal** is a visual identity built for technical credibility. It communicates rigor without stiffness — the aesthetic of a well-architected dashboard rendered in dark mode. Deep slate surfaces with an indigo accent that signals intelligence, not decoration.

### Brand & Style

- **Precision over flair.** Every element earns its place. No gratuitous animation.
- **Dark-first.** The surface layer (`#1E293B`) provides depth; the accent (`#6366F1`) provides direction.
- **Monospace authority.** Fira Code for headings establishes technical competence. Inter for body ensures readability.
- **Live data, not static decoration.** Widgets are dynamic SVGs that update on every profile view — the profile breathes.

## Colors

The palette is anchored in cool slates with a single indigo accent. This avoids the rainbow-spectrum chaos common in developer profiles and projects a unified, deliberate identity.

- **Primary (`#0F172A`):** Deep navy for the base — used in stat card backgrounds, section headers.
- **Accent (`#6366F1`):** Indigo-500. The sole interaction color. Typing SVGs, link highlights, visitor counter, badge borders.
- **Accent-Glow (`#818CF8`):** Indigo-400. Used where the accent needs to be softer — hover states, secondary highlights.
- **Surface (`#1E293B`):** Slate-800. Card backgrounds, badge fills, widget containers.
- **On-Surface (`#E2E8F0`):** Slate-200. Primary text on dark surfaces.
- **Muted (`#64748B`):** Slate-500. Secondary text, dates, metadata.
- **Border (`#334155`):** Slate-700. Subtle dividers and card borders.
- **Success (`#22C55E`):** Reserved for contribution-streak indicators and positive signals.

## Typography

Two typefaces, two roles. Fira Code (monospace) for anything that needs technical authority — headings, stats, code. Inter for everything the reader needs to scan quickly — body text, descriptions, labels.

- **h1:** Fira Code, 28px, weight 700. Profile name and section titles.
- **h2:** Fira Code, 22px, weight 600, -0.02em letter-spacing. Subsection headers.
- **body:** Inter, 16px, 1.6 line-height. Professional summary, descriptions.
- **caption:** Inter, 12px, weight 500, 0.05em letter-spacing. Badges, dates, metadata.
- **mono:** Fira Code, 14px. Inline code references, stat labels.

## Layout & Spacing

The README follows a single-column, center-aligned layout with clear horizontal rules between major sections:

```
[wave header — full width]
[profile intro — centered]
[--- divider ---]
[professional summary — 720px max width]
[--- divider ---]
[tech stack badges — centered grid]
[--- divider ---]
[2-col stat grid: stats | streak]
[2-col stat grid: languages | activity graph]
[trophy row — centered]
[--- divider ---]
[featured work]
[--- divider ---]
[education & certifications — centered tables]
[--- divider ---]
[connect — centered grid]
[wave footer — full width]
```

- **Max content width:** 720px (matches GitHub's rendered README readability sweet spot)
- **Section gaps:** 48px (`{spacing.2xl}`)
- **Card gaps:** 16px (`{spacing.md}`)
- **Divider:** 1px solid `{colors.border}`

## Shapes

- **Rounded sm (4px):** Tight corners — badges, inline code
- **Rounded md (8px):** Cards, stat widgets, tables
- **Rounded lg (12px):** Featured project images
- **Rounded full (9999px):** Profile avatar, pill badges

## Components

### stat-card
- Background: transparent (rendered by external SVG widgets)
- All stat widgets use `hide_border=true` for a borderless, seamless look
- Theme: `tokyonight` applied consistently across github-readme-stats, streak-stats, activity-graph, and trophy

### badge-tech
- Style: `for-the-badge` from shields.io
- Background: color derived from each technology's brand hex
- Consistent height (28px) for grid alignment
- Grouped by category: Development, Data & Analytics, AI

### section-divider
- HTML `<hr>` or three dashes `---`
- 1px height, `{colors.border}` color
- 24px vertical margin

### header-wave / footer-wave
- Capsule Render API with `type=waving`, `color=gradient` (primary → accent)
- Height: 120px for header, 100px for footer
- Acts as visual bookends — no content within them

## Do's and Don'ts

- **Do** align ALL stat widgets with the same theme parameter (`theme=tokyonight`)
- **Do** use `hide_border=true` on every stat widget for seamless integration
- **Do** wrap widget pairs in `<p align="center">` for 2-column grid layout
- **Do** keep donation/sponsor CTAs to a single line at the bottom
- **Do** use `<!-- comments -->` as anchors for GitHub Actions content injection
- **Don't** mix widget themes — inconsistency looks sloppy
- **Don't** use more than 4 stat widgets in a single row — wrap at 2 columns
- **Don't** embed heavy GIFs that slow down profile load time
- **Don't** hide contact information at the bottom without a top-level link
- **Don't** use animated elements that distract from content scanning
