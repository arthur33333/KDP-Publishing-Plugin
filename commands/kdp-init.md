---
description: Scaffold a KDP book project — choose a standard trim, write book.toml, copy the Typst templates in
argument-hint: "[optional — book title, or a trim size like 6x9]"
---

Set up a KDP paperback project here. Scope: $ARGUMENTS

Use the `kdp-print-geometry` skill for the trim decision. In short:

1. **Check the tools first.** `typst --version`, plus `pdfinfo -v`, `pdftotext -v`, `pdffonts -v` and `pdfimages -v` for Poppler.
   All are required and none is worth discovering halfway through a build.

2. **Establish what the book is.** Ask only what you cannot infer: title, author,
   and whether there is an existing manuscript in this directory. Glob for
   `*.typ`, `*.md`, `manuscript/`, `chapters/` before asking — if there is
   obviously a manuscript here, say what you found and confirm rather than asking
   an open question.

   **Do not offer to write the book.** This plugin typesets a manuscript that
   already exists. If there is no manuscript, say so plainly and stop after
   scaffolding — the project is ready, the text is the user's to supply.

3. **Choose the trim.** Run:

   ```
   python3 ${CLAUDE_PLUGIN_ROOT}/scripts/kdp_geometry.py --list-trims
   ```

   Recommend a KDP **standard** size and say why it suits this book. Default to
   6x9 for non-fiction, reference and technical; 5.5x8.5 for novels and memoir;
   7x10 or 8.5x11 where figures, tables or code need the measure.

   If the user asks for a non-standard size, build it — but tell them once, in a
   sentence, that non-standard trims are refused by some marketplaces and by
   expanded distribution, then proceed with their choice.

4. **Choose the paper.** `cream-bw` for prose, `white-bw` for anything with
   figures or fine rules, `groundwood-bw` only where the selected marketplace
   offers it, and colour only if the interior genuinely needs it. Standard and
   premium colour share the same KDP spine caliper; page limits still differ by
   paper and trim. Set this before a cover exists.

5. **Write the project.** Copy `${CLAUDE_PLUGIN_ROOT}/templates/book.toml` to
   `./book.toml` and fill in what you established. Copy `interior.typ` and
   `cover.typ` into `./templates/`. Create `manuscript/`, `listing/` and
   `assets/fonts/` only as things go into them — do not scaffold empty folders.

   Set `title_lines` to how the title should break across lines on the cover. It
   must join back to `title` with single spaces or every script refuses to build.

6. **Report the geometry** the book will be built at, and name the next command.

Do not build anything yet. `/kdp-build` is the next step and it needs a
manuscript.
