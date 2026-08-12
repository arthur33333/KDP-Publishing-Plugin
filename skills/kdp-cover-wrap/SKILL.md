---
name: kdp-cover-wrap
description: Build or edit a KDP full-wrap paperback cover in Typst — spine derived from the interior's measured extent, fold lines, safe zones, spine-text rules, and the layout traps that only show up in a printed proof. Use when building a cover, changing a cover design, diagnosing a spine that does not match the book, or preparing cover art for upload.
---

# The full-wrap cover

One page carrying back cover, spine and front cover, with bleed on all four
outside edges. That single sheet is what KDP wants uploaded.

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/build-cover.py
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/build-cover.py --pages 420   # what-if only
```

## The rule the whole design hangs off

**The cover is built last, and from the interior — never from a number.**

Spine width is page count times caliper. A cover built before the interior was
finished, or carried over from a previous edition, has a spine that does not match
the book. At best the spine type sits off-centre; at worst the title wraps onto
the front face.

Nothing catches this on screen. Not a PDF viewer, not KDP's uploader. The proof
copy catches it, three weeks and one print charge later.

So `build-cover.py` will not take a page count. It runs `pdfinfo` over the
interior that was actually built. `--pages` exists only to answer "what would a
different extent cost", and refuses to write the file.

That is one of **two independent checks**. `kdp-package.py` then measures the
finished wrap, subtracts both faces and both bleeds, and compares what is left
against the spine this page count needs — the same fact reached from the opposite
direction. A stale cover has to defeat both.

## Three layout rules that are not style preferences

Each of these is a proof copy someone lost. They are repeated at the top of
`templates/cover.typ`; read them before editing it.

**1. Nothing on the front panel is anchored up from the bottom edge.**

The whole panel is one fixed-height box with `v(1fr)` spacers in it, so leftover
space is distributed rather than assumed. Anchoring a block to the foot makes its
position a guess about how tall everything above it turned out — and that guess is
wrong the moment the title or subtitle wraps to another line.

With `1fr` the collision is not tuned away, it cannot happen: a longer subtitle
squeezes the gaps instead of overprinting the byline.

**2. Neither bottom corner of the back panel carries type.**

KDP places the retailer barcode in one corner and other print channels use the
other, so neither is safe whichever channel the wrap is built for. Put back-cover
furniture at the head of the panel instead.

**3. A literal `/*` opens a Typst block comment and eats the rest of the file.**

The document still compiles — just shorter. If a cover rebuild loses its back
half for no apparent reason, this is why. Write any URL containing one as a
string concatenation.

## Spine text

KDP prints no spine text at 79 pages or under; `build-cover.py` passes
`spine_text=false` and the template omits it. Above that, cap type to the band
left after 0.0625in clearance each side — the press trims with variance toward
either face.

## Cover art

The wrap itself stays typeset. Folds, spine and safe zones are geometry, and an
image stretched across the whole wrap loses them.

To use raster art — AI-generated or otherwise — place it inside the front panel:

```typst
#place(top + left, dx: front-x, dy: bleed)[
  #image("../assets/art/front.png", width: trim-w + bleed, height: wrap-h)
]
```

Supply it at **300 dpi at final size**. `kdp_geometry.py` prints the wrap and
front-panel pixel dimensions at 300 dpi for exactly this.

The plugin does not generate cover art and does not call an image API. Source or
generate the image however you like, drop it in `assets/art/`, and place it.

## Before upload

- **Convert to CMYK.** KDP asks for CMYK covers and strips embedded profiles.
  Convert a copy, never the source.
- Confirm the print options selected in the KDP form match the file — a different
  paper or trim there means a different spine.

## When the geometry is wrong

`build-cover.py` measures the rendered wrap and fails if it does not match the
geometry it asked for. That failure means the template is overriding
`page(width:)` itself. Fix the template rather than the check.
