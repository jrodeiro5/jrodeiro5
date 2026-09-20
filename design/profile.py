"""The profile as four separate SVG sections (stats, about, milestones, stacks), driven by GitHub data.

Reuses page.py's fonts/text helpers and build.py's logos. Needs `gh` authenticated as the profile
owner (private contributions are only visible to the owner). Run: `.venv/bin/python design/profile.py`."""
import collections
import json
import math
import subprocess

import build as B
import page as P
from build import OUT, esc, place
from page import adv, t, wrap

W = 880
THEMES = {
    "light": dict(bg="#E7ECE6", ink="#0E1512", muted="#4C5A52", line="#C3CCC4", pub="#F26B1D", priv="#3B3BD8"),
    "dark": dict(bg="#101512", ink="#E7ECE6", muted="#93A29A", line="#2A332D", pub="#F58A4B", priv="#7C7CF0"),
}
DOMAINS = [("Programming", "#3B3BD8"), ("Marketing", "#C2510E"), ("Data", "#0B7F58")]
SHADES = ["#3B3BD8", "#5757E6", "#7C7CF0", "#9B9BF4", "#B8B8F7", "#CFCFF9", "#DEDEFB"]

STACKS = [  # ordered by how many of my local repos use each (see the stack survey in the commit message)
    [("python", "Python"), ("typescript", "TypeScript"), ("sql", "SQL"), ("react", "React"), ("nextdotjs", "Next.js"),
     ("fastapi", "FastAPI"), ("docker", "Docker"), ("modelcontextprotocol", "MCP")],
    [("googleanalytics", "GA4"), ("googletagmanager", "Tag Manager"), ("adobe", "Adobe Analytics"),
     ("lookerstudio", "Looker Studio"), ("powerbi", "Power BI"), ("tableau", "Tableau"), ("hotjar", "Hotjar")],
    [("googlebigquery", "BigQuery"), ("snowflake", "Snowflake"), ("duckdb", "DuckDB"), ("postgresql", "PostgreSQL"),
     ("supabase", "Supabase"), ("mlflow", "MLflow"), ("pandas", "pandas"), ("polars", "Polars")],
]

HEADLINE = "AI & Analytics Developer at cinfo · A Coruña"
ABOUT = ("AI & Analytics Developer at cinfo. Before that, two years of web and app analytics for PULL&BEAR "
         "(Inditex) at Ayesa, where I built OmniZenit, the official debugger for Inditex's in-house analytics tool. "
         "I started as a data analyst at Bysidecar, improving lead conversion for insurance, energy and telecom clients.")
RESEARCH = [("Agents and MCP", "MCP servers that give models real tools: GTM, documentation, media."),
            ("Knowledge systems", "Agent memory, RAG and search over what I save and read."),
            ("Local-first AI", "Models, speech and file search running on my own machine."),
            ("Data platforms", "Lakehouses and pipelines with DuckDB, Dagster and MLflow.")]
MILESTONES = [("2026", "AI & Analytics Developer at cinfo"),
              ("2025", "Talk at MeasureCamp Madrid on MCP servers in data and analytics"),
              ("2024–26", "Digital Data Analyst at Ayesa for PULL&BEAR (Inditex)"),
              ("2025–26", "MSc in Big Data, Data Science and AI, Complutense University"),
              ("2023–24", "Master in Web Analytics, KSchool"),
              ("2022–24", "Data Analyst, Call Center CRO at Bysidecar (insurance, energy and telecom clients)")]
ORANGE, INDIGO, GREEN, GREY = "#C2510E", "#3B3BD8", "#0B7F58", "#5B6B62"
# (logo slug or None, text mark, colour, accessible name); the badge itself is the label
CERTS = [("snowflake", "", GREEN, "Snowflake University Platform Skills Badge"),
         ("googleanalytics", "", ORANGE, "Google Analytics Individual Qualification"),
         ("adobe", "", ORANGE, "Adobe Analytics Foundations"),
         ("googlebigquery", "", GREEN, "Query GA4 Data in Google BigQuery (Simmer)"),
         (None, "SM", INDIGO, "Scrum Master (Scrum Manager)"),
         (None, "PO", INDIGO, "Product Owner (Scrum Manager)"),
         (None, "GB", INDIGO, "Six Sigma Green Belt (PMI)"),
         (None, "C2", GREY, "Cambridge C2 Proficiency in English")]


