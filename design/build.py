"""Generate the profile README SVGs (light + dark) into ../assets.

Run:  uv run --with fonttools --with brotli design/build.py
"""

import base64
import io
import json
import math
import re
import subprocess
from datetime import date
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent
OUT = ROOT.parent / "assets"
FONTS = ROOT / "fonts"
LOGOS = ROOT / "logos"
USER = "jrodeiro5"

# One page of the same diary, under two lights. Light is the page in daylight: aged cream, iron-gall
# ink gone brown at the edges. Dark is the same page by candle — the paper falls into shadow and the
# ink is what catches the light, which is why it inverts. A diary has no dark mode; a room does.
# `accent` is the ruled margin in both, and it is the only red on the page.
THEMES = {
    "dark": dict(bg="#191309", tile="#221A0F", line="#3A2E1D", cell="#241C11",
                 text="#E3D8BC", muted="#A2957A", faint="#6E6450", accent="#8E3B31",
                 stain="#4A3A1E", shade="#0A0703", grain=".085", vig=".62"),
    "light": dict(bg="#EDE3CC", tile="#E5D9BE", line="#CFC0A0", cell="#E0D3B6",
                  text="#25283C", muted="#5E5A55", faint="#928975", accent="#973A34",
                  stain="#C7A87A", shade="#8A7A5C", grain=".05", vig=".30"),
}

EASE = "0.65 0 0.35 1"  # in-out, used for eased moves

# --------------------------------------------------------------------------- fonts

CHARS = "".join(chr(c) for c in range(0x20, 0x7F)) + "ñ·—’é"


def woff2(name: str) -> str:
    # recalcTimestamp=False keeps head.modified from the source font. Otherwise every build
    # stamps "now" into the woff2, every embedded font blob changes, and the daily workflow
    # commits all 18 SVGs whether or not anything actually moved.
    font = TTFont(FONTS / name, recalcTimestamp=False)
    opts = subset.Options()
    opts.flavor = "woff2"
    opts.layout_features = ["kern", "liga", "calt", "tnum"]
    sub = subset.Subsetter(opts)
    sub.populate(text=CHARS)
    sub.subset(font)
    buf = io.BytesIO()
    font.flavor = "woff2"
    font.save(buf)
    return base64.b64encode(buf.getvalue()).decode()


# EB Garamond, instanced from the variable OFL release to static weights. A 1940s diary is set in a
# Garamond-family old-style face, and the italic is a separate design rather than a slanted roman —
# which is what lets the italic read as a second voice (the hand) against the roman (the print).
# `G`/`GS`/`GM` are kept as the key names so every existing builder keeps working.
FACES = {
    "G": ("EBGaramond-Regular.ttf", 400),
    "GS": ("EBGaramond-Medium.ttf", 500),
    "GM": ("EBGaramond-Italic.ttf", 400),
}
FONT_CSS = {k: f"@font-face{{font-family:{k};src:url(data:font/woff2;base64,{woff2(f)}) format('woff2');font-weight:{w}}}"
            for k, (f, w) in FACES.items()}
STACK = {"G": "G,'Iowan Old Style','Palatino Linotype',Georgia,serif",
         "GS": "GS,'Iowan Old Style','Palatino Linotype',Georgia,serif",
         "GM": "GM,'Iowan Old Style',Georgia,serif"}


_ADV = {}


def width(s, size, face="G"):
    """Advance width of `s` in px, from the font's own metrics (for laying out rows of text)."""
    if face not in _ADV:
        f = TTFont(FONTS / FACES[face][0])
        cmap, hmtx, upm = f.getBestCmap(), f["hmtx"], f["head"].unitsPerEm
        _ADV[face] = ({ch: hmtx[cmap[ord(ch)]][0] / upm for ch in CHARS if ord(ch) in cmap})
    return sum(_ADV[face].get(ch, 0.6) for ch in s) * size


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


GUTTER = 26  # width of the spine shadow; also the left edge every page lays its margin against


