---
title: GitHub profile README
topics: [architecture, profile]
sources:
  - id: design-build
    type: file
    path: design/build.py
  - id: design-profile
    type: file
    path: design/profile.py
  - id: design-page
    type: file
    path: design/page.py
  - id: design-morph
    type: file
    path: design/morph.mjs
  - id: design-morphs
    type: file
    path: design/morphs.json
  - id: test-activity
    type: file
    path: design/test_activity.py
  - id: workflow-activity
    type: file
    path: .github/workflows/activity.yml
  - id: design-contract
    type: file
    path: DESIGN.md
  - id: readme-skill
    type: file
    path: .claude/skills/readme-design/SKILL.md
  - id: profile-readme
    type: file
    path: README.md
  - id: transcript-e7888b3f
    type: conversation
    path: /Users/jrodeiro/.claude/projects/-Users-jrodeiro-dev-work-jrodeiro5/e7888b3f-0220-48a7-8fc2-872352f74f87.jsonl
  - id: transcript-b558b59f
    type: conversation
    path: /Users/jrodeiro/.claude/projects/-Users-jrodeiro-dev-work-jrodeiro5/b558b59f-aa8c-4352-9967-b3557749e67c.jsonl
---

# GitHub profile README

The repository root `README.md` is not project documentation; it is the rendered GitHub profile. It is a thin Markdown shell around a set of generated SVGs in `assets/`, each produced by the `design/` folder. This page explains how those SVGs are built, why they are constrained the way they are, and how they stay fresh.

## Two entry points

`design/profile.py` generates the four GitHub-data sections — `stats`, `about`, `milestones`, `stacks` — by querying the GraphQL API with `gh api`, so it must run authenticated as the profile owner to see private contributions. It writes `stats-{light,dark}.svg`, `about-*`, `milestones-*`, and `stacks-*`, then prints a one-line summary. `[@design-profile]`

`design/build.py` is the "diary" visual system and holds the remaining builders — `hero`, `card`, `ticker` (the toolkit band), `credentials`, `focus`, `activity`, and `signature`. `profile.py` reuses `build.py` for fonts, text helpers, and logos, so the two files share the type layer. `[@design-build]` `design/page.py` renders the live activity page (blog feed plus contribution calendar) and is reused by `build.py`. `[@design-page]`

## The constraint is the whole design

GitHub renders these SVGs as `<img>`, which strips CSS, JavaScript, and external fonts and only honours `prefers-color-scheme`. Every fact below follows from that single fact:

- Fonts are base64-encoded woff2 subsets embedded by `woff2()`, so each SVG carries roughly 45–60 KB of embedded type. `[@design-contract][@design-build]`
- Theme switching is `<picture><source media="(prefers-color-scheme: dark)">`, so every asset ships as a `-light`/`-dark` pair with no third state. `[@design-contract][@profile-readme]`
- Motion is hand-written SMIL (`<animate>`), because GitHub strips JavaScript. The morphs are the one exception handled specially: `design/morph.mjs` bakes morphicons' spring physics into `design/morphs.json`, and each morph pair gets its own `<path>` because SMIL interpolates only between `d` values with identical structure. `[@design-morph][@design-morphs]`
- Every animated element keeps a visible static base. Renderers that ignore SMIL — GitHub's own image cache, social previews, RSS — must still show the finished frame, so dash offsets start at the drawn value and `fill="freeze"` is used. `[@design-contract]`
- SVG text does not reflow. At a 390px viewport the 880px canvas scales down about 2.25×, so anything that must stay readable on a phone lives in the Markdown, not in an SVG. `[@design-contract]`
- Geometry is repeated with `<use>` rather than duplicated, which is what reduced the toolkit from 155 KB to 91 KB. Logos come from `design/logos/` (Simple Icons CC0 plus official marks) flattened to one fill; a missing mark renders as a text label, so a missing logo means adding the SVG, not faking a label. `[@design-contract][@readme-skill]`

## Two bugs the code guards against

`design/test_activity.py` exists because the activity card's failure mode is silent: playback hides everything at t=0 and reveals it on a schedule, so a bug leaves an empty card for every SMIL-less renderer while looking correct in a browser. The test parses the SVG and asserts what a renderer without SMIL draws — one visible odometer value (the final one), week columns at full opacity, a year of cells, a playback that starts at 0s and ends inside the card, and a counter whose final value equals the `aria-label` total. `[@test-activity]`

`build.py` deliberately does not read `contributionCalendar.totalContributions`: on this account it reports 2,613 against 2,507 summed across the 365 day cells the same response returns. The counter walks the grid week by week, so it must agree with the grid rather than with a figure no cell accounts for. `[@design-build]`

## Keeping it fresh

`.github/workflows/activity.yml` runs `design/profile.py` at 05:17 UTC (and on demand) with `secrets.PROFILE_TOKEN`, then commits and pushes refreshed `assets/` only when they changed. The token makes the run authenticated, which is what lets it see private contributions. `[@workflow-activity]`

The build loop — `uv run --with fonttools --with brotli design/build.py`, then render the output in both themes — and the "never edit `assets/*.svg`" rule are documented in the project `readme-design` skill, which points at the spec `DESIGN.md`. `[@readme-skill]` The design narrative that shaped this system — the Hong Kong 90s "melancholy night" direction, the hand-written signature, and the switch from a hand-made morph to baked morphicons — came from the sessions that produced it. `[@transcript-e7888b3f][@transcript-b558b59f]`
