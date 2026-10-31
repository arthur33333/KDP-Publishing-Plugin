#!/usr/bin/env python3
"""Mechanical pre-flight checks on a built book. Exits non-zero on failure.

    python3 preflight.py
    python3 preflight.py --json

Checks everything about a finished PDF pair that a machine can check. The
judgement calls — does the copy read well, does the gutter look right in KDP's
own previewer, do the two CJK glyphs on page 212 look acceptable — are not here
and still need a human. The output says so explicitly rather than implying the
book is clear.

WHY THE FONT PASS NEEDS ITS OWN TOOL, AND IS THE POINT OF THIS SCRIPT.

Typst does not warn when a character has no glyph in the requested font. It falls
back through the system font list, renders the character in whatever face it
found, and exits 0. There is no error, no warning, and nothing anyone would catch
by eye in a few hundred pages. On another machine, with a different set of fonts
installed, the same source produces a different book.

The only reliable signal is to enumerate every codepoint in the source, confirm
each one survives the round trip into the PDF, and list which fonts actually got
embedded so an unexpected substitution is visible before the proof copy is.

Needs poppler-utils: pdfinfo, pdftotext, pdffonts, pdfimages.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import unicodedata
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import kdp_geometry as geo  # noqa: E402
import kdp_project as proj  # noqa: E402
import listing_audit  # noqa: E402

# Source extensions worth reading for a codepoint corpus.
BODY_SUFFIXES = {".typ", ".md", ".txt", ".json", ".yaml", ".yml", ".toml"}


def run(cmd: list[str]) -> str:
    """Run a Poppler command and fail clearly instead of treating errors as empty output."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, errors="replace", check=False
        )
    except OSError as err:
        raise SystemExit(f"! could not run {cmd[0]!r}: {err}") from err

    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "no diagnostic output"
        raise SystemExit(
            f"! {cmd[0]} exited with code {result.returncode}: {detail}"
        )
    return result.stdout


def parse_pdf_image_resolutions(output: str) -> list[dict]:
    """Parse image pixel dimensions and effective PPI from pdfimages -list output."""
    records: list[dict] = []
    for line in output.splitlines():
        parts = line.split()
        if len(parts) < 14 or not parts[0].isdigit() or not parts[1].isdigit():
            continue
        if parts[2] != "image":
            continue
        try:
            records.append({
                "page": int(parts[0]),
                "image": int(parts[1]),
                "width_px": int(parts[3]),
                "height_px": int(parts[4]),
                "x_ppi": float(parts[12]),
                "y_ppi": float(parts[13]),
            })
        except (ValueError, IndexError):
            continue
    return records


def classify_image_resolutions(records: list[dict], label: str,
                               minimum_ppi: float = 300,
                               recommended_max_ppi: float = 600) -> tuple[list[str], list[str]]:
    """Return hard resolution failures and high-resolution advisory warnings."""
    failures: list[str] = []
    warnings: list[str] = []
    for item in records:
        low = min(item["x_ppi"], item["y_ppi"])
        high = max(item["x_ppi"], item["y_ppi"])
        where = f"{label} image {item['image']} on page {item['page']}"
        if low < minimum_ppi:
            failures.append(
                f"{where} is {item['x_ppi']:.0f} x {item['y_ppi']:.0f} PPI; "
                f"KDP requires at least {minimum_ppi:.0f} PPI"
            )
        elif high > recommended_max_ppi:
            warnings.append(
                f"{where} is {item['x_ppi']:.0f} x {item['y_ppi']:.0f} PPI; "
                f"KDP recommends staying at or below {recommended_max_ppi:.0f} PPI "
                "to avoid unnecessarily large PDFs"
            )
    return failures, warnings


def cover_height_mismatch(actual_height_in: float, expected_height_in: float,
                         tolerance: float = 0.02) -> str | None:
    """Return a diagnostic when the cover PDF height differs from its required wrap."""
    if abs(actual_height_in - expected_height_in) <= tolerance:
        return None
    return (
        f"cover height is {actual_height_in:.4f}in but the full wrap needs "
        f"{expected_height_in:.4f}in — check the cover template and rebuild it"
    )


# Running commentary goes to stderr under --json, so stdout stays a single
# parseable document. A tool that prints prose above its JSON is a tool whose
# output cannot be piped, which defeats the point of having a --json flag.
_QUIET = False


def say(*args, **kwargs) -> None:
    kwargs.setdefault("file", sys.stderr if _QUIET else sys.stdout)
    print(*args, **kwargs)