def gq(q, **v):
    a = ["gh", "api", "graphql", "-f", f"query={q}"] + [x for k, val in v.items() for x in ("-F", f"{k}={val}")]
    return json.loads(subprocess.run(a, check=True, capture_output=True, text=True).stdout)["data"]


def stats():
    u = gq("{viewer{createdAt contributionsCollection{contributionYears}}}")["viewer"]
    years = {}
    for y in sorted(u["contributionsCollection"]["contributionYears"]):
        c = gq("query($f:DateTime!,$t:DateTime!){viewer{contributionsCollection(from:$f,to:$t){totalCommitContributions"
               " totalPullRequestContributions restrictedContributionsCount contributionCalendar{totalContributions}}}}",
               f=f"{y}-01-01T00:00:00Z", t=f"{y}-12-31T23:59:59Z")["viewer"]["contributionsCollection"]
        years[y] = dict(total=c["contributionCalendar"]["totalContributions"], private=c["restrictedContributionsCount"],
                        commits=c["totalCommitContributions"], prs=c["totalPullRequestContributions"])
    langs, after, repos, private, stars, forks, names = collections.Counter(), None, 0, 0, 0, 0, []
    while True:
        r = gq("query($a:String){viewer{repositories(first:100,after:$a,ownerAffiliations:[OWNER,ORGANIZATION_MEMBER,COLLABORATOR],isFork:false){pageInfo"
               "{hasNextPage endCursor} nodes{nameWithOwner isPrivate stargazerCount forkCount languages(first:8,orderBy:{field:SIZE,direction:DESC})"
               "{edges{size node{name}}}}}}}", **({"a": after} if after else {}))["viewer"]["repositories"]
        for n in r["nodes"]:
            repos, private = repos + 1, private + n["isPrivate"]
            stars, forks = stars + n["stargazerCount"], forks + n["forkCount"]
            names.append(n["nameWithOwner"])
            for e in n["languages"]["edges"]:
                langs[e["node"]["name"]] += e["size"]
        if not r["pageInfo"]["hasNextPage"]:
            break
        after = r["pageInfo"]["endCursor"]
    langs.pop("Jupyter Notebook", None)  # notebooks store outputs, not code: they would swamp the share
    tot = sum(langs.values())
    top = [(k, 100 * v / tot) for k, v in langs.most_common(6)]
    top.append(("Other", 100 - sum(p for _, p in top)))
    since = min(years) if years else 0
    v = gq("{viewer{id login repositoriesContributedTo(first:1,contributionTypes:[COMMIT,PULL_REQUEST]){totalCount}}}")["viewer"]
    add, dele = lines(v["id"], names)
    return dict(years=years, langs=top, repos=repos, private=private, since=since, start=u["createdAt"][:7],
                stars=stars, forks=forks, contributed=v["repositoriesContributedTo"]["totalCount"], added=add, deleted=dele)


def lines(uid, names):
    """Lines added/deleted by me on each owned or organisation repo's default branch (GraphQL commit history, paged)."""
    add = dele = 0
    for full in names:
        owner, name = full.split("/")
        after = None
        while True:
            r = gq("query($o:String!,$n:String!,$id:ID!,$a:String){repository(owner:$o,name:$n){defaultBranchRef{target{... on Commit{"
                   "history(first:100,after:$a,author:{id:$id}){pageInfo{hasNextPage endCursor} nodes{additions deletions}}}}}}}",
                   o=owner, n=name, id=uid, **({"a": after} if after else {}))["repository"]["defaultBranchRef"]
            if not r:  # empty repository
                break
            h = r["target"]["history"]
            add, dele = add + sum(c["additions"] for c in h["nodes"]), dele + sum(c["deletions"] for c in h["nodes"])
            if not h["pageInfo"]["hasNextPage"]:
                break
            after = h["pageInfo"]["endCursor"]
    return add, dele


def compact(n):
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M".replace(".0M", "M")
    return f"{n / 1000:.1f}k".replace(".0k", "k") if n >= 1000 else str(n)


def frame(h, title, body, c):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" viewBox="0 0 {W} {h}" role="img" '
            f'aria-label="{esc(title)}"><title>{esc(title)}</title><style>{P.CSS}</style>'
            f'<rect width="{W}" height="{h}" fill="{c["bg"]}"/>{body}</svg>')


