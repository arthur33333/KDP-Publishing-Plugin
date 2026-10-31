---
description: Review manuscript source for common draft leftovers and structural warnings
argument-hint: "[optional — project directory]"
---

Run the conservative manuscript review:

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/analyze-manuscript.py
```

Pass `--project` followed by a project directory when needed. The script reads
the `[paths].body` entry from `book.toml` and supports one Typst file or a
directory containing multiple `.typ` files.

It reports likely editorial placeholders (TODO, FIXME, TBD, TK, Lorem ipsum,
"your text here", and "[insert ...]"), headings with no visible source content
before the next heading, duplicate heading titles within one source file, and
missing image files referenced by literal `image("...")` calls. It handles
multiline image calls and project-root paths, ignores Typst comments, and warns
about absolute Windows paths that will not work on another machine.

These are **warnings, not automatic corrections**. A repeated heading or an
empty section can be intentional, and the checker cannot assess factual
accuracy, originality, grammar, rights, or writing quality. Review every finding
in context. It never edits the manuscript.

Use `--json` for machine-readable output. Use `--strict` to return exit status
1 when warnings exist, for CI or scripted workflows.

Run this before `/kdp-build`; it complements, but does not replace,
`/kdp-preflight`, the KDP Previewer, or a physical proof copy.
