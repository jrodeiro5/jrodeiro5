"""The whole profile as one docs page: a single SVG, sidebar + column, in the manner of vlak.dev/docs.

GitHub strips HTML/CSS from a README, so the only way to get one unified block is one <img>. This
reuses the content tables and helpers of build.py (logos, toolkit, focus icons, calendar fetch) and
lays them out on a sans, monochrome page. Run: `.venv/bin/python design/page.py`."""
import email.utils
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date

from fontTools.ttLib import TTFont

import build as B
from build import FONTS, OUT, esc, place

W, BAR, SIDE, X0, XW = 880, 64, 184, 216, 616  # page, top bar, sidebar edge, column start, column width
FEED = "https://linkedinrss.cns.me/7290366362223284224"

THEMES = {
    "light": dict(bg="#F9F8F4", ink="#1A1A18", muted="#6B6A65", faint="#9A988F", line="#E4E2DA", tile="#F2F0E9"),
    "dark": dict(bg="#131312", ink="#F2F0EA", muted="#A19F97", faint="#6E6C66", line="#2A2A27", tile="#1A1A18"),
}
FACES = {"S": ("Geist-Regular.ttf", 400), "SB": ("Geist-SemiBold.ttf", 600), "M": ("GeistMono-Regular.ttf", 400)}
STACK = {"S": "S,ui-sans-serif,system-ui,sans-serif", "SB": "SB,ui-sans-serif,system-ui,sans-serif",
         "M": "M,ui-monospace,Menlo,monospace"}
CSS = "".join(f"@font-face{{font-family:{k};src:url(data:font/woff2;base64,{B.woff2(f)}) format('woff2');"
              f"font-weight:{w}}}.{k}{{font-family:{STACK[k]}}}" for k, (f, w) in FACES.items()) + "text{font-kerning:normal}"

_ADV = {}


def adv(s, size, face="S"):
    if face not in _ADV:
        f = TTFont(FONTS / FACES[face][0])
        cmap, hmtx, upm = f.getBestCmap(), f["hmtx"], f["head"].unitsPerEm
        _ADV[face] = {ch: hmtx[cmap[ord(ch)]][0] / upm for ch in B.CHARS if ord(ch) in cmap}
    return sum(_ADV[face].get(ch, 0.6) for ch in s) * size


def t(x, y, s, size, fill, face="S", anchor="start"):
    return (f'<text x="{x}" y="{y}" class="{face}" font-size="{size}" fill="{fill}" '
            f'text-anchor="{anchor}">{esc(s)}</text>')


def wrap(s, size, width, face="S"):
    lines, cur = [], ""
    for word in s.split():
        if cur and adv(f"{cur} {word}", size, face) > width * 0.97:  # 3% slack: kerning is not measured
            lines.append(cur)
            cur = word
        else:
            cur = f"{cur} {word}".strip()
    return lines + [cur]


def posts():
    """Latest newsletter issues; the page still builds without them if the feed is down."""
    try:
        with urllib.request.urlopen(urllib.request.Request(FEED, headers={"User-Agent": "Mozilla/5.0"}), timeout=15) as r:
            items = ET.parse(r).getroot().iter("item")
            return [(i.findtext("title"), email.utils.parsedate_to_datetime(i.findtext("pubDate")).strftime("%b %Y"))
                    for i in list(items)[:5]]
    except Exception as e:  # noqa: BLE001 — a dead feed must not block the daily activity refresh
        print(f"feed skipped: {e}")
        return []


ABOUT = ("At cinfo I build AI and analytics solutions on a fully open-source stack. Before that I spent two "
         "years running web and app analytics for PULL&BEAR (Inditex) at Ayesa, where a Chrome extension I "
         "wrote for GA4 validation, OmniZenit, became the tool every Inditex brand's digital analytics team "
         "uses. I'm finishing an MSc in Big Data, Data Science & AI at Complutense University of Madrid.")
TALKS = [("MeasureCamp Madrid 2025", "MCP servers in data & analytics"),
         ("Datola", "Agile Analysis with AI, a series"),
         ("Puppets & Scripts", "Newsletter on AI, data and building things")]