def svg(w, h, title, body, c, faces=("G", "GS", "GM"), rules=None, stains=((0.82, 0.22, 0.13),)):
    """Every asset is one leaf of the same book, not a card. Three things do all the work:

    - **square corners and no frame.** A rounded stroked rectangle is the single detail that reads
      as UI; paper has neither. This is what stops the sections looking like tiles.
    - **the spine gutter** on the left: the dark gradient where a bound page curves into the
      binding. It is the cheapest detail that says "book" rather than "rectangle".
    - **foxing** (`stains`): the rust blooms age leaves in, placed in fractions of the leaf as
      (x, y, radius). They are fixed per asset, never random, so rebuilds stay byte-identical.

    `rules` is the feint horizontal ruling — a y-step in px, or None for an unruled leaf. The grain
    sits above the content because paper tooth is in front of the ink, not behind it."""
    css = "".join(FONT_CSS[f] for f in faces)
    css += "".join(f".{f}{{font-family:{STACK[f]}}}" for f in faces)
    css += "text{font-kerning:normal}"
    fox = "".join(f'<ellipse cx="{fx * w:.0f}" cy="{fy * h:.0f}" rx="{fr * w:.0f}" '
                  f'ry="{fr * w * 0.74:.0f}" fill="url(#fox)"/>' for fx, fy, fr in stains)
    rule = ""
    if rules:
        rule = "".join(f'<line x1="{GUTTER + 22}" y1="{y}" x2="{w - 34}" y2="{y}" '
                       f'stroke="{c["line"]}" stroke-opacity=".5"/>'
                       for y in range(rules, h - 20, rules))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'role="img" aria-label="{esc(title)}"><title>{esc(title)}</title><style>{css}</style>'
            f'<defs>'
            f'<linearGradient id="spine" x1="0" x2="1" y1="0" y2="0">'
            f'<stop offset="0" stop-color="{c["shade"]}" stop-opacity=".40"/>'
            f'<stop offset=".45" stop-color="{c["shade"]}" stop-opacity=".10"/>'
            f'<stop offset="1" stop-color="{c["shade"]}" stop-opacity="0"/></linearGradient>'
            f'<radialGradient id="fox"><stop offset="0" stop-color="{c["stain"]}" stop-opacity=".30"/>'
            f'<stop offset=".6" stop-color="{c["stain"]}" stop-opacity=".10"/>'
            f'<stop offset="1" stop-color="{c["stain"]}" stop-opacity="0"/></radialGradient>'
            # the leaf is darker where it has been handled: the outer edge and the corners
            f'<radialGradient id="vig" cx=".5" cy=".45" r=".80">'
            f'<stop offset=".5" stop-color="{c["shade"]}" stop-opacity="0"/>'
            f'<stop offset="1" stop-color="{c["shade"]}" stop-opacity="{c["vig"]}"/></radialGradient>'
            f'<filter id="grain" x="0" y="0" width="100%" height="100%">'
            f'<feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="2" stitchTiles="stitch"/>'
            f'<feColorMatrix type="saturate" values="0"/></filter>'
            # wet ink sinks into the fibre: a blur merged *under* the glyph keeps the letterform
            # sharp and only spreads the halo, which is what iron-gall does on soft paper.
            f'<filter id="bloom" x="-50%" y="-50%" width="200%" height="200%">'
            f'<feGaussianBlur stdDeviation="1.6" result="b"/><feMerge><feMergeNode in="b"/>'
            f'<feMergeNode in="SourceGraphic"/></feMerge></filter></defs>'
            f'<rect width="{w}" height="{h}" fill="{c["bg"]}"/>'
            f"{fox}{rule}"
            # the ruled margin, the one red on the leaf
            f'<line x1="{GUTTER + 22}" y1="0" x2="{GUTTER + 22}" y2="{h}" stroke="{c["accent"]}" '
            f'stroke-opacity=".34"/>'
            f"{body}"
            f'<rect width="{w}" height="{h}" fill="url(#vig)"/>'
            f'<rect width="{GUTTER}" height="{h}" fill="url(#spine)"/>'
            f'<rect width="{w}" height="{h}" filter="url(#grain)" opacity="{c["grain"]}" '
            f'style="mix-blend-mode:overlay"/></svg>')


def text(x, y, s, size, fill, face="G", anchor="start", track=0.0, extra=""):
    ls = f' letter-spacing="{track * size:.2f}"' if track else ""
    return (f'<text x="{x}" y="{y}" class="{face}" font-size="{size}" fill="{fill}" '
            f'text-anchor="{anchor}"{ls}{extra}>{esc(s)}</text>')


_WIPE = [0]


def written(el, x, y, w, h, t0, dur=0.9):
    """Lay `el` down left to right, the way a pen does. A mask whose rect grows from zero — not a
    fade, because a fade is a UI transition and a nib is a moving point.

    The rect carries its full width in the attribute and is zeroed by `<set>` at 0s, so a renderer
    that ignores SMIL opens the mask completely and draws the finished line. That is the same
    static-base idiom the contribution grid uses, and it is the whole reason this is safe to ship:
    GitHub's own image cache never runs the animation."""
    _WIPE[0] += 1
    i = _WIPE[0]
    return (f'<defs><mask id="w{i}"><rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#fff">'
            f'<set attributeName="width" to="0" begin="0s"/>'
            f'<animate attributeName="width" from="0" to="{w}" begin="{t0:.2f}s" dur="{dur}s" '
            f'fill="freeze" calcMode="spline" keyTimes="0;1" keySplines="0.35 0 0.45 1"/>'
            f'</rect></mask></defs><g mask="url(#w{i})">{el}</g>')


# --------------------------------------------------------------------------- morphing
# The morphs are morphicons' spring physics, sampled by design/morph.mjs into
# design/morphs.json (GitHub strips JS, so SMIL replays the baked keyframes).
# Each morph gets its own <path>, because SMIL can only interpolate between `d`
# values with the same structure, and every icon pair has its own plan.

MORPHS = json.loads((ROOT / "morphs.json").read_text())
SPRING = "0.2 0.9 0.3 1"  # rail easing, close to morphicons' "snappy" spring


