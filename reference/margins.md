# KDP interior margins and bleed

**Verified 2026-08-12** against
<https://kdp.amazon.com/en_US/help/topic/GVBQ3CMEQW3W2VL6> and
<https://kdp.amazon.com/en_US/help/topic/G201834260>.

KDP changes these without notice. Re-check before upload; move the date when you
do. Machine-readable copy: `GUTTER_TIERS` in `scripts/kdp_geometry.py`.

## The gutter is tiered by page count

This is the figure people get wrong, because it means a book that grows past a
boundary needs its margins changed rather than kept.

| Page count | Minimum inside margin (gutter) |
|---|---|
| 24–150 | 0.375in |
| 151–300 | 0.500in |
| 301–500 | 0.625in |
| 501–700 | 0.750in |
| 701–828 | 0.875in |

`build-interior.py` derives margins from the **measured** first-pass extent for
exactly this reason, and recompiles if the extent lands in a different tier than
the seed.

Getting it wrong swallows text into the spine on every page of the book. It is
invisible in a PDF viewer, because the viewer does not bind anything. KDP's own
previewer is the only thing that shows it.

## Outside margins

| | Minimum |
|---|---|
| Top, bottom, outer — no bleed | 0.25in |
| Top, bottom, outer — with bleed | 0.375in |

These are **rejection thresholds, not designs**. A book set exactly at 0.375in
inside margin is accepted by KDP and still reads badly, because the minimum
assumes the reader will crack the spine flat.

`recommended_margins()` adds 0.25in over the gutter floor and scales the outside
margins with the trim, so an 8.5 × 11 workbook does not get a 6 × 9 book's
measure stretched across it.

## Bleed

Bleed is for interiors where art runs to the page edge.

- **No bleed** — supply the interior at exactly the trim size.
- **Bleed** — supply it larger: **0.125in added to the top, bottom and outer
  edge**. Never the gutter edge; that edge is bound, not trimmed.

So a 6 × 9 interior with bleed is a 6.125 × 9.25in file.

**If even one page needs bleed, the whole file is set up with bleed.** You cannot
mix.

**Do not select bleed for a text-only book.** It tells KDP to trim 0.125in off
content that is not there.

## Rough page-count estimation

Only for choosing a trim before anything is typeset. Take the real number from a
build, never from this table.

| Trim | Words per page |
|---|---|
| 5 × 8 | ~200–220 |
| 6 × 9 | ~250–280 |
| 8.5 × 11 | ~400–450 |

A model can be badly off. On one real book here the character-count model
projected 472 pages and the actual typeset extent came in at 398 — 16% under, in
a build that included a section the model excluded. Estimates are for choosing a
trim; measurements are for building a cover.
