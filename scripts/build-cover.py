#!/usr/bin/env python3
"""Render the full-wrap cover at the interior's ACTUAL measured extent.

    python3 build-cover.py
    python3 build-cover.py --pages 420      # what-if; refuses to write the file

Writes `<dist>/cover.pdf`: back cover, spine and front cover on one sheet with
bleed on all four outside edges. That single sheet is what KDP wants uploaded.

THE COVER IS BUILT LAST, AND FROM THE INTERIOR — NOT FROM A NUMBER.

Spine width is page count times paper caliper. So a cover built before the interior
was finished, or kept from a previous edition, has a spine that does not match the
book: at best the spine type sits off-centre, at worst the title wraps onto the
front face. It is not caught by a PDF viewer and it is not caught by KDP's uploader.
It is caught by the proof copy, three weeks and one print charge later.

So this script does not let you hand it a page count. It runs pdfinfo over the
interior you actually built. `--pages` exists only for asking what a different
extent would cost, and it refuses to overwrite cover.pdf when used.

That is one of two independent checks. kdp-package.py then measures the FINISHED
wrap, subtracts both faces and both bleeds, and compares what is left against the
spine this page count needs — arriving at the same fact from the opposite
direction. A stale cover has to defeat both.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import kdp_geometry as geo  # noqa: E402
import kdp_project as proj  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--project", type=Path, default=None)
    ap.add_argument("--pages", type=int, default=None,
                    help="model a different extent; will NOT write cover.pdf")
    args = ap.parse_args()

    try:
        cfg = proj.load(proj.find_project(args.project))
    except proj.ProjectError as err:
        sys.exit(f"! {err}")

    root, dist = cfg["root"], cfg["dist"]
    printing, paths, book = cfg["print"], cfg["paths"], cfg["book"]
    interior = dist / "interior.pdf"
    out = dist / "cover.pdf"

    if not interior.exists():
        sys.exit("! dist/interior.pdf missing — run build-interior.py first. The "
                 "spine width is a function of the interior's page count, so there "
                 "is nothing to build a cover against yet.")

    iw, ih, real_pages = proj.page_geometry(interior)
    pages = args.pages or real_pages
    what_if = args.pages is not None and args.pages != real_pages

    if pages % 2:
        sys.exit(f"! {pages} pages is odd — the interior should have been padded. "
                 f"Re-run build-interior.py.")

    dims = geo.cover_dimensions(pages, printing["trim"], printing["paper"])

    print(f"interior   {real_pages} pages, {iw / proj.PT:.3f} x {ih / proj.PT:.3f} in"
          + (f"  (modelling {pages})" if what_if else ""))
    print(f"spine      {dims['spine_in']} in ({dims['spine_mm']} mm)")
    print(f"full wrap  {dims['wrap_in'][0]} x {dims['wrap_in'][1]} in "
          f"({dims['wrap_px_300dpi'][0]} x {dims['wrap_px_300dpi'][1]} px @ 300dpi)")
    print(f"folds at   {dims['fold_lines_in'][0]} in and {dims['fold_lines_in'][1]} in "
          f"from the wrap's left edge")

    spine_text = dims["spine_text"]
    if spine_text["printable"]:
        print(f"spine text {spine_text['usable_band_in']} in usable band")
    else:
        print(f"spine text NOT PRINTABLE — {spine_text['reason']}")

    if what_if:
        print("\n--pages was given: modelled only, cover.pdf not written.")
        return 0

    template = root / paths["cover_template"]
    if not template.is_file():
        sys.exit(f"! {template} is missing. /kdp-init copies one in.")

    try:
        proj.typst_compile(
            src=template,
            out=out,
            root=root,
            font_path=root / paths["fonts"],
            inputs={
                "book_json": proj.write_book_json(cfg),
                "pages": str(pages),
                "spine": str(dims["spine_in"]),
                "trim_w": str(dims["trim"]["w"]),
                "trim_h": str(dims["trim"]["h"]),
                "spine_text": "true" if spine_text["printable"] else "false",
            },
        )
    except proj.ProjectError as err:
        sys.exit(f"! {err}")

    # Read back what was actually produced. Typst can silently render a page at a
    # size other than the one asked for if the template overrides `page(width:)`
    # itself, and a wrap that is the wrong width is a wrap whose folds land in the
    # wrong place.
    got_w, got_h, _ = proj.page_geometry(out)
    want_w, want_h = dims["wrap_in"]
    if (abs(got_w / proj.PT - want_w) > 0.02
            or abs(got_h / proj.PT - want_h) > 0.02):
        print(f"\n! the rendered wrap is {got_w / proj.PT:.4f} x "
              f"{got_h / proj.PT:.4f} in but the geometry calls for "
              f"{want_w} x {want_h} in.\n"
              f"  The template is overriding the page size it was handed.",
              file=sys.stderr)
        return 1

    print(f"\nwrote      {out.relative_to(root)} "
          f"({got_w / proj.PT:.4f} x {got_h / proj.PT:.4f} in, "
          f"{out.stat().st_size / 1024 / 1024:.1f} MB)")
    print(f"           title on cover: {book['title']}")
    print("\nConvert to CMYK at upload — KDP asks for CMYK and strips embedded "
          "profiles.\nConvert a copy, never the source.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