def morph(name, scale, ox, oy, stroke, width):
    """Loop through the baked morphs of `name`, each played at the end of its slot."""
    ms = MORPHS[name]
    k = len(ms)
    starts = [(i + HOLD) / k for i in range(k)]
    b = []
    for i, m in enumerate(ms):
        f = m["frames"]
        a = starts[i]
        times = [0, a - 0.0005] + [a + m["dur"] / DUR * j / (len(f) - 1) for j in range(len(f))] + [1]
        values = [f[-1], f[-1]] + f + [f[-1]]
        if times[-2] >= 1:  # last morph ends the cycle
            times, values = times[:-1], values[:-1]
            times[-1] = 1
        # visible from its own start until the next morph takes over
        nxt = starts[(i + 1) % k]
        if nxt > a:
            vis = f'values="hidden;visible;hidden" keyTimes="0;{a:.4f};{nxt:.4f}"'
            base = "hidden"
        else:
            vis = f'values="visible;hidden;visible" keyTimes="0;{nxt:.4f};{a:.4f}"'
            base = "visible"
        b.append(f'<path d="{f[-1]}" visibility="{base}">'
                 f'<animate attributeName="d" dur="{DUR}s" repeatCount="indefinite" '
                 f'values="{";".join(values)}" keyTimes="{";".join(f"{t:.4f}" for t in times)}"/>'
                 f'<animate attributeName="visibility" dur="{DUR}s" repeatCount="indefinite" '
                 f'calcMode="discrete" {vis}/></path>')
    return (f'<g transform="translate({ox} {oy}) scale({scale})" fill="none" stroke="{stroke}" '
            f'stroke-width="{width / scale:.2f}" stroke-linejoin="round" stroke-linecap="round">'
            + "".join(b) + "</g>")


def active(i, k, hold, on, off, attr="fill"):
    """Discrete switch keeping step i `on` from mid-morph into it until mid-morph out of it."""
    half = (1 - hold) / 2 / k
    start, end = i / k - half, (i + 1) / k - half
    if start < 0:
        return (f'<animate attributeName="{attr}" dur="{DUR}s" repeatCount="indefinite" calcMode="discrete" '
                f'values="{on};{off};{on}" keyTimes="0;{end:.4f};{1 + start:.4f}"/>')
    return (f'<animate attributeName="{attr}" dur="{DUR}s" repeatCount="indefinite" calcMode="discrete" '
            f'values="{off};{on};{off}" keyTimes="0;{start:.4f};{end:.4f}"/>')


DUR = 13  # was 8: the spring is unchanged, the rests between morphs are longer. Melancholy is slow.
HOLD = 1 - MORPHS["hero"][0]["dur"] * 4 / DUR  # rest, then the spring fills the slot

# --------------------------------------------------------------------------- hero


def hero(c):
    """The opening entry. Nothing is laid out as a card: the leaf is ruled, the text hangs off the
    red margin like handwriting does, and each line is written in rather than faded in."""
    w, h = 880, 300
    x = GUTTER + 44  # text starts a nib's width right of the red rule
    steps = ["measure", "validate", "build", "ship"]
    slot, ry = 104, 280
    b = []
    # the dateline a diary opens with, and the place, on the same line at opposite ends
    b.append(written(text(x, 60, "20th September", 16, c["faint"], "GM")
                     + text(w - 40, 60, "A Coruña", 16, c["faint"], "GM", "end"),
                     x, 40, w - x - 30, 28, 0.2, 1.1))
    b.append(f'<line x1="{x}" y1="76" x2="{w - 40}" y2="76" stroke="{c["line"]}">'
             f'<set attributeName="x2" to="{x}" begin="0s"/>'
             f'<animate attributeName="x2" from="{x}" to="{w - 40}" begin="0.5s" dur="0.8s" '
             f'fill="freeze" calcMode="spline" keyTimes="0;1" keySplines="0.35 0 0.45 1"/></line>')
    lines = [(124, "Javier Rodeiro", 44, c["text"], "GS", -0.015),
             (157, "AI & Analytics Developer at cinfo", 21, c["muted"], "GM", 0.0),
             (208, "Clean data, rigorous validation,", 22, c["text"], "G", 0.0),
             (239, "and when the tool doesn’t exist, I build it.", 22, c["text"], "G", 0.0)]
    for i, (y, s, size, fill, face, tr) in enumerate(lines):
        el = text(x, y, s, size, fill, face, track=tr, extra=' filter="url(#bloom)"')
        b.append(written(el, x, y - size, width(s, size, face) + 14, size * 1.45,
                         1.0 + i * 0.62, 0.55 + size * 0.016))
    # the four steps, underlined one at a time by a nib that slides along under them
    for i, s in enumerate(steps):
        b.append(f'<text x="{x + i * slot}" y="{ry}" class="GM" font-size="15" fill="{c["faint"]}">{s}'
                 f'{active(i, 4, HOLD, c["text"], c["faint"])}</text>')
    bar_vals = ";".join(f"{x + i * slot};{x + i * slot}" for i in range(4)) + f";{x}"
    k_times = ";".join(f"{i / 4:.4f};{(i + HOLD) / 4:.4f}" for i in range(4)) + ";1"
    b.append(f'<rect x="{x}" y="{ry + 7}" width="58" height="1.6" fill="{c["accent"]}" '
             f'filter="url(#bloom)" opacity=".8">'
             f'<animate attributeName="x" dur="{DUR}s" repeatCount="indefinite" calcMode="spline" '
             f'values="{bar_vals}" keyTimes="{k_times}" keySplines="{";".join([SPRING] * 8)}"/></rect>')
    # the marginal sketch: the same morph, but drawn in ink on the leaf instead of sitting in a tile
    b.append(f'<g opacity=".72" transform="rotate(-5 745 180)">'
             f'{morph("hero", 4.4, 690, 132, c["text"], 4)}</g>')
    return svg(w, h, "Javier Rodeiro — AI & Analytics Developer at cinfo. Clean data, rigorous "
                     "validation, and when the tool doesn't exist, I build it.", "".join(b), c,
               rules=None, stains=((0.88, 0.18, 0.15), (0.12, 0.86, 0.09)))


# --------------------------------------------------------------------------- project cards


ARROW = "M0 10 L10 0 M2.5 0 H10 V7.5"

