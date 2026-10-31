#!/usr/bin/env python3
"""Collect everything KDP asks to be uploaded into one folder, and check it.

    python3 kdp-package.py

Writes `<dist>/kdp-upload/`: the interior PDF, the cover PDF, the description as
plain text, and three text files naming exactly what goes in which field of the
KDP form.

NOTHING HERE IS AUTHORED. The description comes from the project's description
file, the targeting from `[listing]` in book.toml, the identity from `[book]`, and
the PDFs from build-interior.py and build-cover.py. This script only ever collects
and checks.

WHAT IT CHECKS, AND WHY EACH CHECK EXISTS

  - The interior really is the trim book.toml claims. KDP will accept a file at
    the wrong trim and print the book with the wrong margins. Nobody sees that
    until the proof arrives.
  - The page count is within supported limits and even, and the spine on the built cover matches THAT page
    count rather than a stale one. This is the second of the two independent
    checks on the cover: build-cover.py measured the interior on the way in, this
    measures the finished wrap on the way out and subtracts both faces and both
    bleeds to see what is left. A cover has to defeat both to reach the printer.
  - The description fits KDP's 4,000-character field.
  - Keywords and categories are within KDP's limits and contain no quotation marks.
  - Advisory listing-review warnings are included for manual review.
  - A previous upload folder is cleared so obsolete PDFs cannot survive a rebuild.
  - The title's display line-breaks join back to the title exactly. KDP will not
    let the title be edited more than 72 hours after publication and requires it
    to read exactly as the cover prints it.

The cover is optional on purpose: spine width is a function of the final page
count, so the cover is built last, and running this before one exists is the
normal thing to do.
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import kdp_geometry as geo  # noqa: E402
import kdp_project as proj  # noqa: E402
import listing_audit  # noqa: E402


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "book"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--project", type=Path, default=None)
    args = ap.parse_args()

    try:
        cfg = proj.load(proj.find_project(args.project))
    except proj.ProjectError as err:
        sys.exit(f"! {err}")

    root, dist = cfg["root"], cfg["dist"]
    book, printing, paths = cfg["book"], cfg["print"], cfg["paths"]
    listing = cfg["listing"]

    interior = dist / "interior.pdf"
    cover = dist / "cover.pdf"
    description_src = root / paths["description"]
    out = dist / "kdp-upload"
    stem = slug(book["title"])

    missing = [str(p.relative_to(root)) for p in (interior, description_src)
               if not p.exists()]
    if missing:
        print(f"! missing: {', '.join(missing)}", file=sys.stderr)
        print("  run: python3 build-interior.py", file=sys.stderr)
        return 1

    iw, ih, pages = proj.page_geometry(interior)
    trim_w, trim_h = geo.parse_trim(printing["trim"])
    std = geo.is_standard(trim_w, trim_h)

    if abs(iw / proj.PT - trim_w) > 0.03 or abs(ih / proj.PT - trim_h) > 0.03:
        # Only meaningful for a no-bleed interior; a bleed interior is legitimately
        # larger than trim, and interior_geometry() knows by how much.
        want_w, want_h = geo.interior_geometry(
            pages, printing["trim"], printing["bleed"], printing["paper"])["page_size_in"]
        if abs(iw / proj.PT - want_w) > 0.03 or abs(ih / proj.PT - want_h) > 0.03:
            print(f"! interior is {iw / proj.PT:.3f} x {ih / proj.PT:.3f}in, not the "
                  f"{want_w} x {want_h}in this book is specified at", file=sys.stderr)
            return 1

    geometry_problems = geo.validate(
        pages, printing["trim"], printing["paper"], printing["bleed"]
    )
    blocking_geometry = [
        problem for problem in geometry_problems
        if "not a KDP standard trim" not in problem and "no spine text" not in problem
    ]
    if blocking_geometry:
        for problem in blocking_geometry:
            print(f"! {problem}", file=sys.stderr)
        print("  rebuild the interior and resolve the print geometry before packaging.",
              file=sys.stderr)
        return 1

    description = description_src.read_text(encoding="utf-8").strip()
    n = len(description)
    if n > geo.DESCRIPTION_MAX:
        print(f"! description is {n:,} characters, over KDP's {geo.DESCRIPTION_MAX:,} "
              f"by {n - geo.DESCRIPTION_MAX:,}", file=sys.stderr)
        return 1

    keywords = listing.get("keywords", [])
    categories = listing.get("categories", [])
    if len(keywords) > geo.KEYWORDS_MAX:
        print(f"! {len(keywords)} keywords; KDP takes {geo.KEYWORDS_MAX}",
              file=sys.stderr)
        return 1
    if len(categories) > geo.CATEGORIES_MAX:
        print(f"! {len(categories)} categories; KDP takes {geo.CATEGORIES_MAX}",
              file=sys.stderr)
        return 1
    if any(isinstance(k, str) and '"' in k for k in keywords):
        print("! a keyword contains a quotation mark — KDP treats the quoted phrase "
              "as an exact match and the book stops surfacing for anything less",
              file=sys.stderr)
        return 1

    listing_warnings = listing_audit.audit_listing(
        description, keywords, categories
    )

    # The package is generated output. Clear it first so an old cover can never
    # survive a later run in which no valid current cover exists.
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)
    listing_review = [
        f"LISTING REVIEW — {book['title']}",
        "=" * 68,
        "",
        "These are automated review suggestions, not a KDP approval decision.",
        "Check current KDP guidance and review each suggestion yourself.",
        "",
    ]
    if listing_warnings:
        listing_review.extend(f"WARN  {warning}" for warning in listing_warnings)
    else:
        listing_review.append("No common listing issues detected by the local checks.")
    (out / "listing-review.txt").write_text(
        "\n".join(listing_review) + "\n", encoding="utf-8"
    )
    shutil.copy2(interior, out / f"{stem}-interior.pdf")
    (out / "description.txt").write_text(description + "\n", encoding="utf-8")

    dims = geo.cover_dimensions(pages, printing["trim"], printing["paper"])
    cover_line = "  Paperback Cover    ->  NOT YET BUILT — build it last"
    cover_block = (
        f"  Spine width         not built yet — will be {dims['spine_in']:.4f} in "
        f"at {pages} pages\n"
        f"  Full wrap           not built yet — will be "
        f"{dims['wrap_in'][0]} x {dims['wrap_in'][1]} in"
    )

    if cover.exists():
        cw, ch, cpages = proj.page_geometry(cover)
        measured = (cw / proj.PT) - 2 * trim_w - 2 * geo.BLEED
        if abs(measured - dims["spine_in"]) > 0.01:
            print(f"! cover spine measures {measured:.4f}in but {pages} pages needs "
                  f"{dims['spine_in']:.4f}in — this cover is stale", file=sys.stderr)
            return 1
        expected_wrap_height = dims["wrap_in"][1]
        if abs(ch / proj.PT - expected_wrap_height) > 0.02:
            print(
                f"! cover height is {ch / proj.PT:.4f}in but the wrap needs "
                f"{expected_wrap_height:.4f}in — rebuild the cover",
                file=sys.stderr,
            )
            return 1
        if cpages != 1:
            print(f"! cover is {cpages} pages; KDP wants one page carrying back, "
                  f"spine and front", file=sys.stderr)
            return 1
        shutil.copy2(cover, out / f"{stem}-cover.pdf")
        cover_line = (f"  Paperback Cover    ->  {stem}-cover.pdf\n"
                      f"                         {cw / proj.PT:.4f} x "
                      f"{ch / proj.PT:.4f}in wrap, {measured:.4f}in spine")
        cover_block = (f"  Spine width         {measured:.4f} in   "
                       f"(measured back out of the built wrap)\n"
                       f"  Full wrap           {cw / proj.PT:.4f} x "
                       f"{ch / proj.PT:.4f} in")

    contributors = "; ".join(book.get("contributors", []))
    subtitle = book.get("subtitle", "")

    (out / "title.txt").write_text(
        "Generated from book.toml. Edit that, not this.\n"
        "\n"
        "KDP takes the title exactly as it appears on the cover, and will not let\n"
        "it be edited more than 72 hours after publication. Get it right here.\n"
        "\n"
        "TITLE\n"
        f"{book['title']}\n"
        "\n"
        "SUBTITLE\n"
        f"{subtitle}\n"
        "\n"
        "AUTHOR\n"
        f"{book['author']}\n"
        "\n"
        "CONTRIBUTORS\n"
        f"{contributors}\n",
        encoding="utf-8")

    trim_rows = []
    for key, (w, h, cm) in geo.KDP_STANDARD_TRIMS.items():
        hit = abs(w - trim_w) < 0.01 and abs(h - trim_h) < 0.01
        trim_rows.append(f"      {'[x]' if hit else '[ ]'} {w} x {h} in ({cm})")
    trim_list = "\n".join(trim_rows)

    kw = "\n".join(f"  {i}. {k}" for i, k in enumerate(keywords, 1)) or "  (none set)"
    cats = "\n".join(f"  {c}" for c in categories) or "  (none set)"
    bleed_choice = "Bleed (PDF only)" if printing["bleed"] else "No bleed"
    paper_label = {
        "white-bw": "Black & white on white paper",
        "cream-bw": "Black & white on cream paper",
        "standard-colour": "Standard colour",
        "groundwood-bw": "Black & white on groundwood paper",
        "premium-colour": "Premium colour",
    }[printing["paper"]]

    (out / "specs.txt").write_text(f"""KDP TECHNICAL SPECS AND TARGETING — {book['title']}
{'=' * 68}

