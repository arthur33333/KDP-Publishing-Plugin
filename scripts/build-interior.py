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


def table_of_contents_enabled(cfg: dict) -> bool:
    """Read the optional contents-page setting, defaulting to enabled."""
    settings = cfg.get("interior", {})
    enabled = settings.get("table_of_contents", True)
    if not isinstance(enabled, bool):
        raise proj.ProjectError(
            "[interior].table_of_contents must be true or false in book.toml."
        )
    return enabled


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
    # Existing projects without an [interior] section get the default contents page.
    toc_enabled = table_of_contents_enabled(cfg)

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
            "toc": "true" if toc_enabled else "false",
        },
    )
    _, _, pages = proj.page_geometry(out)
    return out, pages


def build_until_stable(cfg: dict, no_parity: bool = False,
                       max_passes: int = 5) -> tuple[Path, int, list[dict]]:
    """Rebuild until both the gutter tier and requested page parity are stable."""
    pages_est = 300
    parity = False
    history: list[dict] = []

    for pass_number in range(1, max_passes + 1):
        out, pages = compile_pass(cfg, pages_est=pages_est, parity=parity)
        try:
            measured_gutter = geo.min_gutter(pages)
            estimated_gutter = geo.min_gutter(pages_est)
        except geo.GeometryError as err:
            raise proj.ProjectError(str(err)) from err

        history.append({
            "pass": pass_number,
            "estimated_pages": pages_est,
            "parity_leaf": parity,
            "measured_pages": pages,
            "measured_gutter": measured_gutter,
        })

        gutter_stable = measured_gutter == estimated_gutter
        parity_stable = no_parity or pages % 2 == 0
        if gutter_stable and parity_stable:
            return out, pages, history

        # For a normal production build, ask the next pass for a parity leaf if
        # the measured result is odd. For proofing, keep the true odd extent but
        # still repeat when its measured gutter tier differs from the estimate.
        next_pages_est = pages + (pages % 2 if not no_parity else 0)
        next_parity = parity or (not no_parity and bool(pages % 2))

        if next_pages_est == pages_est and next_parity == parity:
            raise proj.ProjectError(
                "interior geometry did not stabilise; check the template for "
                "content that changes page count between builds"
            )

        pages_est, parity = next_pages_est, next_parity

    raise proj.ProjectError(
        f"interior geometry did not stabilise after {max_passes} passes; "
        "the PDF was not accepted as final"
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--project", type=Path, default=None)
    ap.add_argument("--no-parity", action="store_true",
                    help="skip the parity leaf for proofing, but still correct gutter tiers")
    args = ap.parse_args()

    try:
        cfg = proj.load(proj.find_project(args.project))
    except (proj.ProjectError, OSError, ValueError) as err:
        sys.exit(f"! {err}")

    printing = cfg["print"]
    trim_w, trim_h = geo.parse_trim(printing["trim"])
    std = geo.is_standard(trim_w, trim_h)

    print(f"project    {cfg['root']}")
    print(f"trim       {trim_w} x {trim_h} in "
          f"({'standard: ' + std if std else 'NON-STANDARD'})")
    print(f"paper      {printing['paper']}")

    try:
        out, pages, history = build_until_stable(cfg, no_parity=args.no_parity)
    except (proj.ProjectError, geo.GeometryError) as err:
        sys.exit(f"! {err}")

    for item in history:
        print(
            f"pass {item['pass']}     {item['measured_pages']} pages "
            f"(gutter {item['measured_gutter']}in; "
            f"estimated from {item['estimated_pages']} pages)"
        )

    w, h, pages = proj.page_geometry(out)
    problems = geo.validate(pages, printing["trim"], printing["paper"],
                            printing["bleed"])
    if args.no_parity:
        problems = [problem for problem in problems if "is odd" not in problem]

    print(f"\nwrote      {out.relative_to(cfg['root'])}")
    print(f"           {w / proj.PT:.3f} x {h / proj.PT:.3f} in, {pages} pages, "
          f"{out.stat().st_size / 1024 / 1024:.1f} MB")

    if args.no_parity and pages % 2:
        print("           proofing build only — odd page count is intentional")
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
