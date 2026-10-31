---
description: Assemble the KDP upload folder — PDFs plus a file naming exactly what goes in which field of the form
---

Assemble the upload folder.

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/kdp-package.py
```

Writes `dist/kdp-upload/`: the interior PDF, the cover PDF, the description as
plain text, `listing-review.txt` with advisory checks, and `title.txt`, `specs.txt`
and `README.txt` naming what goes in which field.

**Nothing in that folder is authored.** The description comes from the project's
description file, the targeting from `[listing]` in `book.toml`, the identity from
`[book]`, the PDFs from the build. This script only ever collects and checks.

`specs.txt` splits deliberately into a **measured** half and a **chosen** half.
The measured half is read back out of the PDFs in the folder. Do not retype those
values into the KDP form from memory — if one looks wrong, the file is wrong, and
the fix is to rebuild rather than to correct the form.

**This is the second independent check on the cover.** `build-cover.py` measured
the interior on the way in; this measures the finished wrap on the way out,
subtracts both faces and both bleeds, and compares what is left against the spine
this page count needs. Same fact, opposite direction. A stale cover has to defeat
both.

Running this before a cover exists is normal and expected — the cover is built
last, so the folder is assembled once without it and once with.

**If the user is filling in the KDP form now**, walk them through `README.txt`
field by field and flag two things:

- Convert the cover to CMYK at upload. KDP asks for CMYK and strips embedded
  profiles. Convert a copy, never the source.
- The print options selected in the form must match the file. Choose a different
  paper or trim there and the spine KDP computes stops matching the cover that was
  built.

Do not offer to write the description, the blurb or the keywords. Those are the
user's copy. If they ask for help with them, that is a normal request and you can
help — but do not volunteer it as part of this workflow.
