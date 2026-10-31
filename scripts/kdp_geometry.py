#!/usr/bin/env python3
"""KDP print geometry: trim sizes, spine width, margins, full-wrap dimensions.

    python3 kdp_geometry.py --pages 398                       # 6x9 cream B&W
    python3 kdp_geometry.py --pages 398 --trim 5.5x8.5 --json
    python3 kdp_geometry.py --list-trims

Every other script in this plugin imports this module rather than carrying its own
copy of the numbers. That is the point: a caliper or a bleed figure written down in
two places is a caliper that will disagree with itself the first time KDP moves it.

PAPER CALIPERS, PAGE LIMITS AND GUTTER FIGURES RE-VERIFIED ON 2026-10-31;
standard trim names last checked 2026-08-12. KDP changes these without notice and
without a changelog. `reference/` carries the source URL and verification date for
each table; re-check before any upload that matters and move the date when you do.

WHY THE US STANDARD SIZES ARE PRIVILEGED. KDP splits paperback trims into "standard"
and "non-standard". Standard sizes are available in every marketplace, are the only
ones some distribution channels accept, and are what the print-cost tables are
quoted against. A non-standard trim is not an error and this module will compute it
happily, but `is_standard()` returns False and the callers surface that, because
choosing one is a decision that should be made deliberately rather than by typing a
number slightly wrong.
"""

from __future__ import annotations

import argparse
import json

# --- Trim sizes --------------------------------------------------------------
#
# KDP's "Standard" paperback trim sizes, in inches, from the paperback print
# options form. Verified 2026-08-12.
#
# Keyed by the string a user types. The metric column is KDP's own rounding, kept
# verbatim so a value pasted into the KDP form matches what the form shows rather
# than differing in the last decimal place.
KDP_STANDARD_TRIMS: dict[str, tuple[float, float, str]] = {
    "5x8":        (5.0,  8.0,  "12.7 x 20.32 cm"),
    "5.06x7.81":  (5.06, 7.81, "12.85 x 19.84 cm"),
    "5.25x8":     (5.25, 8.0,  "13.34 x 20.32 cm"),
    "5.5x8.5":    (5.5,  8.5,  "13.97 x 21.59 cm"),
    "6x9":        (6.0,  9.0,  "15.24 x 22.86 cm"),
    "6.14x9.21":  (6.14, 9.21, "15.6 x 23.39 cm"),
    "6.69x9.61":  (6.69, 9.61, "16.99 x 24.41 cm"),
    "7x10":       (7.0,  10.0, "17.78 x 25.4 cm"),
    "7.44x9.69":  (7.44, 9.69, "18.9 x 24.61 cm"),
    "7.5x9.25":   (7.5,  9.25, "19.05 x 23.5 cm"),
    "8x10":       (8.0,  10.0, "20.32 x 25.4 cm"),
    "8.5x11":     (8.5,  11.0, "21.59 x 27.94 cm"),
}

DEFAULT_TRIM = "6x9"

# What each size is actually good for. Surfaced by /kdp-init so the choice is made
# on the book rather than on which number looked familiar.
TRIM_NOTES: dict[str, str] = {
    "5x8":       "Novellas, poetry, pocket non-fiction. Short measure; long lines look cramped.",
    "5.06x7.81": "Mass-market feel. Uncommon outside fiction.",
    "5.25x8":    "Slightly roomier than 5x8, same use.",
    "5.5x8.5":   "Novels, memoirs. The other default alongside 6x9.",
    "6x9":       "THE DEFAULT. Non-fiction, guides, reference, technical. Widest channel support.",
    "6.14x9.21": "Royal. Academic and reference; near-6x9 without 6x9's ubiquity.",
    "6.69x9.61": "Larger reference. Check print cost before committing.",
    "7x10":      "Workbooks, manuals, books with figures. Large trim: higher print cost.",
    "7.44x9.69": "Crown Quarto. Technical books; matches Lulu's equivalent size.",
    "7.5x9.25":  "Technical and illustrated. Large trim.",
    "8x10":      "Illustrated, children's, photo-led. Large trim.",
    "8.5x11":    "US Letter. Workbooks, textbooks, anything with wide tables or code.",
}

