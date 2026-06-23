# Changelog

All notable changes to Super Stacked are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[semantic versioning](https://semver.org/).

## [Unreleased]

### Added
- Four font families: Super Stacked Sans and Grotesk, each in regular and condensed widths, built from OFL bases (Inter, Archivo).
- Full character set: uppercase, lowercase, digits, space, and common punctuation (`. , : - % $ / ! ? ' # & + ( )`).
- Interactive web playground (`out/index.html`): type two lines, switch family, resize, download a PNG, copy the stacked text.
- Static showcase page (`out/showcase.html`) demonstrating the font live in the browser, including all four families and a "mix with a normal font" section.
- Mixed-font example page (`out/mix-demo.html`): a stacked pair inline beside a normal typeface on one baseline.
- Complete OpenType name table embedded in every font: copyright, license (SIL OFL 1.1), license URL, version, and PostScript name.
- `OFL.txt` at the repo root covering the composed font and its base fonts.

### Changed
- Renamed the project from "Super Stack" to "Super Stacked".
- `font_data.json` is now ASCII-escaped so the in-pair BLANK (U+E000) survives copy/paste and embedding.

### Removed
- The `superstack` terminal CLI and its block-character micro-font. Super Stacked is now purely an OpenType font product (the font renders in browsers and design apps; terminals were a separate, lower-fidelity path that no longer fits the product).

### Fixed
- Unequal line lengths now pad the shorter side with the ligature-safe BLANK instead of a raw space, so a trailing character (e.g. the `R` in WATER over AGUA) stacks over an empty cell instead of rendering full-size.

## [0.1.0]

### Added
- Initial proof of concept: a single uppercase + digits font (`SuperStack.otf`) and a `superstack` CLI that stacks two lines with block characters for terminals.