PROJECTS = [
    ("addocu", "Addocu",
     "Documents your whole Google marketing stack in seconds.",
     "Founder · open-source Google Sheets add-on · GA4 · GTM"),
    ("solodshouse", "SoloDShouse",
     "MSc thesis · AI inference energy and cost analytics.",
     "Python · Iceberg · MLflow · LangGraph · local-first"),
    ("findingexcellence", "FindingExcellence PRO",
     "File search with local AI. Nothing leaves your machine.",
     "Python · FastAPI · Ollama · zero external APIs"),
    ("ajazz-deck", "ajazz-deck",
     "Linux daemon + CLI for the AJAZZ AKP153 macro pad.",
     "Python · Linux · one YAML file maps every key"),
]


def card(c, name, title, desc, meta):
    """A dated entry, not a tile: title in print, the description written in as the pen goes."""
    w, h, x = 880, 128, GUTTER + 46
    has = (LOGOS / f"{name}.svg").exists()
    b = [*([place(name, x, 28, 34, c["text"])[0]] if has else []),
         text(x + (44 if has else 0), 56, title, 32, c["text"], "GS", track=-0.025),
         written(text(x, 88, desc, 21, c["muted"]), x, 70, width(desc, 21) + 14, 30, 0.4),
         written(text(x, 112, meta, 16, c["faint"], "GM"), x, 98, width(meta, 16, "GM") + 14, 22, 1.3),
         f'<path d="{ARROW}" transform="translate(836 32)" fill="none" stroke="{c["faint"]}" '
         f'stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/>']
    return svg(w, h, f"{title} — {desc}", "".join(b), c)


# --------------------------------------------------------------------------- logos
# Simple Icons (CC0) plus official marks pulled from each vendor's site. Every logo is
# flattened to one colour so the wall reads as a single system, not a sticker sheet.

CROP = {"amplitude": "0 0 32 32", "addocu": "26 22 72 72"}
DB = ('<g><ellipse cx="12" cy="5" rx="8" ry="3"/>'
      '<path d="M4 8v4c0 1.7 3.6 3 8 3s8-1.3 8-3V8c0 1.7-3.6 3-8 3S4 9.7 4 8z"/>'
      '<path d="M4 14v4c0 1.7 3.6 3 8 3s8-1.3 8-3v-4c0 1.7-3.6 3-8 3s-8-1.3-8-3z"/></g>')


def logo(slug):
    """(viewBox, inner markup) with every fill stripped, so the caller's fill wins."""
    if slug == "sql":
        return "0 0 24 24", DB
    raw = (LOGOS / f"{slug}.svg").read_text()
    head = re.search(r"<svg\b[^>]*>", raw).group(0)
    vb = CROP.get(slug) or (re.search(r'viewBox="([^"]+)"', head) or
                            re.search(r'width="([\d.]+)', head)).group(1)
    if " " not in vb:  # width/height only
        vb = f"0 0 {vb} {re.search(r'height=.([\d.]+)', head).group(1)}"
    body = raw[raw.index(head) + len(head):raw.rindex("</svg>")]
    body = re.sub(r"<(metadata|title|defs|sodipodi:namedview)\b[^>]*/>", "", body)
    body = re.sub(r"<(metadata|title|defs|sodipodi:namedview)\b.*?</\1>", "", body, flags=re.S)
    body = re.sub(r'\s(inkscape|sodipodi):[\w-]+="[^"]*"', "", body)
    body = re.sub(r"<!--.*?-->", "", body, flags=re.S)
    body = re.sub(r'\s(fill|style|class|id|opacity|fill-opacity)="(?!none)[^"]*"', "", body)
    return vb, body


def place(slug, x, y, size, fill):
    vb = logo(slug)[0].split()
    vw, vh = float(vb[2]), float(vb[3])
    w = size * vw / vh
    return (f'<svg x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{size}" viewBox="{" ".join(vb)}" fill="{fill}">'
            f"{logo(slug)[1]}</svg>"), w


# --------------------------------------------------------------------------- toolkit ticker

TOOLKIT = [
    ("analytics", [("googleanalytics", "GA4"), ("googletagmanager", "GTM"), ("googlebigquery", "BigQuery"),
                   ("piwikpro", None), ("adobe", "Adobe Analytics"), ("amplitude", "Amplitude"),
                   ("posthog", "PostHog"), (None, "Clarity")]),
    ("code", [("python", "Python"), ("typescript", "TypeScript"), ("sql", "SQL"), ("go", "Go"),
              ("fastapi", "FastAPI"), ("nextdotjs", "Next.js"), ("nodedotjs", "Node.js"),
              ("googleappsscript", "Apps Script")]),
    ("ai", [("modelcontextprotocol", "MCP servers"), ("langgraph", "LangGraph"), ("ollama", "Ollama"),
            ("claude", "Claude"), ("googlecloud", "Vertex AI"), (None, "LiteLLM")]),
    ("data", [("duckdb", "DuckDB"), (None, "Iceberg"), ("mlflow", "MLflow"), (None, "Dagster"),
              ("postgresql", "PostgreSQL"), ("supabase", "Supabase"), ("lookerstudio", "Looker Studio"),
              ("powerbi", "Power BI"), ("tableau", "Tableau"), (None, "marimo")]),
]


