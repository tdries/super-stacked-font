from fontTools.ttLib import TTFont
from superstack.composer import compose_pair, vmetrics, BASE_FONT_PATH


def test_top_sits_above_bottom_with_gap():
    font = TTFont(BASE_FONT_PATH)
    upm = font["head"].unitsPerEm
    gs = font.getGlyphSet()
    cmap = font.getBestCmap()
    cmds, _ = compose_pair(gs, "A", "X", upm, cmap, vmetrics(font))
    ys = sorted({round(pt[1]) for op, args in cmds
                 for pt in (args or []) if isinstance(pt, tuple)})
    mid = upm * 0.5
    above = [y for y in ys if y > mid]
    below = [y for y in ys if y < mid]
    assert above and below                # both halves populated
    assert min(above) >= mid              # nothing from top crosses below mid
    assert max(below) <= mid              # nothing from bottom crosses above mid