# --- Paper -------------------------------------------------------------------
#
# Per-page caliper in inches. Verified against KDP paperback cover specifications on 2026-10-31.
PAPER_CALIPER: dict[str, float] = {
    "white-bw":        0.002252,
    "cream-bw":        0.0025,
    "groundwood-bw":   0.00235,
    "standard-colour": 0.002347,
    "premium-colour":  0.002347,
}
DEFAULT_PAPER = "cream-bw"

PAPER_NOTES: dict[str, str] = {
    "white-bw":        "B&W on white. Cheapest. Higher contrast; can glare across long text.",
    "cream-bw":        "B&W on cream. Easier on the eye over hundreds of pages. Standard for prose.",
    "groundwood-bw":   "B&W on groundwood paper. Availability depends on marketplace.",
    "standard-colour": "Colour, standard ink. Lower-cost colour printing.",
    "premium-colour":  "Colour, premium ink. Photo-grade, most expensive.",
}

STANDARD_PAGE_LIMITS: dict[str, tuple[int, int]] = {
    "white-bw": (24, 828),
    "cream-bw": (24, 776),
    "groundwood-bw": (24, 812),
    "standard-colour": (72, 600),
    "premium-colour": (24, 828),
}
PAGE_LIMIT_OVERRIDES: dict[str, dict[str, tuple[int, int] | None]] = {
    "8.25x6": {
        "white-bw": (24, 800), "cream-bw": (24, 750),
        "groundwood-bw": (24, 784), "standard-colour": (72, 600),
        "premium-colour": (24, 800),
    },
    "8.25x8.25": {
        "white-bw": (24, 800), "cream-bw": (24, 750),
        "groundwood-bw": (24, 784), "standard-colour": (72, 600),
        "premium-colour": (24, 800),
    },
    "8.27x11.69": {
        "white-bw": (24, 780), "cream-bw": (24, 730),
        "groundwood-bw": (24, 764), "standard-colour": None,
        "premium-colour": (24, 590),
    },
    "8.5x8.5": {
        "white-bw": (24, 590), "cream-bw": (24, 550),
        "groundwood-bw": (24, 578), "standard-colour": (72, 600),
        "premium-colour": (24, 590),
    },
    "8.5x11": {
        "white-bw": (24, 590), "cream-bw": (24, 550),
        "groundwood-bw": (24, 578), "standard-colour": (72, 600),
        "premium-colour": (24, 590),
    },
}

# --- Fixed KDP figures -------------------------------------------------------

BLEED = 0.125            # inches, added to top, bottom and both outside edges
SAFE_ZONE = 0.25         # KDP's minimum clearance from the trim line for cover content
SPINE_TEXT_MIN_PAGES = 80  # KDP prints no spine text at or below 79 pages
SPINE_TEXT_CLEARANCE = 0.0625  # KDP's stated minimum type-to-fold clearance
PAGE_MIN = 24
PAGE_MAX = 828           # Global maximum envelope; use page_limits() for actual limits.
DESCRIPTION_MAX = 4000
KEYWORDS_MAX = 7
CATEGORIES_MAX = 3
PT = 72.0                # PostScript points per inch

# Minimum INSIDE margin (gutter) by page count. KDP states these as hard minimums;
# going under them pulls text into the bind on every page of the book, which is
# invisible in a PDF viewer and obvious in a proof copy. Verified 2026-10-31.
GUTTER_TIERS: list[tuple[int, float]] = [
    (150, 0.375),
    (300, 0.500),
    (500, 0.625),
    (700, 0.750),
    (828, 0.875),
]

# KDP's minimum OUTSIDE margin (top, bottom, outer) is 0.25in with no bleed and
# 0.375in with bleed. Those are floors, not designs — see recommended_margins().
OUTSIDE_MIN_NO_BLEED = 0.25
OUTSIDE_MIN_BLEED = 0.375


class GeometryError(ValueError):
    """A geometry request KDP would reject."""