def ticker(c):
    w, row_h, pad = 880, 68, 8
    h = pad * 2 + row_h * len(TOOLKIT)
    vx, vw = 168, 880 - 168 - 24
    b = [f'<defs><clipPath id="vp"><rect x="{vx}" y="0" width="{vw}" height="{h}"/></clipPath>'
         f'<linearGradient id="fl"><stop offset="0" stop-color="{c["bg"]}"/>'
         f'<stop offset="1" stop-color="{c["bg"]}" stop-opacity="0"/></linearGradient>'
         f'<linearGradient id="fr"><stop offset="0" stop-color="{c["bg"]}" stop-opacity="0"/>'
         f'<stop offset="1" stop-color="{c["bg"]}"/></linearGradient></defs>']
    for r, (label, items) in enumerate(TOOLKIT):
        top = pad + r * row_h
        mid = top + row_h / 2
        b.append(text(GUTTER + 46, mid + 5, label, 17, c["faint"], "GM"))
        # one period of the band
        x, band = 0.0, []
        for slug, name in items:
            if slug:
                g, lw = place(slug, x, mid - 11 if name else mid - 9, 22 if name else 18, c["text"])
                band.append(g)
                x += lw + (10 if name else 0)
            if name:
                band.append(text(round(x, 1), mid + 6, name, 17, c["muted"]))
                x += width(name, 17)
            x += 44
        period = round(x)
        reps = math.ceil(vw / period) + 1
        tiles = f'<g id="band{r}">{"".join(band)}</g>' + "".join(
            f'<use href="#band{r}" x="{k * period}"/>' for k in range(1, reps))
        a, z = (0, -period) if r % 2 == 0 else (-period, 0)
        b.append(f'<g clip-path="url(#vp)"><g transform="translate({vx + 16} 0)"><g>{tiles}'
                 f'<animateTransform attributeName="transform" type="translate" from="{a} 0" to="{z} 0" '
                 f'dur="{period / 12:.1f}s" repeatCount="indefinite"/></g></g></g>')
    b.append(f'<rect x="{vx}" y="1" width="56" height="{h - 2}" fill="url(#fl)"/>')
    b.append(f'<rect x="{vx + vw - 72}" y="1" width="72" height="{h - 2}" fill="url(#fr)"/>')
    b += [f'<line x1="{GUTTER + 22}" y1="{pad + r * row_h}" x2="{w - 24}" y2="{pad + r * row_h}" stroke="{c["line"]}"/>'
          for r in range(1, len(TOOLKIT))]
    flat = ", ".join(f"{lab}: " + ", ".join(n or "Piwik PRO" for _, n in items) for lab, items in TOOLKIT)
    return svg(w, h, f"Toolkit — {flat}.", "".join(b), c)


# --------------------------------------------------------------------------- credentials

CREDENTIALS = [
    ("Google Analytics Individual Qualification", "Google", "google-wordmark"),
    ("Piwik PRO Analytics Suite · Tag Manager · Consent Manager", "Piwik PRO", "piwikpro"),
    ("Adobe Analytics Foundations", "Adobe", "adobe"),
    ("Cambridge C2 Proficiency", "Cambridge English", "cambridgeenglish"),
    ("EF SET C2 Proficient", "EF", "efset"),
]
PRACTICE = "Scrum Master · Product Owner · Kanban · Lean"


def credentials(c):
    w, row_h, top = 880, 54, 20
    n = len(CREDENTIALS)
    h = top + row_h * (n + 1) + 16
    dur = 9
    b = []
    for i, (name, issuer, slug) in enumerate(CREDENTIALS + [(PRACTICE, "practice", None)]):
        y = top + i * row_h
        mid = y + row_h / 2
        if i:
            b.append(f'<line x1="{GUTTER + 22}" y1="{y}" x2="{w - 24}" y2="{y}" stroke="{c["line"]}"/>')
        last = i == n
        if not last:
            # checks draw once, in reading order, then hold (base offset 0 keeps them visible if SMIL never runs)
            t0 = (0.4 + i * 0.25) / dur
            b.append(f'<path d="M{66} {mid} l6 6 l12 -12" fill="none" stroke="{c["accent"]}" stroke-width="2.5" '
                     f'stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="26" stroke-dashoffset="0">'
                     f'<animate attributeName="stroke-dashoffset" dur="{dur}s" fill="freeze" '
                     f'values="26;26;0;0" keyTimes="0;{t0:.3f};{t0 + 0.4 / dur:.3f};1"/></path>')
        else:
            b.append(f'<path d="M66 {mid} h18 M66 {mid - 6} h18 M66 {mid + 6} h12" stroke="{c["faint"]}" '
                     f'stroke-width="2" stroke-linecap="round"/>')
        b.append(text(108, mid + 7, name, 20, c["muted"] if last else c["text"]))
        if slug:  # issuer mark, right-aligned
            lw = place(slug, 0, 0, 20, "")[1]
            b.append(place(slug, w - 32 - lw, mid - 10, 20, c["muted"])[0])
        else:
            b.append(text(w - 32, mid + 5, issuer, 14, c["faint"], "GM", "end"))
    flat = "; ".join(f"{a} ({b_})" for a, b_, _ in CREDENTIALS)
    return svg(w, h, f"Certifications: {flat}. Practice: {PRACTICE}.", "".join(b), c)


# --------------------------------------------------------------------------- focus areas
# Themes across public and private repos; described, never named.

