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

- **Compiles more than once.** Printers need an even leaf count and the extent is
  not known until the document is laid out. Typst cannot decide this itself — a
  conditional on `counter(page).final()` changes the very count it reads and
  oscillates forever. The decision has to be made from outside the document.
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

When it succeeds, report the extent, the trim, and the spine width this page
count implies. Then run `/kdp-preflight` — and only after that `/kdp-cover`,
which must be built last.