def parse_trim(trim: str) -> tuple[float, float]:
    """Accept a named standard trim or a literal WIDTHxHEIGHT in inches."""
    key = trim.strip().lower().replace(" ", "").replace('"', "").replace("in", "")
    if key in KDP_STANDARD_TRIMS:
        w, h, _ = KDP_STANDARD_TRIMS[key]
        return w, h
    if "x" not in key:
        raise GeometryError(
            f"cannot read trim {trim!r}: expected a standard name such as '6x9' "
            f"or a literal 'WIDTHxHEIGHT' in inches"
        )
    try:
        w, h = (float(part) for part in key.split("x", 1))
    except ValueError:
        raise GeometryError(f"cannot read trim {trim!r} as two numbers") from None
    return w, h


def is_standard(trim_w: float, trim_h: float, tol: float = 0.01) -> str | None:
    """Return the standard trim's key, or None if this size is non-standard."""
    for key, (w, h, _) in KDP_STANDARD_TRIMS.items():
        if abs(w - trim_w) < tol and abs(h - trim_h) < tol:
            return key
    return None


def page_limits(paper: str, trim: str = DEFAULT_TRIM) -> tuple[int, int] | None:
    """Return the KDP US paperback page limits for a paper and trim.

    None means the combination is unavailable or its limit is not modelled for
    this non-standard trim. validate() distinguishes the known unavailable case.
    """
    if paper not in STANDARD_PAGE_LIMITS:
        raise GeometryError(
            f"unknown paper {paper!r}; one of {', '.join(STANDARD_PAGE_LIMITS)}"
        )

    trim_w, trim_h = parse_trim(trim)
    for key, limits_by_paper in PAGE_LIMIT_OVERRIDES.items():
        override_w, override_h = parse_trim(key)
        if abs(trim_w - override_w) < 0.01 and abs(trim_h - override_h) < 0.01:
            return limits_by_paper[paper]

    if is_standard(trim_w, trim_h) is None:
        return None
    return STANDARD_PAGE_LIMITS[paper]


def spine_width(pages: int, paper: str = DEFAULT_PAPER) -> float:
    """Spine width in inches. Page count times caliper — no minimum, no rounding."""
    if paper not in PAPER_CALIPER:
        raise GeometryError(
            f"unknown paper {paper!r}; one of {', '.join(PAPER_CALIPER)}"
        )
    return pages * PAPER_CALIPER[paper]


def min_gutter(pages: int) -> float:
    """KDP's minimum inside margin for this extent."""
    for limit, gutter in GUTTER_TIERS:
        if pages <= limit:
            return gutter
    raise GeometryError(
        f"{pages} pages is past KDP's {PAGE_MAX}-page paperback limit"
    )


def recommended_margins(trim_w: float, trim_h: float, pages: int,
                        bleed: bool = False) -> dict[str, float]:
    """A margin set that clears KDP's minimums with room to read.

    The minimums are a rejection threshold, not a design. A book set exactly at
    0.375in inside margin is accepted by KDP and still reads badly, because the
    minimum assumes the reader will crack the spine flat. These add a buffer over
    the floor and scale the outside margins with the trim so a 8.5x11 workbook does
    not get a 6x9 book's measure stretched across it.
    """
    gutter = min_gutter(pages) + 0.25
    outer_floor = OUTSIDE_MIN_BLEED if bleed else OUTSIDE_MIN_NO_BLEED
    outer = max(outer_floor + 0.25, round(trim_w * 0.105, 3))
    vertical = max(outer_floor + 0.25, round(trim_h * 0.075, 3))
    return {
        "inside": round(gutter, 3),
        "outside": round(outer, 3),
        "top": round(vertical, 3),
        "bottom": round(vertical + 0.125, 3),
    }