def month(ym):
    y, m = ym.split("-")
    return f"{['January','February','March','April','May','June','July','August','September','October','November','December'][int(m) - 1]} {y}"


def stats_svg(s, c):
    yrs = s["years"]
    tot = sum(v["total"] for v in yrs.values())
    priv = sum(v["private"] for v in yrs.values())
    pct = round(100 * priv / tot)
    b = [t(32, 96, f"{tot:,}", 84, c["ink"], "SB"),
         t(32 + adv(f"{tot:,}", 84, "SB") + 18, 96, f"{pct}%", 84, c["priv"], "SB"),
         t(32, 128, f"contributions since {month(s['start'])}; {pct}% of them are in private repositories.", 17, c["muted"])]
    # language stripe: one scale, labels only where the segment can hold them
    x, y0, sh, sw = 32, 168, 56, W - 64
    for i, (k, p) in enumerate(s["langs"]):
        w = sw * p / 100
        b.append(f'<rect x="{x:.1f}" y="{y0}" width="{max(w - 2, 1):.1f}" height="{sh}" fill="{SHADES[i]}"/>')
        if adv(k, 13) + 16 < w:
            b.append(t(round(x + 10, 1), y0 + sh - 12, k, 13, "#fff" if i < 3 else "#1B1B5A", "SB"))
        x += w
    # always-visible legend: an <img> SVG has no hover, so every share is printed, small ones included
    lx, ly = 32, y0 + sh + 26
    for i, (k, p) in enumerate(s["langs"]):
        lab = f"{k} {p:.1f}%"
        if lx + 22 + adv(lab, 13) > W - 32:
            lx, ly = 32, ly + 22
        b.append(f'<rect x="{lx}" y="{ly - 10}" width="10" height="10" fill="{SHADES[i]}"/>')
        b.append(t(lx + 16, ly, lab, 13, c["ink"]))
        lx += 16 + adv(lab, 13) + 22
    b.append(t(32, ly + 28, f"Share of code by size across {s['repos']} repositories, organisations included, notebooks excluded.", 13, c["muted"]))
    # history: stacked private/public per year
    top, base, cw = 350, 450, 384
    mx = max(v["total"] for v in yrs.values())
    sc = lambda v: (base - top) * v / mx  # noqa: E731 — one scale for bars and labels
    n = len(yrs)
    step = cw / n
    for i, (yr, v) in enumerate(yrs.items()):
        bx, bw = 32 + step * i + step * 0.2, step * 0.6
        pub = v["total"] - v["private"]
        b.append(f'<rect x="{bx:.1f}" y="{base - sc(v["private"]):.1f}" width="{bw:.1f}" height="{sc(v["private"]):.1f}" fill="{c["priv"]}"/>')
        b.append(f'<rect x="{bx:.1f}" y="{base - sc(v["total"]):.1f}" width="{bw:.1f}" height="{max(sc(pub), 1):.1f}" fill="{c["pub"]}"/>')
        b.append(t(round(bx + bw / 2, 1), round(base - sc(v["total"]) - 8, 1), f"{v['total']:,}", 13, c["ink"], "M", "middle"))
        b.append(t(round(bx + bw / 2, 1), base + 20, str(yr), 12, c["muted"], "M", "middle"))
    b.append(f'<line x1="32" x2="{32 + cw}" y1="{base}" y2="{base}" stroke="{c["line"]}"/>')
    lx = 32
    for lab, col in (("Private", c["priv"]), ("Public", c["pub"])):
        b.append(f'<rect x="{lx}" y="{base + 34}" width="10" height="10" fill="{col}"/>')
        b.append(t(lx + 16, base + 43, lab, 12, c["muted"], "M"))
        lx += 24 + adv(lab, 12, "M") + 12
    # figures for the latest year
    cur = list(yrs.items())[-1]
    figs = [(f"{cur[1]['total']:,}", f"contributions in {cur[0]}"),
            (str(cur[1]["prs"]), f"pull requests, {cur[1]['commits']} commits"),
            (f"{s['private']} of {s['repos']}", "repositories are private"),
            (f"{s['stars']} / {s['forks']}", "stars / forks on my repos"),
            (f"{s['contributed']}", "repositories contributed to"),
            (compact(s["added"]) + " / " + compact(s["deleted"]), "lines added / deleted")]
    for i, (big, lab) in enumerate(figs):
        fy = 372 + (i % 3) * 54
        cx = 460 + (i // 3) * 200
        b.append(t(cx, fy, big, 26, c["ink"], "SB"))
        b.append(t(cx, fy + 20, lab, 12, c["muted"]))
    return frame(520, f"GitHub activity: {tot:,} contributions, {pct}% private.", "".join(b), c)


def about_svg(c):
    b = [t(32, 52, "About", 13, c["muted"], "M")]
    y = 90
    for ln in wrap(ABOUT, 19, W - 64):
        b.append(t(32, y, ln, 19, c["ink"]))
        y += 29
    y += 24
    b.append(t(32, y, "Research lines", 13, c["muted"], "M"))
    y += 32
    col = (W - 64 - 32) / 2
    for i, (h, d) in enumerate(RESEARCH):
        cx, cy = 32 + (i % 2) * (col + 32), y + (i // 2) * 96
        b.append(f'<line x1="{cx}" x2="{cx + col}" y1="{cy - 22}" y2="{cy - 22}" stroke="{c["line"]}"/>')
        b.append(t(cx, cy, h, 19, c["ink"], "SB"))
        for j, ln in enumerate(wrap(d, 15, col)):
            b.append(t(cx, cy + 26 + j * 21, ln, 15, c["muted"]))
    return frame(y + 2 * 96 + 8, "About and research lines.", "".join(b), c)


def badge(x, y, r, slug, mark, col, c, rot):
    """Round merit-badge patch: coloured disc, stitched ring, white logo or text mark."""
    g = [f'<circle r="{r}" fill="{col}" stroke="{c["bg"]}" stroke-width="4"/>',
         f'<circle r="{r - 7}" fill="none" stroke="#fff" stroke-opacity=".55" stroke-width="1.5" stroke-dasharray="3 3"/>']
    if slug:
        inner, lw = place(slug, 0, 0, 34, "#fff")
        g.append(f'<g transform="translate({-lw / 2:.1f} -17)">{inner}</g>')
    else:
        g.append(t(0, 10, mark, 28, "#fff", "SB", "middle"))
    return f'<g transform="translate({x} {y}) rotate({rot})">{"".join(g)}</g>'


def milestones_svg(c):
    b = [t(32, 52, "Milestones", 13, c["muted"], "M")]
    for i, (yr, what) in enumerate(MILESTONES):
        y = 92 + i * 44
        b.append(f'<line x1="32" x2="{W - 32}" y1="{y - 27}" y2="{y - 27}" stroke="{c["line"]}"/>')
        b.append(t(32, y, yr, 15, c["priv"], "M"))
        b.append(t(150, y, what, 17, c["ink"]))
    cy = 92 + len(MILESTONES) * 44 + 12
    b.append(t(32, cy, "Certifications", 13, c["muted"], "M"))
    r, step = 46, 86  # step < 2r: patches overlap like badges on a sash
    for i, (slug, mark, col, _) in enumerate(CERTS):
        b.append(badge(32 + r + i * step, cy + 72 + (-10 if i % 2 else 10), r, slug, mark, col, c, 6 if i % 2 else -6))
    return frame(cy + 150, "Milestones and certifications.", "".join(b), c)


def stacks_svg(c):
    rows, row_h, top, vx = len(STACKS), 92, 44, 32
    h = top + rows * row_h
    vw = W - 64
    b = [f'<defs><clipPath id="vp"><rect x="{vx}" y="0" width="{vw}" height="{h}"/></clipPath>'
         f'<linearGradient id="fl"><stop offset="0" stop-color="{c["bg"]}"/><stop offset="1" stop-color="{c["bg"]}" stop-opacity="0"/></linearGradient>'
         f'<linearGradient id="fr"><stop offset="0" stop-color="{c["bg"]}" stop-opacity="0"/><stop offset="1" stop-color="{c["bg"]}"/></linearGradient></defs>',
         t(32, 30, "Stack", 13, c["muted"], "M")]
    names = []
    for r, ((label, col), items) in enumerate(zip(DOMAINS, STACKS)):
        ry = top + r * row_h
        b.append(t(32, ry + 14, label, 12, c["muted"], "M"))
        x, band = 0.0, []
        for slug, name in items:
            inner, lw = place(slug, 0, 0, 18, "#fff")
            pw = 14 + lw + (8 + adv(name, 14, "SB") if name else 0) + 14
            band.append(f'<rect x="{x:.1f}" y="{ry + 26}" width="{pw:.1f}" height="40" rx="20" fill="{col}"/>')
            band.append(f'<g transform="translate({x + 14:.1f} {ry + 37})">{inner}</g>')
            if name:
                band.append(t(round(x + 14 + lw + 8, 1), ry + 51, name, 14, "#fff", "SB"))
            x += pw + 10
            names.append(name)
        period = round(x)
        reps = math.ceil(vw / period) + 1
        tiles = f'<g id="s{r}">{"".join(band)}</g>' + "".join(f'<use href="#s{r}" x="{k * period}"/>' for k in range(1, reps))
        a, z = (0, -period) if r % 2 == 0 else (-period, 0)
        b.append(f'<g clip-path="url(#vp)"><g transform="translate({vx + 24} 0)"><g>{tiles}'
                 f'<animateTransform attributeName="transform" type="translate" from="{a} 0" to="{z} 0" '
                 f'dur="{period / 30:.1f}s" repeatCount="indefinite"/></g></g></g>')
    for r in range(rows):  # fade only the pills, never the row labels, and only a short edge
        fy = top + r * row_h + 26
        b.append(f'<rect x="{vx}" y="{fy}" width="24" height="40" fill="url(#fl)"/>')
        b.append(f'<rect x="{vx + vw - 24}" y="{fy}" width="24" height="40" fill="url(#fr)"/>')
    return frame(h, "Stack: " + ", ".join(names) + ".", "".join(b), c)


def readme(s):
    """README.md is generated too, so no number or list lives in it by hand (alt text included)."""
    tot = sum(v["total"] for v in s["years"].values())
    pct = round(100 * sum(v["private"] for v in s["years"].values()) / tot)
    top = ", ".join(f"{k} {p:.0f}%" for k, p in s["langs"][:3])
    alts = {
        "stats": f"GitHub activity: {tot:,} contributions since {month(s['start'])}, {pct}% in private repositories. Languages: {top}.",
        "stacks": "Stack. " + " ".join(f"{d}: {', '.join(n for _, n in items)}."
                                       for (d, _), items in zip(DOMAINS, STACKS)),
        "about": f"About: {ABOUT} Research lines: {', '.join(h for h, _ in RESEARCH)}.",
        "milestones": "Milestones: " + "; ".join(f"{y}, {w}" for y, w in MILESTONES) + ". Certifications: " + "; ".join(k[3] for k in CERTS) + ".",
    }
    pics = "\n<br>\n".join(
        f'<picture>\n  <source media="(prefers-color-scheme: dark)" srcset="assets/{n}-dark.svg" />\n'
        f'  <img alt="{esc(a).replace(chr(34), "&quot;")}" src="assets/{n}-light.svg" width="100%" />\n</picture>'
        for n, a in alts.items())
    return f"""<h1 align="center">Javier Rodeiro</h1>
<p align="center">{esc(HEADLINE)}</p>

<p align="center">
  <a href="https://javierrodeiro.com">javierrodeiro.com</a> &nbsp;·&nbsp;
  <a href="https://linkedin.com/in/javier-rodeiro-rodriguez">LinkedIn</a> &nbsp;·&nbsp;
  <a href="https://www.linkedin.com/newsletters/puppets-scripts-7290366362223284224/">Puppets &amp; Scripts</a> &nbsp;·&nbsp;
  <a href="mailto:hello@javierrodeiro.com">hello@javierrodeiro.com</a>
</p>

{pics}
"""


if __name__ == "__main__":
    s = stats()
    for name, mode in THEMES.items():
        for f, svg in (("stats", stats_svg(s, mode)), ("about", about_svg(mode)),
                       ("milestones", milestones_svg(mode)), ("stacks", stacks_svg(mode))):
            (OUT / f"{f}-{name}.svg").write_text(svg)
    (OUT.parent / "README.md").write_text(readme(s))
    print("ok", s["since"], len(s["years"]), "years")
