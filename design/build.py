"""Generate the profile README SVGs (light + dark) into ../assets.

Run:  uv run --with fonttools --with brotli design/build.py
"""

import base64
import io
import math
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent
OUT = ROOT.parent / "assets"
FONTS = ROOT / "fonts"

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
FUNNEL = [(3, 4), (21, 4), (14, 12.5), (14, 20), (10, 22), (10, 12.5)]
LOOP = [(12 + 10 * math.cos(t) / (1 + math.sin(t) ** 2),
         12 + 10 * math.sin(t) * math.cos(t) / (1 + math.sin(t) ** 2))
        for t in (2 * math.pi * i / 72 for i in range(72))]


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


# --------------------------------------------------------------------------- principles


def principles(c):
    w, h = 880, 248
    b = []
    tx, ty, ts = 48, 40, 144
    b.append(f'<rect x="{tx}" y="{ty}" width="{ts}" height="{ts}" rx="14" fill="{c["tile"]}" stroke="{c["line"]}"/>')
    b.append(morph([FUNNEL, LOOP], 4, tx + 24, ty + 24, 7, 0.7, c["accent"], 4.5))
    for i, word in enumerate(["funnel", "loop"]):
        on, off = (c["faint"], "transparent")
        b.append(f'<text x="{tx + ts / 2}" y="{ty + ts + 30}" class="GM" font-size="13" text-anchor="middle" '
                 f'fill="{on if i == 0 else off}">{word}'
                 f'<animate attributeName="fill" dur="7s" repeatCount="indefinite" calcMode="discrete" '
                 f'values="{on if i == 0 else off};{off if i == 0 else on};{on if i == 0 else off}" '
                 f'keyTimes="0;0.5;1"/></text>')
    lines = ["Loops over funnels.", "Get feedback early, deliver often.",
             "Retention is the foundation.", "Quality is a feature."]
    for i, s in enumerate(lines):
        b.append(text(248, 76 + i * 42, s, 24, c["text"] if i == 0 else c["muted"], "G", track=-0.01))
    return svg(w, h, "Principles: loops over funnels; get feedback early, deliver often; "
                     "retention is the foundation; quality is a feature.", "".join(b), c)


# --------------------------------------------------------------------------- project cards


def anim(attr, values, times, dur):
    return (f'<animate attributeName="{attr}" dur="{dur}s" repeatCount="indefinite" calcMode="discrete" '
            f'values="{";".join(values)}" keyTimes="{";".join(f"{t:.4f}" for t in times)}"/>')


def pulse(on, off, t0, t1, dur, attr="fill"):
    return anim(attr, [off, on, off], [0, t0, t1], dur)


def sheet(c, x, y):
    """Addocu: an audit sheet documenting itself row by row."""
    b, dur = [], 6
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
    b, dur = [], 3.2
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
    b, dur = [], 7.2
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
    b, dur = [], 6
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
         text(208, 82, title, 32, c["text"], "GS", track=-0.025),
         text(208, 122, desc, 21, c["muted"]),
         text(208, 164, meta, 15, c["faint"], "GM"),
         f'<path d="{ARROW}" transform="translate(836 36)" fill="none" stroke="{c["faint"]}" '
         f'stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/>']
    return svg(w, h, f"{title} — {desc}", "".join(b), c)


# --------------------------------------------------------------------------- write

if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    for theme, c in THEMES.items():
        files = {"hero": hero(c), "principles": principles(c)}
        for p in PROJECTS:
            files[f"card-{p[0]}"] = card(c, *p)
        for name, content in files.items():
            (OUT / f"{name}-{theme}.svg").write_text(content)
    print("\n".join(sorted(f"{p.name}  {p.stat().st_size // 1024}KB" for p in OUT.glob("*.svg"))))
