---
description: Typeset the interior PDF at KDP trim, with margins cleared against the gutter minimum and an even page count
argument-hint: "[optional — 'proof' to skip the parity leaf]"
---

Typeset the interior. Scope: $ARGUMENTS

Use the `kdp-typeset-interior` skill. In short:

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/build-interior.py
```

Run it from inside the book project, or pass `--project`. It finds the nearest
`book.toml` by walking up from the working directory.

**What it does that a single `typst compile` does not**, and why you should not
replace it with one:

- **Repeats until the geometry settles.** It measures the actual extent,
  corrects the gutter tier when the page count crosses a KDP threshold, and adds
  a parity leaf for production builds. It stops only when the measured gutter
  tier and even page count agree. `--no-parity` is for proofing only: it still
  corrects the gutter.
- **Derives the margins from the measured extent.** KDP's minimum gutter is
  tiered by page count, so a book that crosses 300 pages needs a wider inside
  margin than the same book at 299. The second pass uses a real measurement.

**If Typst errors**, read the message before changing anything. The two failures
that do not look like what they are:

- A literal `/*` in a hand-written template opens a block comment and silently
  eats the rest of the file. The build succeeds and the document is short.
- `pagebreak()` is illegal inside a `columns()` container. Use page-level columns
  if back matter needs to start on a fresh page.

**Do not hand-edit the output PDF or the generated body.** If an entry is wrong,
fix the source or the template.

The title page is unnumbered, contents pages use lower-case Roman numerals, and
the manuscript restarts at Arabic page 1. The contents page is generated from
level-one and level-two Typst headings.

When it succeeds, report the extent, the trim, and the spine width this page
count implies. Then run `/kdp-preflight` — and only after that `/kdp-cover`,
which must be built last.
