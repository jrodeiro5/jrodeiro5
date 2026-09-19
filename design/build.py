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

THEMES = {
    "dark": dict(bg="#0B0B0C", tile="#141416", line="#232326", cell="#1C1C1F",
                 text="#EDEDEF", muted="#A0A0A8", faint="#7E7E86", accent="#8E97FF"),
    "light": dict(bg="#FFFFFF", tile="#FAFAFA", line="#E6E6E8", cell="#EFEFF1",
                  text="#0A0A0B", muted="#5F5F66", faint="#707078", accent="#4F5BD5"),
}

EASE = "0.65 0 0.35 1"  # in-out, used for every morph segment

# --------------------------------------------------------------------------- fonts

CHARS = "".join(chr(c) for c in range(0x20, 0x7F)) + "ñ·—’é"


def woff2(name: str) -> str:
    font = TTFont(FONTS / name)
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


FACES = {
    "G": ("Geist-Regular.ttf", 400),
    "GS": ("Geist-SemiBold.ttf", 600),
    "GM": ("GeistMono-Regular.ttf", 400),
}
FONT_CSS = {k: f"@font-face{{font-family:{k};src:url(data:font/woff2;base64,{woff2(f)}) format('woff2');font-weight:{w}}}"
            for k, (f, w) in FACES.items()}
STACK = {"G": "G,-apple-system,'Segoe UI',Helvetica,Arial,sans-serif",
         "GS": "GS,-apple-system,'Segoe UI',Helvetica,Arial,sans-serif",
         "GM": "GM,ui-monospace,'SF Mono',Menlo,Consolas,monospace"}


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


def svg(w, h, title, body, c, faces=("G", "GS", "GM")):
    css = "".join(FONT_CSS[f] for f in faces)
    css += "".join(f".{f}{{font-family:{STACK[f]}}}" for f in faces)
    css += "text{font-kerning:normal}"
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'role="img" aria-label="{esc(title)}"><title>{esc(title)}</title><style>{css}</style>'
            f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="16" fill="{c["bg"]}" stroke="{c["line"]}"/>'
            f"{body}</svg>")


def text(x, y, s, size, fill, face="G", anchor="start", track=0.0, extra=""):
    ls = f' letter-spacing="{track * size:.2f}"' if track else ""
    return (f'<text x="{x}" y="{y}" class="{face}" font-size="{size}" fill="{fill}" '
            f'text-anchor="{anchor}"{ls}{extra}>{esc(s)}</text>')


# --------------------------------------------------------------------------- morphing geometry
# Every icon is one closed polyline on a 24-unit grid. Resampling them all to the
# same point count (vertices kept exactly) lets SMIL interpolate `d` between them.

N = 120


def resample(pts, n=N):
    pts = list(pts) + [pts[0]]
    segs = [(a, b, math.dist(a, b)) for a, b in zip(pts, pts[1:])]
    total = sum(s[2] for s in segs)
    raw = [n * s[2] / total for s in segs]
    counts = [max(1, math.floor(r)) for r in raw]
    for i in sorted(range(len(segs)), key=lambda i: raw[i] - counts[i], reverse=True):
        if sum(counts) >= n:
            break
        counts[i] += 1
    while sum(counts) > n:
        counts[counts.index(max(counts))] -= 1
    out = []
    for (a, b, _), k in zip(segs, counts):
        out += [(a[0] + (b[0] - a[0]) * j / k, a[1] + (b[1] - a[1]) * j / k) for j in range(k)]
    return out


def normalise(pts):
    """Clockwise, starting at the vertex nearest the top-left, so morphs don't twist."""
    area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(pts, pts[1:] + pts[:1]))
    if area < 0:
        pts = pts[::-1]
    i = min(range(len(pts)), key=lambda i: pts[i][0] + pts[i][1])
    return pts[i:] + pts[:i]


def path_d(pts, scale, ox, oy):
    p = [f"{ox + x * scale:.1f} {oy + y * scale:.1f}" for x, y in pts]
    return "M" + " L".join(p) + " Z"


BARS = [(3, 21), (3, 14), (7.5, 14), (7.5, 21), (9.75, 21), (9.75, 8), (14.25, 8), (14.25, 21),
        (16.5, 21), (16.5, 3.5), (21, 3.5), (21, 21)]
CHECK = [(3.5, 12.5), (9, 18), (20.5, 6.5), (9, 18)]
BOX = [(3, 7), (12, 2), (21, 7), (21, 17), (12, 22), (3, 17), (3, 7), (12, 12), (21, 7), (12, 12),
       (12, 22), (12, 12)]