def cover_dimensions(pages: int, trim: str = DEFAULT_TRIM,
                     paper: str = DEFAULT_PAPER) -> dict:
    """Full-wrap cover geometry for a finished interior of `pages` pages."""
    trim_w, trim_h = parse_trim(trim)
    spine = spine_width(pages, paper)

    wrap_w = BLEED + trim_w + spine + trim_w + BLEED
    wrap_h = BLEED + trim_h + BLEED

    fold_1 = BLEED + trim_w          # back cover -> spine, from the wrap's left edge
    fold_2 = fold_1 + spine          # spine -> front cover

    spine_band = spine - 2 * SPINE_TEXT_CLEARANCE
    spine_text_ok = pages >= SPINE_TEXT_MIN_PAGES and spine_band >= 0.0625

    return {
        "pages": pages,
        "trim": {"w": trim_w, "h": trim_h, "standard": is_standard(trim_w, trim_h)},
        "paper": paper,
        "caliper": PAPER_CALIPER[paper],
        "bleed": BLEED,
        "spine_in": round(spine, 4),
        "spine_mm": round(spine * 25.4, 2),
        "wrap_in": [round(wrap_w, 4), round(wrap_h, 4)],
        "wrap_px_300dpi": [round(wrap_w * 300), round(wrap_h * 300)],
        "fold_lines_in": [round(fold_1, 4), round(fold_2, 4)],
        "front_panel_x_in": round(fold_2, 4),
        "back_panel_x_in": round(BLEED, 4),
        "spine_text": {
            "printable": spine_text_ok,
            "usable_band_in": round(max(spine_band, 0.0), 4),
            "clearance_in": SPINE_TEXT_CLEARANCE,
            "reason": (
                None if spine_text_ok
                else f"under {SPINE_TEXT_MIN_PAGES} pages — KDP prints no spine text"
                if pages < SPINE_TEXT_MIN_PAGES
                else "spine too narrow to hold type after clearance"
            ),
        },
        "safe_zone_in": SAFE_ZONE,
    }


def interior_geometry(pages: int, trim: str = DEFAULT_TRIM,
                      bleed: bool = False, paper: str = DEFAULT_PAPER) -> dict:
    """Interior page geometry, including the page size to hand Typst."""
    trim_w, trim_h = parse_trim(trim)
    margins = recommended_margins(trim_w, trim_h, pages, bleed)

    # With bleed the FILE is larger than the trim: 0.125in on top, bottom and the
    # outer edge only. Never on the gutter edge — that edge is bound, not trimmed.
    page_w = trim_w + BLEED if bleed else trim_w
    page_h = trim_h + 2 * BLEED if bleed else trim_h

    limits = page_limits(paper, trim)
    return {
        "pages": pages,
        "trim": {"w": trim_w, "h": trim_h, "standard": is_standard(trim_w, trim_h)},
        "paper": paper,
        "page_limits": list(limits) if limits else None,
        "bleed": bleed,
        "page_size_in": [round(page_w, 4), round(page_h, 4)],
        "margins_in": margins,
        "min_gutter_in": min_gutter(pages),
        "measure_in": round(trim_w - margins["inside"] - margins["outside"], 4),
        "even_pages": pages % 2 == 0,
        "within_page_limits": (limits[0] <= pages <= limits[1]) if limits else None,
    }


def validate(pages: int, trim: str = DEFAULT_TRIM, paper: str = DEFAULT_PAPER,
             bleed: bool = False) -> list[str]:
    """Every reason KDP would reject this combination. Empty list means clean."""
    problems: list[str] = []
    trim_w, trim_h = parse_trim(trim)

    if is_standard(trim_w, trim_h) is None:
        problems.append(
            f"{trim_w} x {trim_h}in is not a KDP standard trim — it will still print, "
            f"but expanded distribution and some marketplaces may refuse it"
        )
    limits = page_limits(paper, trim)
    if limits is None:
        if (paper == "standard-colour" and abs(trim_w - 8.27) < 0.01
                and abs(trim_h - 11.69) < 0.01):
            problems.append(
                "standard colour ink is not available for the 8.27 x 11.69in A4 trim"
            )
        else:
            problems.append(
                f"page-count limit is not modelled for non-standard trim "
                f"{trim_w} x {trim_h}in; verify the current KDP table before upload"
            )
    else:
        minimum, maximum = limits
        if pages < minimum:
            problems.append(f"{pages} pages is under KDP's {minimum}-page minimum for {paper}")
        if pages > maximum:
            problems.append(f"{pages} pages is over KDP's {maximum}-page maximum for {paper} at {trim}")
    if pages % 2:
        problems.append(f"{pages} pages is odd; KDP interiors need an even leaf count")
    if pages < SPINE_TEXT_MIN_PAGES:
        problems.append(
            f"{pages} pages is under {SPINE_TEXT_MIN_PAGES} — the cover must carry "
            f"no spine text"
        )
    return problems


