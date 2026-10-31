# kdp-publishing

Claude Code plugin for producing a print-ready Amazon KDP paperback with
[Typst](https://typst.app) — trim geometry, a full-wrap cover, mechanical
pre-flight, and an upload folder.

```
/plugin install kdp-publishing@danielrosehill
```

## It does not write your book

This plugin is **production, not authorship**. It takes a manuscript you already
have and turns it into two PDFs a printer will accept.

It does not draft chapters, generate blurbs, invent keywords or write your
description. Nothing in it assumes the text was written by an AI, and nothing in
it works better if it was. If you typed every word yourself, this is aimed at you.

That is a deliberate line. Typesetting and copywriting are different jobs with
different failure modes, and the tools that bundle them tend to be good at
neither. Ask Claude to help with your blurb whenever you like — just not as a
side effect of building a book.

## Why it exists

The expensive mistakes in print-on-demand are the ones that produce a
**successful-looking build**. Typst exits 0. The PDF opens. KDP accepts the
upload. You find out three weeks and one print charge later, when the proof copy
arrives.

Three of them, all handled here:

**A cover built from a stale page count.** Spine width is page count × paper
caliper, so a cover built before the interior was finished has a spine that does
not match the book — the spine type sits off-centre, or the title wraps onto the
front face. Nothing on screen reports it.

So the cover is built **last, and from the interior**. `build-cover.py` refuses to
take a page count and runs `pdfinfo` over the PDF you actually built.
`kdp-package.py` then measures the *finished wrap*, subtracts both faces and both
bleeds, and compares what is left against the spine this extent needs — the same
fact from the opposite direction. A stale cover has to defeat both.

**A missing glyph.** Typst does not warn when a character has no glyph in the
requested font. It falls back through the system font list, renders it in some
other face, and exits 0. On a machine with different fonts installed, the same
source produces a different book. Pre-flight enumerates every codepoint in the
source, confirms each survives into the PDF, and lists what actually got embedded.

**A gutter set for the wrong extent.** KDP's minimum inside margin is tiered by
page count, so a book that grows past 300 pages needs wider margins than the same
book at 299. Under it, text is swallowed into the bind on every page — and a PDF
viewer will never show you, because it does not bind anything. Margins here are
derived from the *measured* first-pass extent, not from an estimate.

The principle underneath all three: **check the artifact, not the signal that
stands in for it.**

## Standard trim sizes, by default

KDP splits paperback trims into standard and non-standard. Standard sizes are
available in every marketplace, are what the print-cost tables are quoted against,
and are the only ones some expanded-distribution channels accept.

So the plugin steers to KDP's US standard list — 5×8, 5.5×8.5, **6×9**, 7×10,
8.5×11 and the rest — and warns on anything else. A non-standard trim still
builds correctly; it just has to be a decision rather than a typo.

## The pipeline

```
/kdp-init       choose a standard trim and paper, write book.toml, copy templates
       ↓
/kdp-manuscript-review  flag common draft leftovers and empty/duplicate headings
       ↓
/kdp-listing-review     audit description, keywords and categories
       ↓
/kdp-build      typeset the interior — contents, pagination, gutter-aware margins, even page count
       ↓
/kdp-preflight  trim, parity, gutter, font round-trip, listing limits
       ↓
/kdp-cover      full wrap, spine measured from the built interior
       ↓
/kdp-package    dist/kdp-upload/ — PDFs plus what goes in which form field
```

Each step reads `book.toml`, the single source of the book's identity and print
settings. The title page, the cover and the KDP listing all derive from it, so
they cannot disagree — which matters because **KDP locks the title field 72 hours
after publication** and requires it to read exactly as the cover prints it.

## Interior layout and manuscript assets

The interior template creates an automatic table of contents from Typst heading
levels 1 and 2. It is enabled by default; set `[interior].table_of_contents = false`
in `book.toml` for journals, workbooks or books that do not need one. The title
page is unnumbered, contents pages use Roman numerals, and the manuscript body
restarts at Arabic page 1. Use Typst headings (`= Chapter`, `== Section`) rather
than bold-only text so the contents page can link to them.

For illustrations, use a Typst figure with a contained image so it scales to the
text area without distortion or overflowing the margins:

```typst
#figure(
  image("images/diagram.png", width: 100%, fit: "contain", alt: "Short description"),
  caption: [Diagram caption],
)
```

Image paths are relative to the `.typ` file that calls `image()`. The manuscript
review reports heading hierarchy and checks literal image paths, including
multiline calls and project-root paths. It ignores comments and warns about
missing files and non-portable absolute Windows paths. It never rewrites images
or alters the manuscript.

## Skills

- `kdp-print-geometry` — trim, paper, spine, margins, bleed, wrap dimensions
- `kdp-typeset-interior` — Typst interior, and the Typst behaviours that fail
  silently
- `kdp-cover-wrap` — the full wrap, and three layout rules that are each a lost
  proof copy
- `kdp-preflight` — what to verify, and what no script can verify for you

## Reference

`reference/` carries KDP's own figures with the **date each was verified** and the
URL it came from. KDP changes these without notice and without a changelog, so
quote the date alongside the number rather than presenting it as current.

- `trim-sizes.md` — standard trims, paper calipers, page-count limits
- `margins.md` — the tiered gutter table, outside margins, bleed
- `cover-spec.md` — wrap maths, safe zones, spine text, the barcode corners
- `listing-limits.md` — field limits and the 72-hour title lock

## Requirements

- [`typst`](https://github.com/typst/typst) on PATH
- `poppler-utils` — `pdfinfo`, `pdftotext`, `pdffonts`
- Contributors: CI also runs a real Typst build, cover, preflight and upload-package smoke test
- Python 3.11+ (for `tomllib`)

**Windows:** see [the Windows setup guide](docs/windows-setup.md) for installing
Python, Typst and the Poppler PDF utilities and adding them to PATH.

No API keys, no network calls, no accounts. The production scripts run locally
after their dependencies are installed.

## Scripts

They work standalone if you would rather not go through the commands. Each finds
the nearest `book.toml` by walking up from the working directory.

```bash
python3 scripts/kdp_geometry.py --list-trims
python3 scripts/kdp_geometry.py --pages 398 --trim 6x9 --json
python3 scripts/analyze-manuscript.py
python3 scripts/listing_audit.py
python3 scripts/build-interior.py
python3 scripts/build-cover.py
python3 scripts/preflight.py --json
python3 scripts/kdp-package.py
```

`kdp_geometry.py` is the single source of every number. Nothing else computes a
spine width, a wrap dimension or a gutter minimum on its own.

## Provenance

Extracted from two books actually printed this way — a 398-page generated
reference index and its companion technical volume. Both validated on KDP first
time. The checks in here exist because something went wrong once, not because
they seemed like good practice.

## Licence

MIT.
