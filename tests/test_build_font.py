import os
import json
from fontTools.ttLib import TTFont
from superstack.build_font import build, PUA_BASE
from superstack.composer import TIER1


def test_build_emits_font_and_data(tmp_path):
    out = build(out_path=str(tmp_path / "SuperStacked.otf"))
    assert os.path.exists(out)
    font = TTFont(out)
    names = set(font.getGlyphOrder())
    assert "A_over_B" in names
    assert "zero_over_one" in names
    stacked = [n for n in names if "_over_" in n]
    assert len(stacked) == len(TIER1) * len(TIER1)   # every ordered pair
    assert "GSUB" in font

    data = json.load(open(str(tmp_path / "font_data.json")))
    assert data["separator"] == "|"
    # font_data drives the web playground: charset, blank, and PUA base must
    # round-trip exactly or the browser addresses the wrong stacked glyphs.
    assert list(data["units"]) == TIER1
    assert data["puaBase"] == PUA_BASE
    assert len(data["families"]) == 4


def test_pua_codepoints_resolve_in_cmap(tmp_path):
    # the playground addresses a pair directly by PUA codepoint; verify the
    # font's cmap actually maps that codepoint to the right stacked glyph.
    out = build(out_path=str(tmp_path / "SuperStacked.otf"))
    font = TTFont(out)
    cmap = font.getBestCmap()
    N = len(TIER1)
    # pair (A, B): A is index 0, B is index 1
    cp = PUA_BASE + 0 * N + 1
    assert cmap[cp] == "A_over_B"