DOT = "m-2 0a2 2 0 1 0 4 0a2 2 0 1 0-4 0"
AGENT = f"M12 6v4M12 10l-6 8M12 10l6 8M12 4{DOT}M6 20{DOT}M18 20{DOT}"
VAULT = "M4 5c3-1 6-1 8 1c2-2 5-2 8-1v14c-3-1-6-1-8 1c-2-2-5-2-8-1zM12 6v14"
CHIP = "M7 7h10v10H7zM10 3v4M14 3v4M10 17v4M14 17v4M3 10h4M3 14h4M17 10h4M17 14h4"
PIPE = "M12 3L3 8l9 5 9-5zM3 12l9 5 9-5M3 16l9 5 9-5"

FOCUS = [
    (AGENT, "Agents & MCP", ("MCP servers that give models", "real tools: GTM, docs, media.")),
    (VAULT, "Knowledge systems", ("Agent memory, RAG and search", "over everything I save and read.")),
    (CHIP, "Local-first AI", ("Models, speech and file search", "running on my own machine.")),
    (PIPE, "Data platforms", ("Lakehouses and pipelines with", "DuckDB, Dagster and MLflow.")),
]


def focus(c):
    w, h = 880, 328
    b = []
    for i, (shape, title, desc) in enumerate(FOCUS):
        col, row = i % 2, i // 2
        x, y = GUTTER + 46 + col * 400, 24 + row * 144
        b.append(f'<path d="{shape}" transform="translate({x} {y + 28}) scale(2)" fill="none" '
                 f'stroke="{c["muted"]}" stroke-width="1.25" stroke-linejoin="round" stroke-linecap="round"/>')
        b.append(text(x + 68, y + 48, title, 22, c["text"], "GS", track=-0.02))
        for k, line in enumerate(desc):
            b.append(text(x + 68, y + 80 + k * 24, line, 17, c["muted"]))
    flat = "; ".join(f"{t}: {' '.join(d)}" for _, t, d in FOCUS)
    return svg(w, h, f"Now building — {flat}", "".join(b), c)


# --------------------------------------------------------------------------- activity (live)

# contributionCalendar.totalContributions is deliberately not read: on this account it reports 2,613
# against 2,507 summed across the 365 day cells the same response returns. The counter below walks
# the grid week by week, so it has to agree with the grid, not with a figure no cell accounts for.
Q = """query($u:String!){user(login:$u){contributionsCollection{
totalCommitContributions totalPullRequestContributions totalPullRequestReviewContributions
totalRepositoriesWithContributedCommits
contributionCalendar{weeks{contributionDays{contributionCount date}}}}}}"""


def fetch_calendar():
    out = subprocess.run(["gh", "api", "graphql", "-f", f"query={Q}", "-F", f"u={USER}"],
                         check=True, capture_output=True, text=True).stdout
    cc = json.loads(out)["data"]["user"]["contributionsCollection"]
    cal = cc["contributionCalendar"]
    return {"weeks": [[(d["date"], d["contributionCount"]) for d in wk["contributionDays"]]
                      for wk in cal["weeks"]],
            "commits": cc["totalCommitContributions"],
            "prs": cc["totalPullRequestContributions"],
            "reviews": cc["totalPullRequestReviewContributions"],
            "repos": cc["totalRepositoriesWithContributedCommits"]}


def streaks(days):
    counts = [n for _, n in days]
    longest = run = 0
    for n in counts:
        run = run + 1 if n else 0
        longest = max(longest, run)
    cur = 0
    for n in reversed(counts[:-1] if counts and counts[-1] == 0 else counts):  # today may still be empty
        if not n:
            break
        cur += 1
    return cur, longest, sum(1 for n in counts if n)


def odometer(x, y, steps, size, c):
    """Count-up built from the real prefix values: one <text> per distinct number, shown on its
    step and hidden by the next. The final value carries opacity="1" in the attribute, so a
    renderer that ignores SMIL draws the finished figure and nothing else."""
    out, prev = [], object()
    for j, (t, v) in enumerate(steps):
        if v == prev:
            continue
        prev = v
        nxt = next((s for s, nv in steps[j + 1:] if nv != v), None)
        if nxt is None:  # the run that reaches the end is the static base, emitted below
            break
        out.append(f'<text x="{x}" y="{y}" opacity="0">{v:,}'
                   f'<set attributeName="opacity" to="1" begin="{t:.2f}s"/>'
                   f'<set attributeName="opacity" to="0" begin="{nxt:.2f}s"/></text>')
    final = steps[-1][1]
    t_final = next(t for i, (t, v) in enumerate(steps)  # start of the final run, not an earlier tie
                   if v == final and all(nv == final for _, nv in steps[i:]))
    out.append(f'<text x="{x}" y="{y}" opacity="1">{final:,}'
               f'<set attributeName="opacity" to="0" begin="0s"/>'
               f'<set attributeName="opacity" to="1" begin="{t_final:.2f}s"/></text>')
    return (f'<g class="GS" font-size="{size}" fill="{c["text"]}" letter-spacing="{-0.03 * size:.2f}">'
            + "".join(out) + "</g>")


