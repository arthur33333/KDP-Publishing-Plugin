# KDP paperback cover specification

**Verified 2026-08-12** against
<https://kdp.amazon.com/en_US/help/topic/G201953020> and
<https://kdp.amazon.com/en_US/help/topic/G201857950>.

Machine-readable copy: `cover_dimensions()` in `scripts/kdp_geometry.py`.

## The file

- **One PDF, one page**, carrying back cover, spine and front cover as a single
  image. Not three files, not three pages.
- Sized **with bleed**, no surrounding white space, **no crop marks**.
- Fonts embedded. Typst does this by default on PDF export.
- **CMYK.** KDP asks for CMYK and strips embedded colour profiles. Convert a copy
  at upload; keep the source RGB.
- Raster art at **300 dpi at final size**.

## Dimensions

```
spine       = page_count × paper_caliper
wrap width  = 0.125 + trim_w + spine + trim_w + 0.125
wrap height = 0.125 + trim_h + 0.125
```

Bleed is 0.125in on all four outside edges of the wrap.

Layout order, flat: **back cover on the left, spine, front cover on the right.**

Fold lines from the wrap's left edge:

```
fold 1 = 0.125 + trim_w              back cover → spine
fold 2 = fold 1 + spine              spine → front cover
```

Worked example, 6 × 9in at 398 pages on cream B&W:

| | |
|---|---|
| Spine | 0.9950in (25.27 mm) |
| Full wrap | 13.2450 × 9.2500in |
| At 300 dpi | 3974 × 2775 px |
| Folds | 6.1250in and 7.1200in from the left edge |
| Spine text band | 0.8700in usable after clearance |

## Safe zones

- **0.25in** minimum from the trim line for anything not intended to be trimmed
  off. KDP's stated figure.
- The bundled template uses **0.375in**, because type sitting exactly on the
  compliance figure reads on a printed proof as though it is about to fall off
  the page.

## Spine text

- **Only above 79 pages.** KDP prints no spine text at or below that.
- At least **0.0625in** clearance between type and each spine edge. The press
  trims with variance toward either face, so type filling the full spine width
  runs onto a cover.
- Usable band = `spine − 2 × 0.0625in`. Under about 0.14in, drop spine text
  entirely rather than setting it very small.

## The barcode

KDP places the retailer barcode on the **back cover, bottom right** — roughly
2 × 1.2in. Other print channels use the opposite corner.

**Keep type out of both bottom corners of the back panel** so the same wrap works
whichever channel it goes to. Put back-cover furniture at the head of the panel
instead.

## What fails silently

A cover built against a stale page count. The spine is wrong, everything shifts
toward one face, and nothing on screen reports it — not a PDF viewer, not KDP's
uploader. This plugin checks it twice from opposite directions
(`build-cover.py` measures the interior; `kdp-package.py` measures the finished
wrap) because one check is not enough for a failure this expensive.