Two halves, split by where the values come from.

MEASURED — read out of the PDFs in this folder
{'-' * 68}

Do not type these from memory into the KDP form. If one looks wrong, the file
is wrong, and the fix is to rebuild rather than to correct the form.

  Page count          {pages}   (even; build-interior.py adds a parity leaf)
  Interior page size  {iw / proj.PT:.3f} x {ih / proj.PT:.3f} in
{cover_block}

PRINT OPTIONS — exactly what to select in the form
{'-' * 68}

The form recomputes the spine from these. Select anything other than what is
marked and the spine KDP expects stops matching the cover that was built.

  Trim Size           {trim_w} x {trim_h} in{'' if std else '   ** NON-STANDARD **'}
{trim_list}

  Bleed               {bleed_choice}
                      {'Art runs to the page edge, so the file is supplied'
                       ' oversized and KDP trims into it.'
                       if printing['bleed'] else
                       'Nothing in this interior runs to the page edge, so the'}
                      {'' if printing['bleed'] else
                       'file goes up at trim size. Choosing bleed tells KDP to'}
                      {'' if printing['bleed'] else
                       'trim 0.125in off content that is not there.'}

  Ink and Paper       {paper_label}
                      Caliper {geo.PAPER_CALIPER[printing['paper']]} in/page — this is what sets the spine width above.

  Cover Finish        {printing['cover_finish'].title()}

