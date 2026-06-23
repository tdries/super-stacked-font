from fontTools.ttLib import TTFont
from superstack.composer import glyph_name, TIER1, BLANK, compose_pair, vmetrics, BASE_FONT_PATH


def test_tier1_covers_alnum_punct_and_blank():
    # uppercase + lowercase + digits + punctuation + one BLANK (the in-pair space)
    assert len(TIER1) == 78
    assert set("ABCDEFGHIJKLMNOPQRSTUVWXYZ").issubset(TIER1)
    assert set("abcdefghijklmnopqrstuvwxyz").issubset(TIER1)
    assert set("0123456789").issubset(TIER1)
    assert BLANK in TIER1


def test_glyph_name_tokens():
    assert glyph_name("A", "B") == "A_over_B"
    assert glyph_name("0", "1") == "zero_over_one"
    assert glyph_name("a", "b") == "alc_over_blc"   # lowercase keeps its lc token
    assert glyph_name(BLANK, "A") == "blank_over_A"


def test_compose_pair_returns_commands_and_width():
    font = TTFont(BASE_FONT_PATH)
    gs = font.getGlyphSet()
    upm = font["head"].unitsPerEm
    cmds, width = compose_pair(gs, "A", "B", upm, font.getBestCmap(), vmetrics(font))
    assert isinstance(cmds, list) and len(cmds) > 0
    assert width > 0
    ys = [pt[1] for cmd in cmds for pt in (cmd[1] or []) if isinstance(pt, tuple)]
    assert max(ys) > upm * 0.5   # something in the upper half
    assert min(ys) < upm * 0.5   # something in the lower half
