---
name: kdp-preflight
description: Verify a built KDP book mechanically before upload — trim, page parity, gutter, raster image resolution, font round-trip, listing and cover spine. Use before any upload, after any rebuild, and when deciding whether a book is actually ready to print.
---

# Pre-flight

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/preflight.py
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/preflight.py --json
```

Exits non-zero on failure. Everything it checks is something a machine can check;
everything it cannot check, it names.

## The principle

**Check the artifact, not the signal that stands in for it.**

Every failure this script is built to catch produces a *successful-looking*
build. Typst exits 0. The PDF opens. KDP accepts the upload. The problem is
discovered in a proof copy, which is the most expensive possible place to
discover it.

So: read the page geometry out of the PDF rather than trusting `book.toml`. Read
the page count out of the PDF rather than trusting the last build. Derive the
cover's spine from the finished wrap rather than recomputing what it should have
been. A number that agrees with itself because it came from one place twice has
not been verified.

## What each check is protecting against

**Trim.** KDP will accept a file at the wrong trim and print the book with the
wrong margins. Nobody sees it until the proof arrives.

**Page parity.** An odd leaf count means the build is stale — the parity pass did
not run or its output was overwritten.

**Gutter against the tiered minimum.** KDP's minimum inside margin steps up with
page count. A book that grew past a boundary since its margins were set has text
being swallowed into the bind on every page, and it looks perfectly fine in a PDF
viewer because the viewer does not bind anything.

**Font round-trip.** The important one, and the reason this script exists.

Typst does not warn when a character has no glyph in the requested font. It falls
back through the system font list, renders the character in some other face, and
exits 0. No error, no warning, nothing anyone would catch by eye across hundreds
of pages. On another machine with different fonts installed, the same source
produces a different book.

The check enumerates every codepoint in the source, confirms each one survives
into the PDF via `pdftotext`, and lists the fonts actually embedded via
`pdffonts`. A substitution reported here is not necessarily a failure — the
fallback is why there is no tofu on the page — but it becomes *visible* and
deliberate rather than discovered in print.

**Raster image resolution.** `pdfimages -list` reports effective PPI after images
have been placed in the PDF. Anything below 300 PPI fails; anything above 600
PPI is a warning because unnecessarily large images can slow processing. This
is more useful than checking source file dimensions alone.

**Cover spine against the interior's extent.** The second of the two independent
routes to the same fact. `build-cover.py` measured the interior going in; this
measures the wrap coming out.

**Listing limits.** Description over 4,000 characters, more than 7 keywords, more
than 3 categories, a quotation mark in a keyword — all rejected by the form, all
cheaper to catch here.

## Reporting the result

If checks fail, **say which, and show the output.** Do not describe a build as
ready when preflight returned non-zero.

If checks pass, **do not describe the book as ready to print.** The script says
this itself; repeat it rather than dropping it:

- The gutter still has to be read in KDP's own previewer, page by page. It is the
  only thing that shows what the press will do.
- Any font substitution listed still has to be eyeballed in a proof.
- The proof copy still has to be ordered and read.

Those are not gaps in the script. They are things no script can do, and a report
that omits them is telling the user the book is finished when it is not.

## Dates

`reference/` carries a verification date on every KDP figure. KDP changes them
without notice and without a changelog. When a number is about to go into a real
upload, quote the date alongside it rather than presenting it as current.