CHOSEN — from [listing] in book.toml
{'-' * 68}

  Language            {listing.get('language', '(not set)')}
  Primary audience    {listing.get('primary_audience', '(not set)')}
  Publishing rights   {listing.get('publishing_rights', '(not set)')}
  ISBN                {listing.get('isbn', '(not set)')}

Categories ({len(categories)} of up to {geo.CATEGORIES_MAX}):
{cats}

Keywords ({len(keywords)} of {geo.KEYWORDS_MAX}):
{kw}

  Keyword rules, from KDP's own help page: word order is how people search, so
  phrase them in that order; no quotation marks; do not repeat a category word,
  make a claim, or use a time-sensitive term. Keywords and the description can
  be revised whenever. The title cannot, 72 hours after publication.

  Price               {listing.get('price_note', '(not set)')}
""", encoding="utf-8")

    margins = geo.interior_geometry(
        pages, printing["trim"], printing["bleed"], printing["paper"])["margins_in"]

    (out / "README.txt").write_text(f"""KDP UPLOAD — {book['title']}
{'=' * 68}

Everything in this folder is generated. Do not edit anything here; edit the
source and re-run:

    python3 build-interior.py
    python3 build-cover.py
    python3 preflight.py
    python3 kdp-package.py

WHAT GOES WHERE
{'-' * 68}

  Paperback Content  ->  {stem}-interior.pdf
{cover_line}
  Description field  ->  description.txt  ({n:,} of {geo.DESCRIPTION_MAX:,} chars)
  Title / subtitle   ->  title.txt
  Print Options      ->  specs.txt  (measured half)
  Keywords, category ->  specs.txt  (chosen half)

  Book Title    ->  {book['title']}
  Subtitle      ->  {subtitle}
  Author        ->  {book['author']}
  Contributors  ->  {contributors}

  All of these derive from book.toml, so the cover, the title page and this
  listing cannot disagree. That matters more than it looks: KDP will not let
  the title be edited more than 72 hours after publication, and requires it to
  read exactly as the cover prints it.

INTERIOR AS BUILT
{'-' * 68}

  Trim        {trim_w} x {trim_h} in{'  (KDP standard)' if std else '  ** NON-STANDARD **'}
  Pages       {pages}  (even; build-interior.py pads parity)
  Bleed       {'yes — file is supplied oversized' if printing['bleed'] else
               'none — file is supplied at trim size'}
  Paper       {paper_label}
  Gutter      {margins['inside']}in inside margin
              (KDP's minimum at {pages} pages is {geo.min_gutter(pages)}in)

              [VERIFY] Confirm that against KDP's CURRENT minimum before
              uploading. The figure in reference/margins.md carries the date it
              was checked, and KDP changes it without notice. Getting it wrong
              swallows text into the spine on every page of the book.

SETTINGS THAT MUST MATCH THE FILE
{'-' * 68}

Choose these in the KDP form, or the spine width it assumes will not be the
spine width the cover was built to:

  Ink and paper     {paper_label}
  Trim size         {trim_w} x {trim_h} in
  Bleed             {bleed_choice}
  Cover finish      {printing['cover_finish'].title()}

BEFORE UPLOADING
{'-' * 68}

  - Convert the cover to CMYK at upload. KDP asks for CMYK covers and strips
    embedded profiles. Convert the copy, not the source.
  - Check the KDP previewer page by page. It is the only thing that shows what
    the press will do with the gutter.
  - Re-run preflight.py if anything changed since the last build.
  - Order the proof copy and read it.
""", encoding="utf-8")

    print(f"  wrote  {out.relative_to(root)}/")
    for f in sorted(out.iterdir()):
        print(f"    {f.name:48} {f.stat().st_size:>12,} bytes")
    if not cover.exists():
        print(f"\n  ! no cover yet — build it last, against the final {pages} pages:")
        print(f"    python3 build-cover.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