PLANE = [(2.5, 10.5), (21.5, 2.5), (13.5, 21.5), (10.5, 13.5), (21.5, 2.5), (10.5, 13.5)]


def morph(shapes, scale, ox, oy, dur, hold, stroke, width):
    """Path cycling through `shapes`; each holds `hold` of its slot, then eases to the next."""
    ds = [path_d(resample(normalise(s)), scale, ox, oy) for s in shapes]
    k = len(ds)
    values, times = [], []
    for i, d in enumerate(ds):
        values += [d, d]
        times += [i / k, (i + hold) / k]
    values.append(ds[0])
    times.append(1)
    splines = ";".join([EASE] * (len(values) - 1))
    return (f'<path d="{ds[0]}" fill="none" stroke="{stroke}" stroke-width="{width}" '
            f'stroke-linejoin="round" stroke-linecap="round">'
            f'<animate attributeName="d" dur="{dur}s" repeatCount="indefinite" calcMode="spline" '
            f'values="{";".join(values)}" keyTimes="{";".join(f"{t:.4f}" for t in times)}" '
            f'keySplines="{splines}"/></path>')


def active(i, k, hold, on, off, attr="fill"):
    """Discrete switch keeping step i `on` from mid-morph into it until mid-morph out of it."""
    half = (1 - hold) / 2 / k
    start, end = i / k - half, (i + 1) / k - half
    if start < 0:
        return (f'<animate attributeName="{attr}" dur="{DUR}s" repeatCount="indefinite" calcMode="discrete" '
                f'values="{on};{off};{on}" keyTimes="0;{end:.4f};{1 + start:.4f}"/>')
    return (f'<animate attributeName="{attr}" dur="{DUR}s" repeatCount="indefinite" calcMode="discrete" '
            f'values="{off};{on};{off}" keyTimes="0;{start:.4f};{end:.4f}"/>')


DUR, HOLD = 10, 0.72

# --------------------------------------------------------------------------- hero


def hero(c):
    w, h = 880, 300
    steps = ["measure", "validate", "build", "ship"]
    slot, x0, ry = 104, 48, 256
    b = []
    b.append(text(48, 100, "Javier Rodeiro", 46, c["text"], "GS", track=-0.03))
    b.append(text(48, 142, "AI & Analytics Developer at cinfo", 22, c["muted"]))
    b.append(text(48, 192, "Clean data, rigorous validation,", 22, c["text"]))
    b.append(text(48, 222, "and when the tool doesn’t exist, I build it.", 22, c["text"]))
    # step rail, synced with the morph
    b.append(f'<line x1="{x0}" y1="{ry + 14}" x2="{x0 + slot * 4 - 24}" y2="{ry + 14}" stroke="{c["line"]}"/>')
    for i, s in enumerate(steps):
        b.append(f'<text x="{x0 + i * slot}" y="{ry}" class="GM" font-size="13" fill="{c["faint"]}">{s}'
                 f'{active(i, 4, HOLD, c["text"], c["faint"])}</text>')
    bar_vals = ";".join(f"{x0 + i * slot};{x0 + i * slot}" for i in range(4)) + f";{x0}"
    k_times = ";".join(f"{i / 4:.4f};{(i + HOLD) / 4:.4f}" for i in range(4)) + ";1"
    b.append(f'<rect x="{x0}" y="{ry + 13}" width="56" height="2" rx="1" fill="{c["accent"]}">'
             f'<animate attributeName="x" dur="{DUR}s" repeatCount="indefinite" calcMode="spline" '
             f'values="{bar_vals}" keyTimes="{k_times}" keySplines="{";".join([EASE] * 8)}"/></rect>')
    # morph tile
    tx, ty, ts = 640, 48, 192
    b.append(f'<rect x="{tx}" y="{ty}" width="{ts}" height="{ts}" rx="14" fill="{c["tile"]}" stroke="{c["line"]}"/>')
    b.append(morph([BARS, CHECK, BOX, PLANE], 4.5, tx + 42, ty + 42, DUR, HOLD, c["accent"], 5))
    b.append(text(tx + ts, ry, "A Coruña, Spain", 13, c["faint"], "GM", "end"))
    return svg(w, h, "Javier Rodeiro — AI & Analytics Developer at cinfo. Clean data, rigorous "
                     "validation, and when the tool doesn't exist, I build it.", "".join(b), c)


# --------------------------------------------------------------------------- project cards


def anim(attr, values, times, dur):
    return (f'<animate attributeName="{attr}" dur="{dur}s" repeatCount="indefinite" calcMode="discrete" '
            f'values="{";".join(values)}" keyTimes="{";".join(f"{t:.4f}" for t in times)}"/>')


