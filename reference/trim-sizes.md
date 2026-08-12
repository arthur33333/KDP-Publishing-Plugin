# KDP paperback trim sizes and paper

**Verified 2026-08-12** against KDP's paperback print options form and
<https://kdp.amazon.com/en_US/help/topic/GVBQ3CMEQW3W2VL6>.

KDP changes these without notice and without a changelog. Re-check before any
upload that matters, and move the date above when you do.

The machine-readable copy is `scripts/kdp_geometry.py` — `KDP_STANDARD_TRIMS`
and `PAPER_CALIPER`. This file is the provenance; that file is the source of
truth for anything computed.

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
trim and costs more per copy. That covers `6.69x9.61` and everything below it in
the table.

**Non-standard sizes.** KDP accepts trims from 4 × 6in up to 8.5 × 11.69in.
`kdp_geometry.py` computes them correctly and `is_standard()` returns `None`, so
every caller warns. It is a legitimate choice, not an error — but it should be a
choice.

## Paper and caliper

Spine width is page count × caliper. No minimum, no rounding rule.

| Paper | Caliper (in/page) | Notes |
|---|---|---|
| White B&W | 0.002252 | Cheapest. Higher contrast; can glare over long text |
| Cream B&W | 0.0025 | Easier on the eye over hundreds of pages. Standard for prose |
| Standard colour | 0.002252 | Much more expensive per page |
| Premium colour | 0.002347 | Photo-grade, most expensive |

**The paper selected in the KDP form must match the paper the cover was built
for.** Cream and white differ by 0.000248in per page — 0.10in of spine across a
400-page book, which is enough to move the spine type onto a face.

## Page count limits

| | |
|---|---|
| Minimum | 24 pages |
| Maximum, B&W | 828 pages |
| Maximum, colour | Lower; check the current figure — it varies by trim and ink |
| Parity | Must be even |
| Spine text | Only above 79 pages |

`kdp_geometry.py` carries the B&W limit. A colour book near the ceiling needs the
current figure checked directly.
