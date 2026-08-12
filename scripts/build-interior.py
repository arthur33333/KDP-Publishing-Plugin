#!/usr/bin/env python3
"""Typeset the interior PDF, at KDP's trim, with an even leaf count.

    python3 build-interior.py                 # from the nearest book.toml
    python3 build-interior.py --no-parity     # skip the second pass (proofing only)

Writes `<dist>/interior.pdf`.

THE INTERIOR IS RENDERED TWICE, ON PURPOSE. Printers need an even leaf count, and
the extent is not known until the document has been laid out. So the first pass is
compiled and counted, and if it came back odd a blank parity leaf is added and the
whole thing is compiled again.

This cannot be decided inside Typst. A conditional on `counter(page).final()`
oscillates: adding the leaf makes the count even, which makes the condition false,
which removes the leaf. The decision has to be made by something standing outside
the document, which is why this script exists rather than a clever template.

Margins are computed from the trim and the FIRST PASS page count, because KDP's
minimum gutter is tiered by extent — a book that crosses 300 pages needs a wider
inside margin than the same book at 299. The second pass therefore uses margins
derived from a real measurement rather than from an estimate.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import kdp_geometry as geo  # noqa: E402
import kdp_project as proj  # noqa: E402


def compile_pass(cfg: dict, pages_est: int, parity: bool) -> tuple[Path, int]:
    """Compile once at margins derived from `pages_est`; return the PDF and extent."""
    root, dist = cfg["root"], cfg["dist"]
    printing, paths = cfg["print"], cfg["paths"]

    trim_w, trim_h = geo.parse_trim(printing["trim"])
    inner = geo.interior_geometry(pages_est, printing["trim"], printing["bleed"])
    m = inner["margins_in"]

    template = root / paths["interior_template"]
    if not template.is_file():
        raise proj.ProjectError(
            f"{template} is missing. /kdp-init copies one in; if you deleted it, "
            f"point [paths].interior_template at your own."
        )

    dist.mkdir(parents=True, exist_ok=True)
    out = dist / "interior.pdf"
    book_json = proj.write_book_json(cfg)

    proj.typst_compile(
        src=template,
        out=out,
        root=root,
        font_path=root / paths["fonts"],
        inputs={
            "book_json": book_json,
            "trim_w": str(trim_w),
            "trim_h": str(trim_h),
            "bleed": "true" if printing["bleed"] else "false",
            "margin_inside": str(m["inside"]),
            "margin_outside": str(m["outside"]),
            "margin_top": str(m["top"]),
            "margin_bottom": str(m["bottom"]),
            "body": paths["body"],
            "parity_leaf": "true" if parity else "false",
        },
    )
    _, _, pages = proj.page_geometry(out)
    return out, pages


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--project", type=Path, default=None)
    ap.add_argument("--no-parity", action="store_true",
                    help="do not pad to an even leaf count (proofing only)")
    args = ap.parse_args()

    try:
        cfg = proj.load(proj.find_project(args.project))
    except proj.ProjectError as err:
        sys.exit(f"! {err}")

    printing = cfg["print"]
    trim_w, trim_h = geo.parse_trim(printing["trim"])
    std = geo.is_standard(trim_w, trim_h)

    print(f"project    {cfg['root']}")
    print(f"trim       {trim_w} x {trim_h} in "
          f"({'standard: ' + std if std else 'NON-STANDARD'})")
    print(f"paper      {printing['paper']}")

    try:
        # First pass. The margin tier needs a page count and we do not have one yet,
        # so seed with the middle tier; the second pass corrects it from the measured
        # extent. A book that lands in a different tier than the seed gets rebuilt
        # with the right gutter below.
        _, pages = compile_pass(cfg, pages_est=300, parity=False)
        print(f"pass 1     {pages} pages")

        target = pages + (pages % 2) if not args.no_parity else pages
        needs_second = (
            not args.no_parity
            and (pages % 2 or geo.min_gutter(pages) != geo.min_gutter(300))
        )

        if needs_second:
            out, pages = compile_pass(cfg, pages_est=target, parity=bool(pages % 2))
            print(f"pass 2     {pages} pages "
                  f"(gutter {geo.min_gutter(pages)}in minimum at this extent)")
        else:
            out = cfg["dist"] / "interior.pdf"

        if not args.no_parity and pages % 2:
            # The parity leaf changed the tier, which changed the margins, which
            # changed the extent back to odd. Rare, but it happens on a book sitting
            # exactly on a tier boundary. One more pass settles it.
            out, pages = compile_pass(cfg, pages_est=pages + 1, parity=True)
            print(f"pass 3     {pages} pages (tier boundary)")

    except proj.ProjectError as err:
        sys.exit(f"! {err}")

    w, h, pages = proj.page_geometry(out)
    problems = geo.validate(pages, printing["trim"], printing["paper"],
                            printing["bleed"])

    print(f"\nwrote      {out.relative_to(cfg['root'])}")
    print(f"           {w / proj.PT:.3f} x {h / proj.PT:.3f} in, {pages} pages, "
          f"{out.stat().st_size / 1024 / 1024:.1f} MB")

    if problems:
        print()
        for problem in problems:
            print(f"!! {problem}")
        return 1

    spine = geo.spine_width(pages, printing["paper"])
    print(f"\nnext       the cover, built against THESE {pages} pages "
          f"(spine {spine:.4f}in):")
    print(f"           python3 build-cover.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
