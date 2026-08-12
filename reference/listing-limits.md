# KDP listing field limits

**Verified 2026-08-12** against KDP's title setup form and its keywords help page.

Machine-readable copy: `DESCRIPTION_MAX`, `KEYWORDS_MAX`, `CATEGORIES_MAX` in
`scripts/kdp_geometry.py`. Enforced by `preflight.py` and `kdp-package.py`.

**This plugin does not write any of this copy.** The limits are here so a
description that will be rejected is caught before upload rather than at it.

| Field | Limit | Editable after publication? |
|---|---|---|
| Description | 4,000 characters | Yes, any time |
| Keywords | 7 | Yes, any time |
| Categories | 3 | Yes |
| Title | — | **No, after 72 hours** |
| Subtitle | — | **No, after 72 hours** |

## The title is the one that cannot be fixed

KDP locks the title and subtitle fields **72 hours after publication**, and
requires the title to read **exactly as it appears on the cover**.

This is why `book.toml` is the single source of the book's identity and why
`title_lines` must join back to `title` exactly — the cover, the title page and
the listing all derive from one string, so they cannot drift into three
near-misses that are then permanent.

## Keyword rules

From KDP's own help page:

- **Word order is how people search.** Phrase a keyword in the order someone
  would type it.
- **No quotation marks.** KDP treats a quoted phrase as an exact match, and the
  book stops surfacing for anything less than the whole phrase. `preflight.py`
  fails the build on this.
- Do not repeat a word already covered by a chosen category.
- Do not make a claim ("best", "bestselling").
- Do not use a time-sensitive term ("new", "2026").

## Categories

Three slots. KDP has moved this number before and its keywords help page does not
state it, so if all three matter, confirm against the live form rather than
against this file.

## What is worth carrying in `book.toml`

`[listing]` holds **chosen** values only: language, audience, rights, ISBN,
categories, keywords, price note.

Anything **measurable** — page count, trim, spine width, wrap dimensions — is
never typed there. It is read back out of the built PDFs by `kdp-package.py`,
which is why `specs.txt` splits into a measured half and a chosen half.

If a value in the measured half looks wrong, the file is wrong. Rebuild rather
than correcting the form.
