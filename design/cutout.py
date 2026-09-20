"""Cut the white background out of the certification badges in design/badges/ so they sit on any README theme.

Neutral ink (greys, black) is recoloured per theme; coloured pixels keep their colour. Output: assets/certs/<name>-{light,dark}.png
Run: uv run --with pillow --with numpy --with scipy design/cutout.py
"""
import pathlib

import numpy as np
from scipy import ndimage
from PIL import Image

SRC, OUT = pathlib.Path(__file__).parent / "badges", pathlib.Path(__file__).parent.parent / "assets" / "certs"
INK = {"light": (31, 42, 36), "dark": (231, 236, 230)}
H = 168  # output height in px (shown at ~84 CSS px)


def cut(path, theme):
    src = Image.open(path).convert("RGBA")
    im = Image.alpha_composite(Image.new("RGBA", src.size, "white"), src).convert("RGB")  # transparent corners -> white
    im = im.resize((round(im.width * H / im.height), H), Image.LANCZOS)
    p = np.asarray(im, dtype=float)
    mn, mx = p.min(2), p.max(2)
    a = np.clip((255 - mn) / 60, 0, 1)  # white -> transparent, anything clearly coloured -> opaque
    lum = p @ [0.299, 0.587, 0.114]
    neutral = (mx - mn) < 40
    a = np.where(neutral, np.clip((255 - lum) / 200, 0, 1), a)
    if (~neutral & (a > 0.9)).mean() > 0.3:  # a coloured badge: only the outer white goes, inner white text stays white
        lab, _ = ndimage.label(mn >= 235)
        edge = np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
        inner = (mn >= 235) & ~np.isin(lab, edge[edge > 0])
        a = np.where(ndimage.binary_dilation(np.isin(lab, edge[edge > 0]), iterations=3), a, 1.0)  # only the outside fades
        neutral = neutral & ~ndimage.binary_dilation(inner, iterations=2)  # keep the white text white, edges included
    safe = np.maximum(a, 1e-3)[..., None]
    rgb = np.clip((p - (1 - a[..., None]) * 255) / safe, 0, 255)  # undo the white blend on edge pixels
    rgb = np.where(neutral[..., None], np.array(INK[theme], float), rgb)
    return Image.fromarray(np.dstack([rgb, a * 255]).astype("uint8"), "RGBA")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for f in sorted(SRC.glob("*.png")):
        for theme in INK:
            cut(f, theme).save(OUT / f"{f.stem}-{theme}.png", optimize=True)
    print(len(list(OUT.glob("*.png"))), "files")