def pulse(on, off, t0, t1, dur, attr="fill"):
    return anim(attr, [off, on, off], [0, t0, t1], dur)


def sheet(c, x, y):
    """Addocu: an audit sheet documenting itself row by row."""
    b, dur = [], 9
    cols = [(0, 22), (28, 34), (68, 36)]
    for r in range(5):
        ry = y + 26 + r * 21
        t0 = 0.06 + r * 0.08
        for j, (cx, cw) in enumerate(cols):
            fill = c["accent"] if j == 0 else c["muted"]
            b.append(f'<rect x="{x + 24 + cx}" y="{ry}" width="{cw}" height="13" rx="3" fill="{c["cell"]}"/>')
            b.append(f'<rect x="{x + 24 + cx}" y="{ry}" width="{cw}" height="13" rx="3" fill="{fill}" opacity="0">'
                     f'<animate attributeName="opacity" dur="{dur}s" repeatCount="indefinite" '
                     f'values="0;0;{0.9 if j == 0 else 0.35};{0.9 if j == 0 else 0.35};0" '
                     f'keyTimes="0;{t0 + j * 0.02:.3f};{t0 + j * 0.02 + 0.05:.3f};0.85;0.95"/></rect>')
    return "".join(b)


def lakehouse(c, x, y):
    """SoloDShouse: one record falling through raw → clean → gold layers."""
    b, dur = [], 6
    b.append(f'<line x1="{x + 76}" y1="{y + 22}" x2="{x + 76}" y2="{y + 132}" stroke="{c["line"]}" stroke-width="2"/>')
    for i, ly in enumerate([42, 71, 100]):
        t = (ly + 9 - 22) / 110 * 0.7
        b.append(f'<rect x="{x + 24}" y="{y + ly}" width="104" height="18" rx="5" fill="{c["cell"]}" '
                 f'stroke="{c["line"]}"/>')
        b.append(f'<rect x="{x + 24}" y="{y + ly}" width="104" height="18" rx="5" fill="{c["accent"]}" opacity="0">'
                 f'<animate attributeName="opacity" dur="{dur}s" repeatCount="indefinite" '
                 f'values="0;0;{0.25 + i * 0.25:.2f};0" keyTimes="0;{t - 0.04:.3f};{t:.3f};{t + 0.18:.3f}"/></rect>')
    b.append(f'<circle cx="{x + 76}" cy="{y + 22}" r="5" fill="{c["accent"]}">'
             f'<animate attributeName="cy" dur="{dur}s" repeatCount="indefinite" calcMode="spline" '
             f'values="{y + 22};{y + 132};{y + 132}" keyTimes="0;0.7;1" keySplines="0.4 0 0.6 1;0 0 1 1"/>'
             f'<animate attributeName="opacity" dur="{dur}s" repeatCount="indefinite" '
             f'values="0;1;1;0;0" keyTimes="0;0.06;0.62;0.72;1"/></circle>')
    return "".join(b)


def search(c, x, y):
    """FindingExcellence: a lens hopping across local files; the file it lands on lights up."""
    b, dur = [], 10
    stops = [(1, 0), (3, 1), (0, 2), (2, 1)]
    cell = lambda i, j: (x + 24 + i * 28, y + 34 + j * 30)
    k = len(stops)
    for j in range(3):
        for i in range(4):
            cx, cy = cell(i, j)
            b.append(f'<rect x="{cx}" y="{cy}" width="18" height="22" rx="3" fill="{c["cell"]}" stroke="{c["line"]}">')
            if (i, j) in stops:
                s = stops.index((i, j))
                b.append(pulse(c["accent"], c["cell"], (s + 0.45) / k, (s + 0.95) / k, dur))
            b.append("</rect>")
            b.append(f'<line x1="{cx + 4}" y1="{cy + 8}" x2="{cx + 14}" y2="{cy + 8}" stroke="{c["line"]}" stroke-width="1.5"/>')
            b.append(f'<line x1="{cx + 4}" y1="{cy + 13}" x2="{cx + 11}" y2="{cy + 13}" stroke="{c["line"]}" stroke-width="1.5"/>')
    # lens rests on each stop for 40% of its slot, then eases to the next
    vals, kt = [], []
    for s, (i, j) in enumerate(stops):
        px, py = cell(i, j)
        vals += [f"{px + 9 - (x + 24)} {py + 11 - (y + 34)}"] * 2
        kt += [s / k, (s + 0.4) / k]
    vals.append(vals[0])
    kt.append(1)
    b.append(f'<g transform="translate({x + 24} {y + 34})">'
             f'<circle r="15" fill="none" stroke="{c["text"]}" stroke-width="2.5"/>'
             f'<line x1="11" y1="11" x2="19" y2="19" stroke="{c["text"]}" stroke-width="2.5" stroke-linecap="round"/>'
             f'<animateTransform attributeName="transform" type="translate" additive="sum" dur="{dur}s" '
             f'repeatCount="indefinite" calcMode="spline" values="{";".join(vals)}" '
             f'keyTimes="{";".join(f"{t:.4f}" for t in kt)}" keySplines="{";".join([EASE] * (len(vals) - 1))}"/>'
             f'</g>')
    return "".join(b)


