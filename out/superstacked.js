// Super Stacked web encoder.
//
// Browsers refuse to form OpenType ligatures that involve a space glyph, so the
// "type TOP|BOTTOM" approach is unreliable on the web. Instead every stacked
// pair has its own Private-Use codepoint, and we address it directly: one
// codepoint per column, no ligatures, no separators. Works in every browser.
//
// Usage:
//   const ss = await SuperStacked.load("./font_data.json");
//   el.textContent = ss.encode("HELLO", "world");   // top, bottom
//   ss.families  // [{name, file}, ...]
const SuperStacked = (() => {
  function build(data) {
    const units = Array.from(data.units);          // ordered charset
    const N = units.length;
    const BLANK = String.fromCodePoint(data.blank);
    const PUA = data.puaBase;
    const idx = new Map(units.map((c, i) => [c, i]));

    // Map a user character to a supported unit: spaces -> BLANK, unknown -> BLANK.
    function unit(ch) {
      if (ch === " ") return BLANK;
      return idx.has(ch) ? ch : BLANK;
    }

    // encode(top, bottom) -> string of one PUA char per column.
    function encode(top, bottom) {
      top = top ?? "";
      bottom = bottom ?? "";
      const w = Math.max(top.length, bottom.length);
      let out = "";
      for (let k = 0; k < w; k++) {
        const t = idx.get(unit(top[k] ?? " "));
        const b = idx.get(unit(bottom[k] ?? " "));
        out += String.fromCodePoint(PUA + t * N + b);
      }
      return out;
    }

    return { encode, families: data.families, units: data.units };
  }

  async function load(url) {
    const res = await fetch(url);
    if (!res.ok) throw new Error("font_data.json not found at " + url);
    return build(await res.json());
  }

  return { load, build };
})();

if (typeof module !== "undefined") module.exports = SuperStacked;