def is_warning(problem: str) -> bool:
    """Whether a geometry finding is advisory rather than a publishing blocker."""
    return (
        "not a KDP standard trim" in problem
        or "no spine text" in problem
        or "page-count limit is not modelled" in problem
    )


def _report(pages: int, trim: str, paper: str, bleed: bool) -> None:
    cover = cover_dimensions(pages, trim, paper)
    inner = interior_geometry(pages, trim, bleed, paper)
    tw, th = cover["trim"]["w"], cover["trim"]["h"]
    std = cover["trim"]["standard"]

    print(f"\n=== {pages} pages, {tw} x {th}in, {paper} ===")
    print(f"  trim               {'STANDARD (' + std + ')' if std else 'NON-STANDARD'}")
    print(f"  interior page      {inner['page_size_in'][0]} x {inner['page_size_in'][1]} in"
          f"{' (with bleed)' if bleed else ' (no bleed)'}")
    m = inner["margins_in"]
    print(f"  margins            inside {m['inside']}  outside {m['outside']}  "
          f"top {m['top']}  bottom {m['bottom']} in")
    print(f"  KDP min gutter     {inner['min_gutter_in']} in at this extent")
    print(f"  measure            {inner['measure_in']} in")
    print(f"  spine              {cover['spine_in']} in ({cover['spine_mm']} mm)")
    print(f"  full wrap          {cover['wrap_in'][0]} x {cover['wrap_in'][1]} in "
          f"({cover['wrap_px_300dpi'][0]} x {cover['wrap_px_300dpi'][1]} px @ 300dpi)")
    print(f"  fold lines         {cover['fold_lines_in'][0]} in and "
          f"{cover['fold_lines_in'][1]} in from the wrap's left edge")
    st = cover["spine_text"]
    print(f"  spine text         {st['usable_band_in']} in usable"
          if st["printable"] else f"  spine text         NOT PRINTABLE — {st['reason']}")

    for problem in validate(pages, trim, paper, bleed):
        level = "WARN" if is_warning(problem) else "!!"
        print(f"  {level} {problem}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--pages", type=int, help="finished interior leaf count")
    ap.add_argument("--trim", default=DEFAULT_TRIM,
                    help=f"standard name or WIDTHxHEIGHT (default {DEFAULT_TRIM})")
    ap.add_argument("--paper", default=DEFAULT_PAPER,
                    choices=sorted(PAPER_CALIPER), help=f"default {DEFAULT_PAPER}")
    ap.add_argument("--bleed", action="store_true", help="interior runs art to the edge")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--list-trims", action="store_true",
                    help="print the standard trim table and exit")
    args = ap.parse_args()

    if args.list_trims:
        if args.json:
            print(json.dumps(
                {k: {"w": w, "h": h, "metric": cm, "note": TRIM_NOTES.get(k, "")}
                 for k, (w, h, cm) in KDP_STANDARD_TRIMS.items()}, indent=2))
        else:
            print("\nKDP STANDARD PAPERBACK TRIM SIZES (verified 2026-08-12)\n")
            for k, (w, h, cm) in KDP_STANDARD_TRIMS.items():
                mark = " <- default" if k == DEFAULT_TRIM else ""
                print(f"  {k:<12} {w} x {h} in   {cm:<18}{mark}")
                print(f"  {'':<12} {TRIM_NOTES.get(k, '')}\n")
        return 0

    if args.pages is None:
        ap.error("--pages is required (or use --list-trims)")

    if args.json:
        print(json.dumps({
            "cover": cover_dimensions(args.pages, args.trim, args.paper),
            "interior": interior_geometry(args.pages, args.trim, args.bleed, args.paper),
            "problems": validate(args.pages, args.trim, args.paper, args.bleed),
        }, indent=2))
        return 0

    _report(args.pages, args.trim, args.paper, args.bleed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