def activity(c, cal):
    w, h, weeks = 880, 344, cal["weeks"]
    days = [d for wk in weeks for d in wk]
    cur, longest, active_days = streaks(days)
    total = sum(n for _, n in days)
    peak = max(n for _, n in days) or 1
    # one column per week, left to right; every other animation hangs off these times
    t0, span, fade = 0.3, 3.2, 0.5
    starts = [t0 + span * i / max(1, len(weeks) - 1) for i in range(len(weeks))]
    b = []

    # headline stats, stepped by the column that is filling: the counters follow the real
    # cumulative curve of the year, so they speed up and stall exactly where the work did.
    end, frames = 0, []
    for i, wk in enumerate(weeks):
        end += len(wk)
        pre = days[:end]
        pc, pl, pa = streaks(pre)
        frames.append((starts[i], (sum(n for _, n in pre), pa, pl, pc)))
    for k, lab in enumerate(["contributions", "active days", "longest streak", "current streak"]):
        x = 72 + k * 190
        b.append(odometer(x, 76, [(0.0, 0)] + [(t, f[k]) for t, f in frames], 36, c))
        b.append(text(x, 102, lab, 14, c["faint"], "GM"))
    # year totals with no per-week breakdown, so they hold until the playback has walked the year —
    # showing them from the start reads as if they were accumulating too
    row2 = []
    for k, (v, lab) in enumerate([(cal["commits"], "commits"), (cal["prs"], "pull requests"),
                                  (cal["reviews"], "reviews"), (cal["repos"], "repositories")]):
        x = 72 + k * 190
        row2.append(text(x, 140, f"{v:,}", 18, c["muted"], "GS", track=-0.02))
        row2.append(text(x + width(f"{v:,}", 18, "GS") + 8, 140, lab, 13, c["faint"], "GM"))
    b.append(f'<g opacity="1">{"".join(row2)}'
             f'<set attributeName="opacity" to="0" begin="0s"/>'
             f'<animate attributeName="opacity" values="0;1" begin="{t0 + span:.2f}s" dur="0.45s" '
             f'fill="freeze" calcMode="spline" keyTimes="0;1" keySplines="0.3 0 0.2 1"/></g>')

    cell, gap = 12, 3
    x0, y0 = 72 + (776 - len(weeks) * (cell + gap) + gap) / 2, 196
    b.append(f'<defs><path id="c" d="M3 1 L{cell - 3} {cell - 1}" fill="none" stroke-width="1.7" stroke-linecap="round"/></defs>')
    last_month = None
    for i, wk in enumerate(weeks):
        cx = x0 + i * (cell + gap)
        month = wk[0][0][:7]
        if month != last_month and (i or wk[0][0][8:] < "20"):  # skip a sliver of month at the left edge
            b.append(text(cx, y0 - 14, date.fromisoformat(wk[0][0]).strftime("%b"), 12, c["faint"], "GM"))
        last_month = month
        col = []
        for d, n in wk:
            j = date.fromisoformat(d).isoweekday() % 7
            if n:
                lvl = 0.25 + 0.75 * min(1, math.sqrt(n / peak) * 1.3)
                col.append(f'<use href="#c" x="{cx:.1f}" y="{y0 + j * (cell + gap)}" '
                           f'stroke="{c["accent"]}" stroke-opacity="{lvl:.2f}"/>')
            else:
                col.append(f'<use href="#c" x="{cx:.1f}" y="{y0 + j * (cell + gap)}" stroke="{c["line"]}" stroke-opacity=".55"/>')
        # the column is drawn whole and opaque; the <set> zeroes it only where SMIL runs, so the
        # year plays back once and any renderer without SMIL still gets the finished grid
        b.append(f'<g opacity="1">{"".join(col)}'
                 f'<set attributeName="opacity" to="0" begin="0s"/>'
                 f'<animate attributeName="opacity" values="0;1" begin="{starts[i]:.2f}s" dur="{fade}s" '
                 f'fill="freeze" calcMode="spline" keyTimes="0;1" keySplines="0.3 0 0.2 1"/>'
                 f'<animateTransform attributeName="transform" type="translate" values="0 7;0 0" '
                 f'begin="{starts[i]:.2f}s" dur="{fade}s" fill="freeze" calcMode="spline" keyTimes="0;1" '
                 f'keySplines="{SPRING}"/></g>')
    today = days[-1][0]
    b.append(text(w - 40, 322, f"last 12 months · updated {today}", 12, c["faint"], "GM", "end"))
    return svg(w, h, f"GitHub activity, last 12 months: {total:,} contributions, {active_days} active "
                     f"days, longest streak {longest} days, current streak {cur} days. "
                     f"{cal['commits']:,} commits, {cal['prs']:,} pull requests, {cal['reviews']:,} reviews "
                     f"across {cal['repos']} repositories.", "".join(b), c)


# --------------------------------------------------------------------------- signature
# Skeleton: EMS Allure (OFL, single-stroke script from the Hershey/EggBot family), smoothed with
# Catmull-Rom. The broad nib is faked by stacking the stroke along a 45° vector: thick on strokes
# that cross the nib, hairline on strokes that run along it.

def allure():
    src = (FONTS / "EMSAllure.svg").read_text()
    return {m[1]: (float(m[2]), m[3] or "") for m in
            re.finditer(r'<glyph unicode="(.)"[^>]*?horiz-adv-x="([\d.]+)"(?:[^>]*?d="([^"]*)")?', src)}


def glyph_strokes(d):
    out, toks, i = [], re.findall(r"[MLC]|-?[\d.]+", d), 0
    while i < len(toks):
        t = toks[i]
        if t == "M":
            out.append([(float(toks[i + 1]), float(toks[i + 2]))]); i += 3
        elif t == "L":
            out[-1].append((float(toks[i + 1]), float(toks[i + 2]))); i += 3
        elif t == "C":  # endpoint only; the spline below re-smooths it
            out[-1].append((float(toks[i + 5]), float(toks[i + 6]))); i += 7
        else:
            out[-1].append((float(toks[i]), float(toks[i + 1]))); i += 2
    return out


