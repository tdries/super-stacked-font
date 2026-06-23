"""Build Super Stacked OTFs: stacked-pair fonts with ligature substitution.

Input sequence ``<top> | <bottom>`` substitutes (via the ``liga`` feature) to a
single welded glyph drawn by the composer (top char in the upper half, bottom
char in the lower half of the em).

One family is built per (base font, width). ``build_all()`` builds the full
matrix defined in FAMILIES.
"""
import os
import json
from fontTools.ttLib import TTFont
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.pens.recordingPen import RecordingPen
from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
from .composer import (TIER1, CHAR_NAMES, glyph_name, compose_pair,
                       BASE_FONT_PATH, vmetrics, _record, BLANK)

from . import __version__ as VERSION

SEP = "|"
PUA_BASE = 0xE100   # direct-codepoint range for stacked pairs (after BLANK at E000)

# Metadata embedded in every OTF's name table. The fonts compose their outlines
# from OFL-licensed bases (Inter, Archivo), so the generated fonts are OFL too.
COPYRIGHT = "Copyright (c) 2026 Tim Dries. Composed from Inter and Archivo (SIL OFL 1.1)."
LICENSE_DESC = ("This font is licensed under the SIL Open Font License, Version 1.1. "
                "It is composed from Inter and Archivo, both under the same license. "
                "See OFL.txt.")
LICENSE_URL = "https://openfontlicense.org"

# Fixed build timestamp for reproducible output. OpenType `head` stores seconds
# since 1904-01-01; this is 2026-06-01 00:00 UTC. CI/packagers can override the
# wall-clock source via SOURCE_DATE_EPOCH (Unix epoch), converted to Mac epoch.
_MAC_EPOCH_OFFSET = 2082844800   # seconds between 1904-01-01 and 1970-01-01
_sde = os.environ.get("SOURCE_DATE_EPOCH")
BUILD_EPOCH = (int(_sde) + _MAC_EPOCH_OFFSET) if _sde else 3865104000

_HERE = os.path.dirname(__file__)
_BASES = os.path.normpath(os.path.join(_HERE, "..", "..", "assets", "base-fonts"))

# The build matrix: each entry is one OTF. xscale tunes horizontal density.
FAMILIES = [
    {"family": "Super Stacked Sans",            "base": "Inter-Regular.ttf",   "xscale": 0.78, "file": "SuperStackedSans.otf"},
    {"family": "Super Stacked Sans Condensed",  "base": "Inter-Regular.ttf",   "xscale": 0.55, "file": "SuperStackedSans-Condensed.otf"},
    {"family": "Super Stacked Grotesk",         "base": "Archivo-Regular.ttf", "xscale": 0.78, "file": "SuperStackedGrotesk.otf"},
    {"family": "Super Stacked Grotesk Condensed", "base": "Archivo-Regular.ttf", "xscale": 0.55, "file": "SuperStackedGrotesk-Condensed.otf"},
]


def _charstring(cmds, width):
    pen = T2CharStringPen(width, None)
    rp = RecordingPen()
    rp.value = cmds
    rp.replay(pen)
    return pen.getCharString()


