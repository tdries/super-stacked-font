"""Weld two base-font glyphs into one stacked glyph (top over bottom)."""
import os
from fontTools.pens.recordingPen import RecordingPen, DecomposingRecordingPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.boundsPen import ControlBoundsPen

# Supported characters: uppercase, lowercase, digits, space, and common
# punctuation. Each must map to a glyph-name-safe token (CHAR_NAMES) because
# OpenType glyph names can't contain most symbols and are case-insensitive on
# some platforms (so lowercase gets a `.lc` suffix to avoid colliding with caps).
_UPPER = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
_LOWER = "abcdefghijklmnopqrstuvwxyz"
_DIGITS = "0123456789"
_PUNCT = ".,:-%$/!?'#&+()"

# Browsers refuse to form OpenType ligatures that involve the U+0020 space glyph
# (whitespace gets special shaping treatment), so any pair containing a space
# silently fails to stack. We use a Private-Use blank character (U+E000) as the
# in-pair "space": it renders empty but, being a normal ink character to the
# shaper, ligates fine. Callers translate real spaces to BLANK before pairing.
BLANK = ""

_UNITS = _UPPER + _LOWER + _DIGITS + _PUNCT + BLANK
TIER1 = list(_UNITS)

_DIGIT_NAMES = {"0": "zero", "1": "one", "2": "two", "3": "three", "4": "four",
                "5": "five", "6": "six", "7": "seven", "8": "eight", "9": "nine"}
_PUNCT_NAMES = {".": "period", ",": "comma", ":": "colon", "-": "hyphen",
                "%": "percent", "$": "dollar", "/": "slash", "!": "exclam",
                "?": "question", "'": "quotesingle", "#": "numbersign",
                "&": "ampersand", "+": "plus", "(": "parenleft", ")": "parenright"}
CHAR_NAMES = {c: c for c in _UPPER}
CHAR_NAMES.update({c: c + ".lc" for c in _LOWER})
CHAR_NAMES.update(_DIGIT_NAMES)
CHAR_NAMES.update(_PUNCT_NAMES)
CHAR_NAMES[BLANK] = "blank"

# Dot-free tokens for building composed-pair glyph names (dots are reserved in
# glyph names). Lowercase 'a' -> 'alc', everything else reuses its CHAR_NAME.
_PAIR_TOKEN = {c: (CHAR_NAMES[c].replace(".lc", "lc")) for c in TIER1}

# Default base font (overridable per build). Prefer the bundled libre Inter so
# generated OTFs are freely distributable; fall back to a system font otherwise.
_HERE = os.path.dirname(__file__)
_BUNDLED = os.path.normpath(os.path.join(_HERE, "..", "..", "assets", "base-fonts",
                                         "Inter-Regular.ttf"))
_CANDIDATES = [
    _BUNDLED,
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/System/Library/Fonts/Monaco.ttf",
]
BASE_FONT_PATH = next((p for p in _CANDIDATES if os.path.exists(p)), _CANDIDATES[-1])

GAP = 0.06   # hairline gap as a fraction of the em between the two rows


def glyph_name(top: str, bottom: str) -> str:
    return f"{_PAIR_TOKEN[top]}_over_{_PAIR_TOKEN[bottom]}"


def _record(glyphset, gname):
    # Decompose component references (composite glyphs) into plain contours so
    # the commands replay against a None-glyphset later (bounds, charstring).
    pen = DecomposingRecordingPen(glyphset)
    if gname is not None and gname in glyphset:
        glyphset[gname].draw(pen)
    return pen.value  # list of (op, args), components flattened


SIDE = 0.012  # side bearing each side, as a fraction of the em (tight)
XSCALE = 0.78  # default horizontal condense (the regular width; build passes per-family)


def vmetrics(font):
    """(ascender, descender) defining the design box to fit into each half-row.

    Uses typo metrics so ascenders and descenders (lowercase g, p, y) are fully
    contained: without this, descenders would clip below the em in the bottom row.
    """
    os2 = font["OS/2"]
    return os2.sTypoAscender, os2.sTypoDescender


def _squash_into(commands, upm, top_half, tx, asc, desc, xscale):
    """Scale recorded glyph commands into the upper or lower half of the em.

    The font's full design box (descender..ascender) is scaled to fit one
    half-row (preserving the baseline so every letter aligns), and x is scaled by
    the same y-factor times xscale to condense. Descenders stay inside the row.
    """
    gap = upm * GAP / 2
    half = upm * 0.5 - gap                 # height available per row
    box = asc - desc                       # full design height (asc positive, desc negative)
    sy = half / box
    sx = sy * xscale
    # baseline y within the row: lift glyph so its descender sits at the row floor
    floor = (upm * 0.5 + gap) if top_half else 0.0
    ty = floor - desc * sy                 # maps design-y=desc to the row floor
    out_pen = RecordingPen()
    tpen = TransformPen(out_pen, (sx, 0, 0, sy, tx, ty))
    replay = RecordingPen()
    replay.value = commands
    replay.replay(tpen)
    return out_pen.value


def _ink_x(commands):
    """(xmin, xmax) of the actual outline ink, ignoring built-in side bearings.
    Returns (0, 0) for an empty glyph like space."""
    pen = ControlBoundsPen(None)
    replay = RecordingPen()
    replay.value = commands
    replay.replay(pen)
    if pen.bounds is None:
        return 0.0, 0.0
    xmin, _, xmax, _ = pen.bounds
    return xmin, xmax


def compose_pair(glyphset, top: str, bottom: str, upm: int, cmap, vmetrics,
                 xscale=XSCALE):
    """Return (recorded_drawing_commands, advance_width) for the stacked pair.

    Letters are condensed (xscale) and squashed to fit one half-row using the
    font's design box (vmetrics = (ascender, descender)) so descenders stay
    inside the em. We measure each letter's actual ink width (not its advance,
    which bakes in side bearings), pack the cell to the wider inked letter, and
    align ink to a common left edge. Dense, even spacing, no clipping. A smaller
    xscale yields a Condensed width.
    """
    asc, desc = vmetrics
    # BLANK is our own Private-Use char; the base font may have an unrelated glyph
    # at that codepoint, so force it to draw nothing rather than the base's PUA art.
    top_cmds = [] if top == BLANK else _record(glyphset, cmap.get(ord(top)))
    bot_cmds = [] if bottom == BLANK else _record(glyphset, cmap.get(ord(bottom)))

    gap = upm * GAP / 2
    sy = (upm * 0.5 - gap) / (asc - desc)      # same factor used in _squash_into
    sx = sy * xscale
    side = upm * SIDE

    txmin, txmax = _ink_x(top_cmds)
    bxmin, bxmax = _ink_x(bot_cmds)
    w_top = (txmax - txmin) * sx
    w_bot = (bxmax - bxmin) * sx
    inner = max(w_top, w_bot)
    if inner < upm * 0.04:                      # a space (no ink): keep a word gap
        inner = upm * 0.22
    width = inner + 2 * side
    # move each letter's ink to x=side, then center the narrower one in `inner`
    tx_top = side - txmin * sx + (inner - w_top) / 2
    tx_bot = side - bxmin * sx + (inner - w_bot) / 2

    cmds = _squash_into(top_cmds, upm, True, tx_top, asc, desc, xscale) + \
        _squash_into(bot_cmds, upm, False, tx_bot, asc, desc, xscale)
    return cmds, int(round(width))
