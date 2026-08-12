---
description: Run every mechanical check on the built PDFs — trim, parity, gutter, font round-trip, spine against extent
---

Pre-flight the build.

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/preflight.py
```

Use `--json` if you need to act on the result programmatically. Exits non-zero on
any failure.

Use the `kdp-preflight` skill for what each check is protecting against. The one
worth understanding before you report a pass:

**Typst does not warn about missing glyphs.** When a character has no glyph in
the requested font, Typst falls back through the system font list, renders it in
whatever face it found, and exits 0. No error, no warning, and nothing anyone
would catch by eye in a few hundred pages. On another machine with different
fonts installed, the same source produces a different book. The round-trip check
— enumerate every codepoint in the source, confirm each survives into the PDF,
list what actually got embedded — is the only signal that exists.

**Report the result honestly.** If checks fail, say which and show the output. Do
not describe a build as ready when preflight returned non-zero.

**And do not describe a passing preflight as the book being ready to print.** The
script says so itself, and repeat it: the gutter still has to be checked in KDP's
own previewer page by page, any font substitution still has to be eyeballed in a
proof, and the proof copy still has to be ordered and read. Those are not
oversights in the script — they are things no script can do.

If the gutter minimum is the thing in question, check `reference/margins.md` for
the date those figures were verified. KDP changes them without notice and without
a changelog. If the date is old, say so rather than quoting it as current.