def macropad(c, x, y):
    """ajazz-deck: the AKP153's 15 keys firing their mapped commands."""
    b, dur = [], 9
    seq = [7, 2, 11, 4, 13, 0, 9]
    for r in range(3):
        for col in range(5):
            idx = r * 5 + col
            kx, ky = x + 22 + col * 22, y + 45 + r * 22
            b.append(f'<rect x="{kx}" y="{ky}" width="18" height="18" rx="4" fill="{c["cell"]}" stroke="{c["line"]}">')
            if idx in seq:
                s = seq.index(idx)
                t0 = (s + 0.1) / len(seq)
                b.append(pulse(c["accent"], c["cell"], t0, t0 + 0.07, dur))
            b.append("</rect>")
    return "".join(b)


ARROW = "M0 10 L10 0 M2.5 0 H10 V7.5"

PROJECTS = [
    ("addocu", "Addocu", sheet,
     "Documents your whole Google marketing stack in seconds.",
     "Founder · open-source Google Sheets add-on · GA4 · GTM"),
    ("solodshouse", "SoloDShouse", lakehouse,
     "MSc thesis · AI inference energy and cost analytics.",
     "Python · Iceberg · MLflow · LangGraph · local-first"),
    ("findingexcellence", "FindingExcellence PRO", search,
     "File search with local AI. Nothing leaves your machine.",
     "Python · FastAPI · Ollama · zero external APIs"),
    ("ajazz-deck", "ajazz-deck", macropad,
     "Linux daemon + CLI for the AJAZZ AKP153 macro pad.",
     "Python · Linux · one YAML file maps every key"),
]