def corpus_from(root: Path, body: str) -> tuple[str, int]:
    """Every character the book's source asks to be typeset."""
    target = root / body
    files: list[Path] = []
    if target.is_dir():
        files = sorted(p for p in target.rglob("*") if p.suffix in BODY_SUFFIXES)
    elif target.is_file():
        files = [target]

    text = []
    for path in files:
        try:
            text.append(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, OSError):
            continue
    return "".join(text), len(files)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--project", type=Path, default=None)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    global _QUIET
    _QUIET = args.json

    try:
        cfg = proj.load(proj.find_project(args.project))
    except proj.ProjectError as err:
        sys.exit(f"! {err}")

    root, dist = cfg["root"], cfg["dist"]
    printing, paths, book = cfg["print"], cfg["paths"], cfg["book"]
    interior = dist / "interior.pdf"
    cover = dist / "cover.pdf"

    if not interior.exists():
        sys.exit("! dist/interior.pdf missing — run build-interior.py first")

    for tool in ("pdftotext", "pdffonts", "pdfimages"):
        if not shutil.which(tool):
            sys.exit(f"! {tool} not on PATH — install poppler-utils")

    failures: list[str] = []
    warnings: list[str] = []
    report: dict = {"title": book["title"]}

    # --- geometry ------------------------------------------------------------
    iw, ih, pages = proj.page_geometry(interior)
    trim_w, trim_h = geo.parse_trim(printing["trim"])
    expected = geo.interior_geometry(pages, printing["trim"], printing["bleed"], printing["paper"])
    want_w, want_h = expected["page_size_in"]

    say(f"title           {book['title']}")
    say(f"extent          {pages} pages, "
          f"{iw / proj.PT:.3f} x {ih / proj.PT:.3f} in")

    if (abs(iw / proj.PT - want_w) > 0.02 or abs(ih / proj.PT - want_h) > 0.02):
        failures.append(
            f"interior renders at {iw / proj.PT:.3f} x {ih / proj.PT:.3f}in but "
            f"book.toml specifies {want_w} x {want_h}in"
        )

    std = geo.is_standard(trim_w, trim_h)
    say(f"trim            {trim_w} x {trim_h} in "
          f"({'standard: ' + std if std else 'NON-STANDARD'})")
    if std is None:
        warnings.append(
            f"{trim_w} x {trim_h}in is not a KDP standard trim — it prints, but "
            f"expanded distribution and some marketplaces may refuse it"
        )

    for problem in geo.validate(pages, printing["trim"], printing["paper"],
                                printing["bleed"]):
        if geo.is_warning(problem):
            warnings.append(problem)
        else:
            failures.append(problem)

    gutter = geo.min_gutter(pages)
    say(f"gutter          {expected['margins_in']['inside']} in inside margin as "
          f"built; KDP's minimum at {pages} pages is {gutter} in")
    if expected["margins_in"]["inside"] < gutter:
        failures.append(
            f"inside margin {expected['margins_in']['inside']}in is under KDP's "
            f"{gutter}in minimum at {pages} pages — text will be swallowed by the bind"
        )
    report["geometry"] = {
        "pages": pages, "trim": [trim_w, trim_h], "standard": std,
        "page_size_in": [round(iw / proj.PT, 4), round(ih / proj.PT, 4)],
        "min_gutter_in": gutter,
    }

    # --- font round trip -----------------------------------------------------
    source, n_files = corpus_from(root, paths["body"])
    if not source:
        warnings.append(
            f"no readable source under [paths].body ({paths['body']}) — the font "
            f"round-trip check could not run, which is the one check that catches "
            f"silent glyph substitution"
        )
        say(f"font round trip SKIPPED — no source found at {paths['body']}")
        report["fonts"] = {"checked": False}
    else:
        chars = Counter(source)
        non_ascii = {c: n for c, n in chars.items() if ord(c) > 127}
        pdf_chars = set(run(["pdftotext", str(interior), "-"]))
        dropped = sorted(
            (c for c in chars
             if c not in pdf_chars and not c.isspace() and ord(c) > 127),
            key=lambda c: -chars[c],
        )

        say(f"codepoints      {len(chars)} distinct across {n_files} source file(s), "
              f"{len(non_ascii)} non-ASCII")
        for c in sorted(non_ascii, key=lambda c: -non_ascii[c])[:20]:
            try:
                name = unicodedata.name(c)
            except ValueError:
                name = "<unnamed>"
            say(f"                U+{ord(c):04X} {non_ascii[c]:>6}x  {c}  {name}")

        if dropped:
            failures.append(
                "codepoint(s) in the source did not survive into the PDF: "
                + ", ".join(f"U+{ord(c):04X} ({c})" for c in dropped[:10])
            )
        say(f"round trip      {'FAIL' if dropped else 'every codepoint reached the PDF'}")

        embedded = [
            line.split()[0].split("+")[-1]
            for line in run(["pdffonts", str(interior)]).splitlines()[2:]
            if line.strip()
        ]
        intended = tuple(printing.get("fonts", []))
        fallbacks = ([f for f in embedded if not any(f.startswith(i) for i in intended)]
                     if intended else [])
        say(f"fonts embedded  {len(set(embedded))}: {', '.join(sorted(set(embedded)))}")
        if fallbacks:
            # Not a failure. Typst's fallback is why there is no tofu on the page.
            # The point is that the substitution is visible and deliberate rather
            # than discovered in a proof copy.
            warnings.append(
                f"font substitution in use: {', '.join(sorted(set(fallbacks)))} — "
                f"check these render acceptably, or add them to [print].fonts"
            )
        report["fonts"] = {
            "checked": True, "distinct_codepoints": len(chars),
            "non_ascii": len(non_ascii), "dropped": [f"U+{ord(c):04X}" for c in dropped],
            "embedded": sorted(set(embedded)), "unexpected": sorted(set(fallbacks)),
        }

    # --- cover against THIS interior ----------------------------------------
    if cover.exists():
        cw, ch, cpages = proj.page_geometry(cover)
        dims = geo.cover_dimensions(pages, printing["trim"], printing["paper"])

        # Derive the spine from the finished wrap rather than recomputing it. This
        # is the second, independent route to the same fact: build-cover.py measured
        # the interior going in, this measures the cover coming out.
        measured_spine = (cw / proj.PT) - 2 * trim_w - 2 * geo.BLEED
        say(f"cover wrap      {cw / proj.PT:.4f} x {ch / proj.PT:.4f} in, "
              f"{cpages} page(s)")
        say(f"cover spine     {measured_spine:.4f} in measured back out of the wrap; "
              f"{pages} pages needs {dims['spine_in']:.4f} in")

        if cpages != 1:
            failures.append(
                f"cover is {cpages} pages — KDP wants back, spine and front as a "
                f"single page"
            )
        if abs(measured_spine - dims["spine_in"]) > 0.01:
            failures.append(
                f"cover spine is {measured_spine:.4f}in but {pages} pages needs "
                f"{dims['spine_in']:.4f}in — this cover is stale, rebuild it"
            )
        height_error = cover_height_mismatch(ch / proj.PT, dims["wrap_in"][1])
        if height_error:
            failures.append(height_error)
        report["cover"] = {
            "wrap_in": [round(cw / proj.PT, 4), round(ch / proj.PT, 4)],
            "measured_spine_in": round(measured_spine, 4),
            "required_spine_in": dims["spine_in"],
        }
    else:
        say("cover           not built yet — build it last, against these "
              f"{pages} pages")
        report["cover"] = None

    # --- image resolution ----------------------------------------------------
    image_reports: dict[str, list[dict]] = {}
    image_pdfs = [("interior", interior)]
    if cover.exists():
        image_pdfs.append(("cover", cover))
    for label, pdf_path in image_pdfs:
        image_records = parse_pdf_image_resolutions(
            run(["pdfimages", "-list", str(pdf_path)])
        )
        image_reports[label] = image_records
        image_failures, image_warnings = classify_image_resolutions(
            image_records, label
        )
        failures.extend(image_failures)
        warnings.extend(image_warnings)
        say(f"{label + ' images':16} {len(image_records)} raster image(s) checked")
    report["images"] = image_reports

    # --- listing -------------------------------------------------------------
    description = root / paths["description"]
    if description.is_file():
        n = len(description.read_text(encoding="utf-8").strip())
        say(f"description     {n:,} of {geo.DESCRIPTION_MAX:,} characters")
        if n > geo.DESCRIPTION_MAX:
            failures.append(
                f"description is {n:,} characters, over KDP's "
                f"{geo.DESCRIPTION_MAX:,} by {n - geo.DESCRIPTION_MAX:,}"
            )
        report["description_chars"] = n

    listing = cfg["listing"]
    keywords, categories = listing.get("keywords", []), listing.get("categories", [])
    if len(keywords) > geo.KEYWORDS_MAX:
        failures.append(f"{len(keywords)} keywords; KDP takes {geo.KEYWORDS_MAX}")
    if len(categories) > geo.CATEGORIES_MAX:
        failures.append(f"{len(categories)} categories; KDP takes {geo.CATEGORIES_MAX}")
    if any('"' in k for k in keywords):
        failures.append(
            'a keyword contains a quotation mark — KDP treats the quoted phrase as '
            'an exact match and the book stops surfacing for anything less than all '
            'of it'
        )

    listing_warnings = listing_audit.audit_listing(
        description.read_text(encoding="utf-8") if description.is_file() else "",
        keywords,
        categories,
    )
    warnings.extend(listing_warnings)
    report["listing"] = {
        "keyword_count": len(keywords),
        "category_count": len(categories),
        "audit_warnings": listing_warnings,
    }

    # --- verdict -------------------------------------------------------------
    report["failures"], report["warnings"] = failures, warnings

    if args.json:
        print(json.dumps(report, indent=2))
        return 1 if failures else 0

    print()
    for w in warnings:
        print(f"WARN  {w}")
    for f in failures:
        print(f"FAIL  {f}")
    if failures:
        return 1

    print("PASS  every mechanical check.")
    print()
    print("Still needs a human, and no script can do these:")
    print("  - read the KDP previewer page by page; it is the only thing that shows")
    print("    what the press will do with the gutter")
    print("  - confirm the gutter against KDP's CURRENT minimum; reference/margins.md")
    print("    was verified on a date, and KDP moves these without notice")
    print("  - look at any font substitution listed above in a proof copy")
    print("  - order the proof copy and read it")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
