---
name: kdp-print-geometry
description: Choose a KDP trim size, paper and margins, and compute spine width and full-wrap cover dimensions. Use when starting a book project, when deciding between trim sizes, when a page count changes and the cover has to follow, or whenever a spine, gutter, bleed or wrap dimension is being calculated or quoted. Biased toward KDP's US standard trim sizes.
---

# KDP print geometry

Every number here comes from `scripts/kdp_geometry.py`. Do not compute a spine
width, a wrap dimension or a gutter minimum in your head or in a one-off snippet —
call the module. A caliper written down in two places is a caliper that will
eventually disagree with itself.

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/kdp_geometry.py --list-trims
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/kdp_geometry.py --pages 398 --trim 6x9
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/kdp_geometry.py --pages 398 --json
```

## Prefer a standard trim

KDP splits paperback trims into **standard** and **non-standard**. Standard sizes
are available in every marketplace, are the only ones some distribution channels
accept, and are what the print-cost tables are quoted against. Non-standard sizes
print, but expanded distribution may refuse them and the economics are worse.

So: recommend a standard size, and treat a non-standard one as a decision that
has to be made deliberately rather than by typing a number slightly wrong. The
module returns `standard: null` for a non-standard trim and every caller surfaces
it — that is the warning working as intended, not a bug to route around.

The defaults worth reaching for first:

| Book | Trim |
|---|---|
| Non-fiction, guides, reference, technical | **6x9** |
| Novels, memoir | 5.5x8.5 |
| Novellas, poetry | 5x8 |
| Workbooks, manuals, anything with figures | 7x10 |
| Wide tables, code listings, textbooks | 8.5x11 |

Trims above 6.12in wide or 9in tall are "large trim" and cost more to print. Say
so when recommending one.

## Spine width

Page count times per-page caliper. No minimum, no rounding.

| Paper | Caliper (in/page) |
|---|---|
| White B&W | 0.002252 |
| Cream B&W | 0.0025 |
| Groundwood B&W | 0.00235 |
| Standard colour | 0.002347 |
| Premium colour | 0.002347 |

Standard and premium colour use the same KDP caliper. Page-count limits also vary
by paper and trim; use the geometry module instead of assuming the B&W ceiling.

The paper chosen in the KDP form must match the paper the cover was built for, or
the spine KDP computes stops matching the spine that was printed.

KDP prints **no spine text at 79 pages or under**. Above that, keep type inside
the band left after 0.0625in of clearance on each side — the press trims with
variance toward either face, so type filling the full spine width runs onto a
cover.

## Full wrap

```
wrap width  = bleed + trim_w + spine + trim_w + bleed
wrap height = bleed + trim_h + bleed
```

Bleed is 0.125in, on all four outside edges of the wrap. The cover is **one page**
carrying back, spine and front — not three pages, not three files. Back cover on
the left, front on the right.

KDP's minimum safe zone is 0.25in from the trim line. The bundled template uses
0.375in because type sitting exactly on the compliance figure reads on a proof as
though it is about to fall off the page.

## Margins and the gutter

The inside margin (gutter) minimum is **tiered by page count** — this is the one
people get wrong, because it means a book that grows past a tier boundary needs
its margins changed:

| Pages | Minimum gutter |
|---|---|
| up to 150 | 0.375in |
| 151–300 | 0.500in |
| 301–500 | 0.625in |
| 501–700 | 0.750in |
| 701–828 | 0.875in |

Outside margins: 0.25in minimum without bleed, 0.375in with. These are rejection
thresholds, not designs — `recommended_margins()` adds a buffer over the floor,
because a book set exactly at the minimum is accepted by KDP and still reads badly.

`build-interior.py` derives margins from the **measured** extent and repeats until
the gutter tier used for typesetting matches the actual page count.

## Bleed

Bleed is for interiors where art runs to the page edge. With bleed the interior
FILE is larger than the trim — 0.125in added to the top, bottom and outer edge,
**never** the gutter edge, which is bound rather than trimmed.

If nothing in the interior touches the edge, supply the file at trim size and
select "No bleed". Choosing bleed for a text-only book tells KDP to trim 0.125in
off content that is not there.

## Verify before quoting

`reference/` carries the source and the verification date for each table. KDP
changes these figures without notice and without a changelog. If a number is
about to go into a real upload and the date is old, say the date rather than
presenting the figure as current.
