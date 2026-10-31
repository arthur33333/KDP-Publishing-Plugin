# KDP paperback trim sizes, paper and page limits

**Trim list verified 2026-08-12. Paper calipers and page limits re-verified
2026-10-31** against KDP's official paperback submission guidelines:
<https://kdp.amazon.com/en_US/help/topic/G201857950>.

KDP changes these without notice and without a changelog. Re-check before any
upload that matters, and move the date above when you do.

The machine-readable copy is `scripts/kdp_geometry.py`:
`KDP_STANDARD_TRIMS`, `PAPER_CALIPER`, `STANDARD_PAGE_LIMITS` and
`PAGE_LIMIT_OVERRIDES`.

## Standard trim sizes

Standard sizes are available in every marketplace, are what the print-cost tables
are quoted against, and are the only ones some expanded-distribution channels
accept. **Prefer one.**

| Key | Inches | Metric (KDP's rounding) | For |
|---|---|---|---|
| `5x8` | 5 × 8 | 12.7 × 20.32 cm | Novellas, poetry, pocket non-fiction |
| `5.06x7.81` | 5.06 × 7.81 | 12.85 × 19.84 cm | Mass-market feel |
| `5.25x8` | 5.25 × 8 | 13.34 × 20.32 cm | Slightly roomier than 5×8 |
| `5.5x8.5` | 5.5 × 8.5 | 13.97 × 21.59 cm | Novels, memoir |
| **`6x9`** | 6 × 9 | 15.24 × 22.86 cm | **Default.** Non-fiction, reference, technical |
| `6.14x9.21` | 6.14 × 9.21 | 15.6 × 23.39 cm | Royal. Academic, reference |
| `6.69x9.61` | 6.69 × 9.61 | 16.99 × 24.41 cm | Larger reference |
| `7x10` | 7 × 10 | 17.78 × 25.4 cm | Workbooks, manuals, figures |
| `7.44x9.69` | 7.44 × 9.69 | 18.9 × 24.61 cm | Crown Quarto. Technical |
| `7.5x9.25` | 7.5 × 9.25 | 19.05 × 23.5 cm | Technical, illustrated |
| `8x10` | 8 × 10 | 20.32 × 25.4 cm | Illustrated, photo-led |
| `8.5x11` | 8.5 × 11 | 21.59 × 27.94 cm | US Letter. Workbooks, textbooks, code |

**Large trim.** Anything wider than 6.12in or taller than 9in is priced as large
trim and costs more per copy.

**Non-standard sizes.** KDP accepts trims from 4 × 6in up to 8.5 × 11.69in.
`kdp_geometry.py` computes dimensions for literal sizes. If a non-standard trim
has no explicit page-limit row in the current code, the plugin warns and asks
you to verify that limit in KDP rather than inventing one.

## Paper and spine caliper

Spine width is page count × the caliper below.

| Paper | Caliper (in/page) | Notes |
|---|---:|---|
| White B&W | 0.002252 | Black ink on white paper |
| Cream B&W | 0.0025 | Black ink on cream paper |
| Groundwood B&W | 0.00235 | Availability depends on marketplace |
| Standard colour | 0.002347 | Colour paper |
| Premium colour | 0.002347 | Colour paper |

**Important correction:** KDP specifies the same 0.002347in/page caliper for
standard and premium colour. The code now uses that figure for both. Groundwood
is included as a separate paper option at 0.00235in/page.

## Paperback page-count limits (US KDP table)

For the standard trim sizes from 5×8 through 8×10:

| Paper | Minimum | Maximum |
|---|---:|---:|
| Black ink, white paper | 24 | 828 |
| Black ink, cream paper | 24 | 776 |
| Black ink, groundwood paper | 24 | 812 |
| Standard colour ink, white paper | 72 | 600 |
| Premium colour ink, white paper | 24 | 828 |

KDP publishes lower ceilings for some larger and square trim sizes:

| Trim | White B&W | Cream B&W | Groundwood B&W | Standard colour | Premium colour |
|---|---:|---:|---:|---:|---:|
| 8.25 × 6in | 800 | 750 | 784 | 600 | 800 |
| 8.25 × 8.25in | 800 | 750 | 784 | 600 | 800 |
| 8.27 × 11.69in (A4) | 780 | 730 | 764 | Not available | 590 |
| 8.5 × 8.5in | 590 | 550 | 578 | 600 | 590 |
| 8.5 × 11in | 590 | 550 | 578 | 600 | 590 |

All minimums are 24 pages except standard colour, which starts at 72 pages.
The code blocks the known unavailable A4 standard-colour combination. It does
not pretend that an unlisted custom trim has a verified maximum.

## Parity and spine text

- The final interior page count must be even. The build script measures the PDF
  and adds a blank leaf when needed.
- KDP prints spine text only above 79 pages. A shorter book is still valid; its
  cover must simply omit spine text.

