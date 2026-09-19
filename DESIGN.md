---
name: Instrument
description: Sober Linear/Vercel-style profile. Neutral surfaces, one indigo accent, Geist, and morphing line icons that show the work instead of describing it.
version: "2.0"
colors:
  light: { bg: "#FFFFFF", tile: "#FAFAFA", line: "#E6E6E8", cell: "#EFEFF1", text: "#0A0A0B", muted: "#5F5F66", faint: "#707078", accent: "#4F5BD5" }
  dark:  { bg: "#0B0B0C", tile: "#141416", line: "#232326", cell: "#1C1C1F", text: "#EDEDEF", muted: "#A0A0A8", faint: "#7E7E86", accent: "#8E97FF" }
typography:
  sans: Geist (Regular, SemiBold), OFL, embedded as base64 woff2 subset
  mono: Geist Mono (Regular), OFL, embedded as base64 woff2 subset
---

# Instrument

## Principles

- **Neutral surfaces with one accent.** Everything is greyscale except the moving element, so the eye follows the motion.
- **Subtle, then still.** Only the hero and the project diagrams loop, slowly. Everything else plays once on arrival (`fill="freeze"`) and rests. Every animated element has a visible static base, so a renderer that never runs SMIL still shows the finished state.
- **The motion is the content.** Each animation shows what a project does: rows filling, data falling through lakehouse layers, a magnifier searching files, keys lighting up. Nothing is only decoration.
- **Quiet type.** Geist SemiBold with tight tracking (-0.025 to -0.03) for titles, Regular for body, and Mono for metadata and labels.

## Building blocks

| Asset | Size | Content |
|---|---|---|
| `hero` | 880×300 | Name, role and two-line thesis. The step rail (measure / validate / build / ship) is synced to a morph tile: BARS → CHECK → BOX → PLANE, 10s cycle. |
| `card-*` | 880×200 | A 152px diagram tile, title 32px, a one-line description at 21px, a mono meta line at 15px, and an ↗ arrow. |
| `focus` | 880×328 | "Now building": four tiles in a 2×2 grid (agents, knowledge, local-first, data). Static `muted` line glyphs. |
| `toolkit` | 880×n·68 | A ticker with one row per category (analytics / code / ai / data). Each row's band is defined once, repeated with `<use>`, and slid by `animateTransform` at 12 px/s. Rows alternate direction, and the edges fade out. |
| `credentials` | 880×… | Certification list. Accent checks draw once, in reading order, 250ms apart. Issuer logos sit right-aligned at 20px, in `muted`. |
| `signature` | w×150 | "Javier Rodeiro" in EMS Allure (OFL single-stroke script, `design/fonts/EMSAllure.svg`) smoothed with Catmull-Rom, plus a closing swash. A broad nib is faked by stacking the stroke 7× along 45° with `<use>`. Drawn once with `stroke-dashoffset` over 4.5s; transparent background. |
| `activity` | 880×292 | Live stats plus a 53×7 heatmap. Built from the GraphQL `contributionCalendar`. Cell opacity scales with the square root of the day's count. Cells are static; an accent scan column sweeps across them once, then fades. |

- **Logos:** `design/logos/`. Simple Icons (CC0, see `LICENSE-simple-icons.md`) plus official marks where they exist (Amplitude, Piwik PRO, Looker Studio, Google, Cambridge English, EF SET, Addocu). They are flattened to a single colour: all fills and styles are stripped, and the viewBox is cropped through `CROP`. A tool with no mark is shown as a label only. A card shows a project logo only when `design/logos/<name>.svg` exists.

- **Frame:** a 16px-radius rounded rect filled with `bg` and a 1px `line` stroke. Tiles use a 14px radius, filled with `tile`.
- **Easing:** `keySplines="0.65 0 0.35 1"` everywhere.
- **Morphs:** every shape is a closed polyline on a 24-unit grid. Each is resampled to 120 points (keeping its vertices) and normalised to clockwise order from the vertex nearest the top-left, so SMIL `d` interpolation stays clean.

## Rendering

- **GitHub limits:** GitHub strips CSS and JS from the README. Each image ships as a `-light` / `-dark` pair switched with `<picture><source media="(prefers-color-scheme: dark)">`. Fonts are embedded because SVGs inside `<img>` can't load external resources.
- **Mobile ceiling:** SVG text scales with the viewport, so card text is small at 390px. Anything that has to be readable on a phone (links, writing, path) stays in Markdown.

## Workflow

Edit `design/build.py`, then run:

```sh
uv run --with fonttools --with brotli design/build.py   # writes assets/*.svg
```

Don't hand-edit files in `assets/`; they are generated. The build calls `gh api graphql`, so `gh` has to be authenticated. `.github/workflows/activity.yml` runs the same build every day with `github.token` and commits `assets/` whenever the output changes.