PATH = [("2026 —", "cinfo", "AI & Analytics Developer"),
        ("2024–26", "Ayesa for PULL&BEAR / Inditex", "Digital Data Analyst"),
        ("2022–24", "Bysidecar", "Data Analyst"),
        ("2025–26", "Complutense University of Madrid", "MSc Big Data, Data Science & AI"),
        ("2023–24", "KSchool", "Master in Web Analytics"),
        ("2018–22", "San Jorge University", "BA Advertising & Public Relations")]
NAV = [("Start", ["About", "Work"]), ("Foundations", ["Building", "Toolkit", "Credentials"]),
       ("Build", ["Activity", "Writing", "Path"])]


def page(c, cal, feed):
    b, y = [], BAR + 64
    ink, muted, faint, line = c["ink"], c["muted"], c["faint"], c["line"]

    def h2(label, blurb=None):
        nonlocal y
        b.append(f'<line x1="{X0}" y1="{y}" x2="{X0 + XW}" y2="{y}" stroke="{line}"/>')
        y += 40
        b.append(t(X0, y, label, 20, ink, "SB"))
        y += 10
        if blurb:
            y += 20
            b.append(t(X0, y, blurb, 14, muted))
        y += 24

    # hero
    b.append(t(X0, y, "Javier Rodeiro", 48, ink, "SB"))
    y += 36
    for ln in wrap("AI & Analytics Developer at cinfo. Clean data, rigorous validation, and when the tool "
                   "doesn’t exist, I build it.", 19, XW):
        y += 6 + 19
        b.append(t(X0, y, ln, 19, muted))
    y += 40
    for ln in wrap(ABOUT, 15, XW):
        b.append(t(X0, y, ln, 15, ink))
        y += 24
    y += 24

    # selected work: one bordered row per project, a table rather than four cards
    h2("Work", "Open source, research and things I needed that did not exist.")
    for name, title, desc, meta in B.PROJECTS:
        b.append(f'<line x1="{X0}" y1="{y}" x2="{X0 + XW}" y2="{y}" stroke="{line}"/>')
        lx = X0
        if (B.LOGOS / f"{name}.svg").exists():
            g, lw = place(name, X0, y + 20, 22, ink)
            b.append(g)
            lx += lw + 12
        b.append(t(lx, y + 38, title, 17, ink, "SB"))
        b.append(t(X0 + XW, y + 38, "↗", 15, faint, "S", "end"))
        b.append(t(X0, y + 66, desc, 14, muted))
        b.append(t(X0, y + 88, meta, 12, faint, "M"))
        y += 112
    b.append(f'<line x1="{X0}" y1="{y}" x2="{X0 + XW}" y2="{y}" stroke="{line}"/>')
    y += 24

    # now building: a 2x2 grid of ruled cells, the component-grid look of the reference
    h2("Building", "What the last months of work have been about.")
    cw, ch = XW // 2, 128
    for i, (shape, title, desc) in enumerate(B.FOCUS):
        cx, cy = X0 + (i % 2) * cw, y + (i // 2) * ch
        b.append(f'<rect x="{cx}" y="{cy}" width="{cw}" height="{ch}" fill="{c["tile"]}" stroke="{line}"/>')
        b.append(f'<path d="{shape}" transform="translate({cx + 20} {cy + 22}) scale(1.4)" fill="none" '
                 f'stroke="{muted}" stroke-width="1.5" stroke-linejoin="round" stroke-linecap="round"/>')
        b.append(t(cx + 20, cy + 76, title, 15, ink, "SB"))
        for k, ln in enumerate(desc):
            b.append(t(cx + 20, cy + 98 + k * 18, ln, 13, muted))
    y += ch * 2 + 24

    # toolkit: label column + flowing names, wrapped inside the column
    h2("Toolkit")
    lab_w = 96
    for label, items in B.TOOLKIT:
        b.append(f'<line x1="{X0}" y1="{y}" x2="{X0 + XW}" y2="{y}" stroke="{line}"/>')
        b.append(t(X0, y + 34, label, 12, faint, "M"))
        x, ry = X0 + lab_w, y + 16
        for slug, name in items:
            iw = 16 + 6 if slug else 0
            w_ = iw + (adv(name, 14) if name else 0)
            if x + w_ > X0 + XW:
                x, ry = X0 + lab_w, ry + 28
            if slug:
                b.append(place(slug, x, ry + 4, 16, muted)[0])
            if name:
                b.append(t(x + iw, ry + 17, name, 14, muted))
            x += w_ + 22
        y = ry + 44
    b.append(f'<line x1="{X0}" y1="{y}" x2="{X0 + XW}" y2="{y}" stroke="{line}"/>')
    y += 24

    h2("Credentials")
    for i, (name, issuer, slug) in enumerate(B.CREDENTIALS + [(B.PRACTICE, "practice", None)]):
        b.append(f'<line x1="{X0}" y1="{y}" x2="{X0 + XW}" y2="{y}" stroke="{line}"/>')
        mark = "M0 0" if slug is None else f"M{X0} {y + 25} l4 4 l8 -8"
        b.append(f'<path d="{mark}" fill="none" stroke="{ink}" stroke-width="1.8" stroke-linecap="round" '
                 f'stroke-linejoin="round"/>')
        b.append(t(X0 + 26, y + 30, name, 14, ink if slug else muted))
        if slug:
            lw = place(slug, 0, 0, 16, "")[1]
            b.append(place(slug, X0 + XW - lw, y + 16, 16, muted)[0])
        y += 48
    b.append(f'<line x1="{X0}" y1="{y}" x2="{X0 + XW}" y2="{y}" stroke="{line}"/>')
    y += 24

    # activity: real numbers, the year as one square per day
    weeks = cal["weeks"]
    days = [d for wk in weeks for d in wk]
    cur, longest, active_days = B.streaks(days)
    total = sum(n for _, n in days)
    peak = max(n for _, n in days) or 1
    h2("Activity", f"Last 12 months, updated {days[-1][0]}.")
    stats = [(f"{total:,}", "contributions"), (str(active_days), "active days"), (str(longest), "longest streak"),
             (str(cur), "current streak")]
    for k, (v, lab) in enumerate(stats):
        sx = X0 + k * (XW // 4)
        b.append(t(sx, y + 28, v, 30, ink, "SB"))
        b.append(t(sx, y + 50, lab, 12, faint, "M"))
    y += 76
    for k, (v, lab) in enumerate([(cal["commits"], "commits"), (cal["prs"], "pull requests"),
                                  (cal["reviews"], "reviews"), (cal["repos"], "repositories")]):
        sx = X0 + k * (XW // 4)
        b.append(t(sx, y + 14, f"{v:,}", 15, muted, "SB"))
        b.append(t(sx + adv(f"{v:,}", 15, "SB") + 6, y + 14, lab, 11, faint, "M"))
    y += 44
    cell, gap, t0, span = 9, 2, 0.3, 3.0
    gx = X0 + (XW - (len(weeks) * (cell + gap) - gap)) / 2
    b.append(f'<defs><rect id="d" width="{cell}" height="{cell}" rx="2"/></defs>')
    for i, wk in enumerate(weeks):
        cx, col = gx + i * (cell + gap), []
        for d, n in wk:
            j = date.fromisoformat(d).isoweekday() % 7
            op = f'fill="{ink}" fill-opacity="{0.22 + 0.78 * min(1, (n / peak) ** 0.5 * 1.3):.2f}"' if n \
                else f'fill="{line}"'
            col.append(f'<use href="#d" x="{cx:.1f}" y="{y + j * (cell + gap)}" {op}/>')
        st = t0 + span * i / max(1, len(weeks) - 1)
        # drawn whole; the <set> hides it only where SMIL runs, so a renderer without SMIL keeps the finished grid
        b.append(f'<g>{"".join(col)}<set attributeName="opacity" to="0" begin="0s"/>'
                 f'<animate attributeName="opacity" values="0;1" begin="{st:.2f}s" dur="0.4s" fill="freeze"/></g>')
    y += 7 * (cell + gap) + 32

    h2("Writing", "Talks and the newsletter.")
    for name, blurb in TALKS:
        b.append(f'<line x1="{X0}" y1="{y}" x2="{X0 + XW}" y2="{y}" stroke="{line}"/>')
        b.append(t(X0, y + 30, name, 14, ink, "SB"))
        b.append(t(X0 + XW, y + 30, blurb, 13, muted, "S", "end"))
        y += 44
    for title, when in feed:
        while adv(title, 13) > XW - 100:
            title = title[:-2].rstrip() + "…"
        b.append(f'<line x1="{X0}" y1="{y}" x2="{X0 + XW}" y2="{y}" stroke="{line}"/>')
        b.append(t(X0, y + 30, title, 13, muted))
        b.append(t(X0 + XW, y + 30, when, 12, faint, "M", "end"))
        y += 40
    b.append(f'<line x1="{X0}" y1="{y}" x2="{X0 + XW}" y2="{y}" stroke="{line}"/>')
    y += 24

    h2("Path")
    for when, org, role in PATH:
        b.append(f'<line x1="{X0}" y1="{y}" x2="{X0 + XW}" y2="{y}" stroke="{line}"/>')
        b.append(t(X0, y + 30, when, 12, faint, "M"))
        b.append(t(X0 + 92, y + 30, org, 14, ink, "SB"))
        b.append(t(X0 + XW, y + 30, role, 13, muted, "S", "end"))
        y += 44
    b.append(f'<line x1="{X0}" y1="{y}" x2="{X0 + XW}" y2="{y}" stroke="{line}"/>')
    y += 36
    b.append(t(X0, y, "Spanish and Galician (native) · English (C2) · French (working). Based in A Coruña.",
               12, faint, "M"))
    h = y + 48

    # chrome, drawn last so it sits over nothing: top bar, sidebar and the two grid rules
    chrome = [f'<line x1="0" y1="{BAR}" x2="{W}" y2="{BAR}" stroke="{line}"/>',
              f'<line x1="{SIDE}" y1="0" x2="{SIDE}" y2="{h}" stroke="{line}"/>',
              f'<line x1="{X0 + XW + 16}" y1="{BAR}" x2="{X0 + XW + 16}" y2="{h}" stroke="{line}"/>',
              f'<rect x="24" y="22" width="20" height="20" rx="4" fill="{ink}"/>',
              t(34, 37, "J", 13, c["bg"], "SB", "middle"),
              t(X0, 38, "Javier Rodeiro", 14, ink, "SB")]
    for k, item in enumerate(["javierrodeiro.com", "LinkedIn", "GitHub"]):
        chrome.append(t(W - 24 - sum(adv(n, 13) + 24 for n in ["javierrodeiro.com", "LinkedIn", "GitHub"][k + 1:]),
                        38, item, 13, muted, "S", "end"))
    ny = BAR + 40
    for group, items in NAV:
        chrome.append(t(24, ny, group, 12, muted, "SB"))
        ny += 26
        for it in items:
            chrome.append(t(24, ny, it, 14, ink if it == "About" else muted))
            ny += 28
        ny += 16
    summary = (f"Javier Rodeiro, AI & Analytics Developer at cinfo. {ABOUT} "
               f"GitHub, last 12 months: {total:,} contributions, {active_days} active days, longest streak "
               f"{longest} days, current streak {cur} days.")
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" viewBox="0 0 {W} {h}" role="img" '
            f'aria-label="{esc(summary)}"><title>Javier Rodeiro</title><style>{CSS}</style>'
            f'<rect width="{W}" height="{h}" fill="{c["bg"]}"/>{"".join(b)}{"".join(chrome)}</svg>')


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    cal, feed = B.fetch_calendar(), posts()
    for theme, c in THEMES.items():
        (OUT / f"profile-{theme}.svg").write_text(page(c, cal, feed))
    print("\n".join(f"{p.name}  {p.stat().st_size // 1024}KB" for p in sorted(OUT.glob("profile-*.svg"))))
