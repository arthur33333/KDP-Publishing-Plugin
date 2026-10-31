---
description: Review KDP title, description, keywords and categories for common listing issues
argument-hint: "[optional — project directory]"
---

Run the local listing review:

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/listing_audit.py
```

Pass `--project` followed by a project directory when needed. The script reads
the title from `book.toml`, the description from the configured
`[paths].description` file, and keywords/categories from `[listing]`.

It flags empty fields, duplicate keywords, keywords that repeat category words,
quotation marks, likely promotional claims, time-sensitive wording, and
configured field-count/description-length limits. Findings are warnings for
human review; it does not invent metadata, predict search volume, choose
categories, or guarantee KDP approval.

Use `--json` for machine-readable output or `--strict` to return exit status 1
when warnings exist. The review runs locally and requires no API key.
