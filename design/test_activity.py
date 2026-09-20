"""Check the activity SVG. Run: uv run --with fonttools --with brotli design/test_activity.py

The failure mode this guards is silent: the playback hides everything at t=0 and reveals it on a
schedule, so a bug leaves an empty card for every renderer that ignores SMIL — GitHub's image
cache, social previews, RSS readers — and looks perfect in a browser.
"""
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

SVG = Path(__file__).resolve().parent.parent / "assets" / "activity-dark.svg"
NS = "{http://www.w3.org/2000/svg}"


def main():
    src = SVG.read_text()
    root = ET.fromstring(src)

    # 1. what a renderer without SMIL draws: every element at its own attribute values
    odo = [g for g in root.iter(f"{NS}g") if g.get("class") == "GS" and g.get("font-size") == "36"]
    assert len(odo) == 4, f"expected 4 odometers, got {len(odo)}"
    for g in odo:
        shown = [t for t in g if t.get("opacity") != "0"]
        assert len(shown) == 1, f"odometer draws {len(shown)} numbers without SMIL, must draw 1"
        assert shown[0] is g[-1], "the visible number is not the last one (not the final value)"

    cols = [g for g in root.iter(f"{NS}g") if any(u.tag == f"{NS}use" for u in g)]
    assert 52 <= len(cols) <= 54, f"expected ~53 week columns, got {len(cols)}"
    for g in cols:
        assert g.get("opacity") == "1", "week column is hidden without SMIL"
        assert g.get("transform") is None, "week column is displaced without SMIL"
    cells = sum(1 for _ in root.iter(f"{NS}use"))
    assert 365 <= cells <= 372, f"expected a year of cells, got {cells}"

    # 2. the playback runs once and lands inside the card's own timeline
    begins = sorted(float(b) for b in re.findall(r'begin="([\d.]+)s"', src))
    assert begins[0] == 0.0 and begins[-1] <= 3.6, f"playback ends at {begins[-1]}s"
    assert 'repeatCount="indefinite"' not in src, "activity must not loop"

    # 3. the counters are the real cumulative curve, so the last step equals the aria-label total
    total = int(re.search(r"last 12 months: ([\d,]+) contributions", root.get("aria-label"))[1].replace(",", ""))
    assert int(odo[0][-1].text.replace(",", "")) == total, "counter final value disagrees with the stated total"

    print(f"ok — {cells} cells in {len(cols)} columns, {total:,} contributions, "
          f"playback {begins[0]}s–{begins[-1]}s, static base intact")


if __name__ == "__main__":
    sys.exit(main())