def build(base_path: str = BASE_FONT_PATH, out_path: str = "out/SuperStackedSans.otf",
          family: str = "Super Stacked Sans", xscale: float = 0.78,
          write_data: bool = True) -> str:
    """Build a single Super Stacked OTF from one base font at one width."""
    out_dir = os.path.dirname(out_path) or "."
    os.makedirs(out_dir, exist_ok=True)

    base = TTFont(base_path, fontNumber=0)
    upm = base["head"].unitsPerEm
    gs = base.getGlyphSet()
    cmap = base.getBestCmap()
    vm = vmetrics(base)

    glyph_order = [".notdef"]
    charstrings = {".notdef": _charstring([], upm)}
    advances = {".notdef": upm}
    pairs = []

    # 1) stacked-pair glyphs. Each also gets a direct Private-Use codepoint
    # (PUA_BASE + index) so the web playground can address a stacked glyph with a
    # single character, bypassing browser ligature shaping (which refuses pairs
    # containing spaces). The pipe-ligature path still works for design apps.
    for top in TIER1:
        for bot in TIER1:
            gname = glyph_name(top, bot)
            cmds, width = compose_pair(gs, top, bot, upm, cmap, vm, xscale)
            charstrings[gname] = _charstring(cmds, width)
            advances[gname] = width
            cp = PUA_BASE + len(pairs)
            glyph_order.append(gname)
            pairs.append((gname, cp))

    # 2) single base glyphs for each char (ligature input requires them)
    for c in TIER1:
        gname = CHAR_NAMES[c]
        # BLANK draws nothing (don't pick up the base font's PUA glyph at E000)
        cmds = [] if c == BLANK else _record(gs, cmap.get(ord(c)))
        charstrings[gname] = _charstring(cmds, upm)
        advances[gname] = upm
        glyph_order.append(gname)

    # 3) separator glyph (pipe): blank, zero advance
    charstrings["bar"] = _charstring([], 0)
    advances["bar"] = 0
    glyph_order.append("bar")

    ps_name = family.replace(" ", "")
    fb = FontBuilder(upm, isTTF=False)
    fb.setupGlyphOrder(glyph_order)
    cmap_table = {ord(c): CHAR_NAMES[c] for c in TIER1}
    cmap_table[ord(SEP)] = "bar"
    cmap_table[ord(" ")] = "blank"   # a stray literal space renders as the blank glyph
    for gname, cp in pairs:                     # direct PUA codepoint per pair
        cmap_table[cp] = gname
    fb.setupCharacterMap(cmap_table)
    fb.setupCFF(ps_name, {"FullName": family}, charstrings, {})

    metrics = {g: (advances[g], 0) for g in glyph_order if g != ".notdef"}
    metrics[".notdef"] = (upm, 0)
    fb.setupHorizontalMetrics(metrics)
    fb.setupHorizontalHeader(ascent=upm, descent=0)
    # Full name table so the license and metadata travel inside the font file,
    # not just in a sibling text file (Font Bakery / OS font managers read these).
    fb.setupNameTable({
        "familyName": family,
        "styleName": "Regular",
        "uniqueFontIdentifier": f"SuperStacked;{VERSION};{ps_name}",
        "fullName": family,
        "psName": ps_name,
        "version": f"Version {VERSION}",
        "copyright": COPYRIGHT,
        "licenseDescription": LICENSE_DESC,
        "licenseInfoURL": LICENSE_URL,
    })
    fb.setupOS2()
    fb.setupPost()

    # ligatures: "<top> bar <bottom>" -> stacked glyph
    lines = ["feature liga {"]
    for top in TIER1:
        for bot in TIER1:
            lines.append(
                f"  sub {CHAR_NAMES[top]} bar {CHAR_NAMES[bot]} by {glyph_name(top, bot)};")
    lines.append("} liga;")
    addOpenTypeFeaturesFromString(fb.font, "\n".join(lines))

    # Pin the head timestamps so the build is byte-reproducible (fontTools
    # otherwise stamps "now", which breaks a clone-and-compare). BUILD_EPOCH is
    # seconds since the 1904 Mac epoch; override with SOURCE_DATE_EPOCH if set.
    fb.font["head"].created = fb.font["head"].modified = BUILD_EPOCH

    fb.save(out_path)
    if write_data:
        # Compact descriptor for the web playground: a pair's codepoint is
        # PUA_BASE + units.index(top)*len(units) + units.index(bottom).
        # Spaces in user input map to BLANK before lookup.
        json.dump({
            "separator": SEP,
            "units": "".join(TIER1),          # ordered charset (BLANK is last char)
            "blank": ord(BLANK),
            "puaBase": PUA_BASE,
            "families": [{"name": f["family"], "file": f["file"]} for f in FAMILIES],
        }, open(os.path.join(out_dir, "font_data.json"), "w"), ensure_ascii=True)
    return out_path


def build_all(out_dir: str = "out") -> list:
    """Build every family in the matrix. Returns the list of output paths."""
    paths = []
    for i, spec in enumerate(FAMILIES):
        base_path = os.path.join(_BASES, spec["base"])
        out_path = os.path.join(out_dir, spec["file"])
        build(base_path=base_path, out_path=out_path, family=spec["family"],
              xscale=spec["xscale"], write_data=(i == 0))
        paths.append(out_path)
    return paths


def main():
    for p in build_all():
        print(f"wrote {p}")


if __name__ == "__main__":
    main()