def card(c, name, title, draw, desc, meta):
    w, h = 880, 200
    b = [f'<rect x="24" y="24" width="152" height="152" rx="12" fill="{c["tile"]}" stroke="{c["line"]}"/>',
         draw(c, 24, 24),
         *([place(name, 208, 54, 34, c["text"])[0]] if (LOGOS / f"{name}.svg").exists() else []),
         text(208 + (44 if (LOGOS / f"{name}.svg").exists() else 0), 82, title, 32, c["text"], "GS", track=-0.025),
         text(208, 122, desc, 21, c["muted"]),
         text(208, 164, meta, 15, c["faint"], "GM"),
         f'<path d="{ARROW}" transform="translate(836 36)" fill="none" stroke="{c["faint"]}" '
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
        b.append(text(32, mid + 5, label, 14, c["faint"], "GM"))
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
    b += [f'<line x1="24" y1="{pad + r * row_h}" x2="{w - 24}" y2="{pad + r * row_h}" stroke="{c["line"]}"/>'
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
            b.append(f'<line x1="24" y1="{y}" x2="{w - 24}" y2="{y}" stroke="{c["line"]}"/>')
        last = i == n
        if not last:
            # checks draw once, in reading order, then hold (base offset 0 keeps them visible if SMIL never runs)
            t0 = (0.4 + i * 0.25) / dur
            b.append(f'<path d="M{34} {mid} l6 6 l12 -12" fill="none" stroke="{c["accent"]}" stroke-width="2.5" '
                     f'stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="26" stroke-dashoffset="0">'
                     f'<animate attributeName="stroke-dashoffset" dur="{dur}s" fill="freeze" '
                     f'values="26;26;0;0" keyTimes="0;{t0:.3f};{t0 + 0.4 / dur:.3f};1"/></path>')
        else:
            b.append(f'<path d="M34 {mid} h18 M34 {mid - 6} h18 M34 {mid + 6} h12" stroke="{c["faint"]}" '
                     f'stroke-width="2" stroke-linecap="round"/>')
        b.append(text(76, mid + 7, name, 20, c["muted"] if last else c["text"]))
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
        x, y = 24 + col * 420, 24 + row * 144
        b.append(f'<rect x="{x}" y="{y}" width="408" height="132" rx="12" fill="{c["tile"]}" stroke="{c["line"]}"/>')
        b.append(f'<path d="{shape}" transform="translate({x + 24} {y + 28}) scale(2)" fill="none" '
                 f'stroke="{c["muted"]}" stroke-width="1.25" stroke-linejoin="round" stroke-linecap="round"/>')
        b.append(text(x + 92, y + 48, title, 22, c["text"], "GS", track=-0.02))
        for k, line in enumerate(desc):
            b.append(text(x + 92, y + 80 + k * 24, line, 17, c["muted"]))
    flat = "; ".join(f"{t}: {' '.join(d)}" for _, t, d in FOCUS)
    return svg(w, h, f"Now building — {flat}", "".join(b), c)


# --------------------------------------------------------------------------- activity (live)

Q = """query($u:String!){user(login:$u){contributionsCollection{contributionCalendar{
totalContributions weeks{contributionDays{contributionCount date}}}}}}"""


def fetch_calendar():
    out = subprocess.run(["gh", "api", "graphql", "-f", f"query={Q}", "-F", f"u={USER}"],
                         check=True, capture_output=True, text=True).stdout
    cal = json.loads(out)["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    return cal["totalContributions"], [[(d["date"], d["contributionCount"]) for d in wk["contributionDays"]]
                                       for wk in cal["weeks"]]


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


def activity(c, total, weeks):
    w, h = 880, 292
    days = [d for wk in weeks for d in wk]
    cur, longest, active_days = streaks(days)
    peak = max(n for _, n in days) or 1
    stats = [(f"{total:,}", "contributions"), (f"{active_days}", "active days"),
             (f"{longest}", "longest streak"), (f"{cur}", "current streak")]
    b = []
    for i, (v, lab) in enumerate(stats):
        x = 40 + i * 200
        b.append(text(x, 72, v, 36, c["text"], "GS", track=-0.03))
        b.append(text(x, 98, lab, 14, c["faint"], "GM"))
    cell, gap = 12, 3
    x0, y0 = 40 + (800 - len(weeks) * (cell + gap) + gap) / 2, 140
    last_month = None
    for i, wk in enumerate(weeks):
        cx = x0 + i * (cell + gap)
        month = wk[0][0][:7]
        if month != last_month and (i or wk[0][0][8:] < "20"):  # skip a sliver of month at the left edge
            b.append(text(cx, y0 - 12, date.fromisoformat(wk[0][0]).strftime("%b"), 12, c["faint"], "GM"))
        last_month = month
        for d, n in wk:
            j = date.fromisoformat(d).isoweekday() % 7
            if n:
                lvl = 0.25 + 0.75 * min(1, math.sqrt(n / peak) * 1.3)
                b.append(f'<rect x="{cx:.1f}" y="{y0 + j * (cell + gap)}" width="{cell}" height="{cell}" rx="3" '
                         f'fill="{c["accent"]}" fill-opacity="{lvl:.2f}"/>')
            else:
                b.append(f'<rect x="{cx:.1f}" y="{y0 + j * (cell + gap)}" width="{cell}" height="{cell}" rx="3" '
                         f'fill="{c["cell"]}"/>')
    # sweep: cells stay static (visible in any renderer), one scan pass on arrival, then gone
    x_end = x0 + (len(weeks) - 1) * (cell + gap)
    b.append(f'<rect x="{x0 - 2}" y="{y0 - 2}" width="{cell + 4}" height="{7 * (cell + gap) - gap + 4}" rx="4" '
             f'fill="none" stroke="{c["accent"]}" stroke-width="1.5" opacity="0">'
             f'<animate attributeName="x" values="{x0 - 2};{x_end - 2}" dur="4s" fill="freeze" '
             f'calcMode="spline" keyTimes="0;1" keySplines="0.65 0 0.35 1"/>'
             f'<animate attributeName="opacity" values="0;.7;.7;0" keyTimes="0;.08;.9;1" dur="4.4s" fill="freeze"/>'
             f'</rect>')
    today = days[-1][0]
    b.append(text(w - 40, 270, f"last 12 months · updated {today}", 12, c["faint"], "GM", "end"))
    return svg(w, h, f"GitHub activity, last 12 months: {total:,} contributions, {active_days} active days, "
                     f"longest streak {longest} days, current streak {cur} days.", "".join(b), c)


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
                 "credentials": credentials(c), "focus": focus(c), "activity": activity(c, *cal),
                 "signature": signature(c)}
        for p in PROJECTS:
            files[f"card-{p[0]}"] = card(c, *p)
        for name, content in files.items():
            (OUT / f"{name}-{theme}.svg").write_text(content)
    print("\n".join(sorted(f"{p.name}  {p.stat().st_size // 1024}KB" for p in OUT.glob("*.svg"))))
