---
description: Build the full-wrap cover — back, spine and front on one sheet — at the interior's actual measured extent
argument-hint: "[optional — 'what-if N' to model a different page count]"
---

Build the cover. Scope: $ARGUMENTS

Use the `kdp-cover-wrap` skill. In short:

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/build-cover.py
```

**The cover is built LAST, and from the interior.** Spine width is page count
times paper caliper, so a cover built before the interior was finished — or kept
from a previous edition — has a spine that does not match the book. The spine
type sits off-centre, or the title wraps onto the front face. A PDF viewer will
not catch it. KDP's uploader will not catch it. The proof copy catches it, three
weeks and one print charge later.

So the script does not accept a page count. It runs `pdfinfo` over the interior
that was actually built. If the user asks what a different extent would cost:

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/build-cover.py --pages 420
```

which models it and refuses to write the file.

**Before editing `templates/cover.typ`, read the three rules at the top of it.**
They are not style preferences — each one is a proof copy someone lost:

1. Nothing on the front panel is anchored up from the bottom edge. The panel is
   one fixed-height box with `v(1fr)` spacers, so a longer subtitle squeezes the
   gaps instead of overprinting the byline.
2. Neither bottom corner of the back panel carries type. KDP puts the retailer
   barcode in one and other channels use the other.
3. A literal `/*` opens a block comment and eats the rest of the file.

**If the user wants AI-generated cover art**, that is supported but not
automated: generate or source the image separately, drop it in `assets/art/`, and
place it in the front panel of `cover.typ` with `image()`. Keep the wrap itself
typeset — the folds, the spine and the safe zones are geometry, not artwork, and
an image stretched across the whole wrap loses them.

Do not let the template override `page(width:)`. The script measures the rendered
wrap afterwards and fails the build if the folds moved.

After it builds, run `/kdp-package`, which independently re-derives the spine from
the finished wrap as a second check.