def spline(pts):
    d = f"M{pts[0][0]:.1f} {pts[0][1]:.1f}"
    if len(pts) < 3:
        return d + "".join(f" L{x:.1f} {y:.1f}" for x, y in pts[1:])
    p = [pts[0]] + pts + [pts[-1]]
    for i in range(1, len(p) - 2):
        p0, p1, p2, p3 = p[i - 1], p[i], p[i + 1], p[i + 2]
        d += (f" C{p1[0] + (p2[0] - p0[0]) / 6:.1f} {p1[1] + (p2[1] - p0[1]) / 6:.1f} "
              f"{p2[0] - (p3[0] - p1[0]) / 6:.1f} {p2[1] - (p3[1] - p1[1]) / 6:.1f} {p2[0]:.1f} {p2[1]:.1f}")
    return d


def signature(c, name="Javier Rodeiro"):
    h, size, x0, base, slant = 150, 72, 20, 88, 0.18
    font, k, x, strokes = allure(), size / 1000, 0.0, []
    for ch in name:
        adv, d = font[ch]
        strokes += [[(x0 + (x + px + py * slant) * k, base - py * k) for px, py in st] for st in glyph_strokes(d)]
        x += adv + 30
    xe = x0 + x * k
    w = round(xe + 40)
    swash = [(xe - 24, base - 4), (xe + 8, base - 10), (xe - 30, base + 26), (xe * 0.55, base + 20),
             (x0 + 40, base + 18), (x0 + 14, base + 27)]
    ds = [spline(st) for st in strokes] + [
        f"M{swash[0][0]:.1f} {swash[0][1]} C{swash[1][0]:.1f} {swash[1][1]} {swash[2][0]:.1f} {swash[2][1]} "
        f"{swash[3][0]:.1f} {swash[3][1]} S{swash[4][0]} {swash[4][1]} {swash[5][0]} {swash[5][1]}"]  # closing swash
    # SVG restarts the dash pattern on every subpath, so each stroke gets its own path, timed
    # by its length: the pen moves at one speed and lifts briefly between strokes.
    lens = [sum(math.dist(a, b) for a, b in zip(st, st[1:])) for st in strokes + [swash]]
    lens[-1] *= 0.75  # control polygon overestimates the curve
    dur, lift = 4.5, 0.06
    speed = (dur - 0.4 - lift * (len(lens) - 1)) / sum(lens)
    t, paths = 0.4, []
    for d, ln in zip(ds, lens):
        a, z = t / dur, (t + ln * speed) / dur
        # dasharray "1 2" keeps the undrawn stroke fully in the gap, so no round-cap dots before it starts
        paths.append(f'<path d="{d}" pathLength="1" stroke-dasharray="1 2" stroke-dashoffset="0">'
                     f'<animate attributeName="stroke-dashoffset" values="1;1;0;0" keyTimes="0;{a:.4f};{z:.4f};1" '
                     f'dur="{dur}s" fill="freeze"/></path>')
        t += ln * speed + lift
    # base offset 0 shows the ink whole if SMIL never runs
    nib = (f'<g id="ink">{"".join(paths)}</g>' +
           "".join(f'<use href="#ink" x="{i * 0.45:.2f}" y="{-i * 0.45:.2f}"/>' for i in range(1, 7)))
    font, k, x, ds = allure(), size / 1000, 0.0, []
    for ch in name:
        adv, d = font[ch]
        ds += [spline([(x0 + (x + px + py * slant) * k, base - py * k) for px, py in st]) for st in glyph_strokes(d)]
        x += adv + 30
    xe = x0 + x * k
    w = round(xe + 40)
    ds.append(f"M{xe - 24:.1f} {base - 4} C{xe + 8:.1f} {base - 10} {xe - 30:.1f} {base + 26} "
              f"{xe * 0.55:.1f} {base + 20} S{x0 + 40} {base + 18} {x0 + 14} {base + 27}")  # closing swash
    d = " ".join(ds)
    # one pass, eased like a hand, then the ink stays; base offset 0 shows it whole if SMIL never runs
    nib = (f'<path id="ink" d="{d}" pathLength="1000" stroke-dasharray="1000" stroke-dashoffset="0">'
           f'<animate attributeName="stroke-dashoffset" values="1000;1000;0" keyTimes="0;.1;1" dur="4.5s" '
           f'calcMode="spline" keySplines="0 0 1 1;0.45 0 0.3 1" fill="freeze"/></path>' +
           "".join(f'<use href="#ink" x="{i * 0.45:.2f}" y="{-i * 0.45:.2f}"/>' for i in range(1, 7)))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" '
            f'aria-label="Signature: {name}"><title>Signature: {name}</title>'
            f'<g fill="none" stroke="{c["text"]}" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round">'
            f'{nib}</g></svg>')


# --------------------------------------------------------------------------- write

if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    cal = fetch_calendar()
    for theme, c in THEMES.items():
        files = {"hero": hero(c), "toolkit": ticker(c),
                 "credentials": credentials(c), "focus": focus(c), "activity": activity(c, cal),
                 "signature": signature(c)}
        for p in PROJECTS:
            files[f"card-{p[0]}"] = card(c, *p)
        for name, content in files.items():
            (OUT / f"{name}-{theme}.svg").write_text(content)
    print("\n".join(sorted(f"{p.name}  {p.stat().st_size // 1024}KB" for p in OUT.glob("*.svg"))))
