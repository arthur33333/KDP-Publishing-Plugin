#!/usr/bin/env python3
"""Locate and load a book project's `book.toml`, and read geometry back out of PDFs.

`book.toml` is the single source of the book's identity and print settings. Every
script in this plugin reads it rather than taking the same values on the command
line, because a title typed twice is a title that will eventually differ — and KDP
locks the title field 72 hours after publication and requires it to read exactly as
the cover prints it.

Not a CLI. Imported by build-interior.py, build-cover.py, preflight.py and
kdp-package.py.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tomllib
from pathlib import Path

PT = 72.0

# A page object, not the /Pages tree node. The negative-ish `[^s]` is what keeps
# `/Type /Pages` from being counted as a page.
_PAGE_RE = re.compile(rb"/Type\s*/Page[^s]")


class ProjectError(RuntimeError):
    """The project is not laid out the way the scripts expect."""


def find_project(start: Path | None = None) -> Path:
    """Walk up from `start` to the nearest directory holding a book.toml."""
    here = (start or Path.cwd()).resolve()
    for candidate in (here, *here.parents):
        if (candidate / "book.toml").is_file():
            return candidate
    raise ProjectError(
        "no book.toml found in this directory or any parent. Run /kdp-init to "
        "scaffold a book project, or cd into one."
    )


def load(root: Path | None = None) -> dict:
    """Load book.toml, apply defaults, and check the internal consistency of it."""
    root = root or find_project()
    with (root / "book.toml").open("rb") as fh:
        cfg = tomllib.load(fh)

    cfg.setdefault("book", {})
    cfg.setdefault("print", {})
    cfg.setdefault("listing", {})
    cfg.setdefault("paths", {})

    book, printing, paths = cfg["book"], cfg["print"], cfg["paths"]

    for required in ("title", "author"):
        if not book.get(required):
            raise ProjectError(f"book.toml: [book].{required} is required")

    printing.setdefault("trim", "6x9")
    printing.setdefault("paper", "cream-bw")
    printing.setdefault("bleed", False)
    printing.setdefault("cover_finish", "matte")

    paths.setdefault("dist", "dist")
    paths.setdefault("body", "manuscript/body.typ")
    paths.setdefault("interior_template", "templates/interior.typ")
    paths.setdefault("cover_template", "templates/cover.typ")
    paths.setdefault("fonts", "assets/fonts")
    paths.setdefault("description", "listing/description.txt")

    # The cover and the title page break the title across lines; the KDP form takes
    # it as one string. Both have to be the same title, and the only way to know
    # that is to join the display lines back up and compare.
    lines = book.get("title_lines")
    if lines:
        joined = " ".join(lines)
        if joined != book["title"]:
            raise ProjectError(
                f"book.toml: title_lines join to {joined!r} but title is "
                f"{book['title']!r} — these must be the same string"
            )
    else:
        book["title_lines"] = [book["title"]]

    book.setdefault("subtitle", "")
    book.setdefault("contributors", [])

    cfg["root"] = root
    cfg["dist"] = root / paths["dist"]
    return cfg


def write_book_json(cfg: dict) -> str:
    """Dump the book's identity to `<dist>/book.json` for the templates to read.

    THE TEMPLATES DO NOT HARDCODE THE TITLE. They read this file, which is
    generated from book.toml on every build, so the cover, the title page and the
    KDP listing all derive from one string and cannot drift into three
    near-misses. That matters because KDP locks the title field 72 hours after
    publication and requires it to read exactly as the cover prints it.

    Values arrive in Typst as strings rather than as markup, because `json()`
    parses them as data. So a title containing `#`, `$`, `*`, `_`, `@` or a
    backslash renders literally with no escaping, hand-rolled or otherwise. That
    is the point of routing through JSON rather than interpolating into source.

    Returns the root-relative path to pass to Typst, which resolves a leading `/`
    against `--root` rather than against the template's own directory.
    """
    import json

    book = cfg["book"]
    dist = cfg["dist"]
    dist.mkdir(parents=True, exist_ok=True)

    payload = {
        "title": book["title"],
        "title_lines": book["title_lines"],
        "subtitle": book.get("subtitle", ""),
        "author": book["author"],
        "contributors": book.get("contributors", []),
        "blurb": _blurb(cfg),
    }
    (dist / "book.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    return "/" + str((dist / "book.json").relative_to(cfg["root"])).replace("\\", "/")


def _blurb(cfg: dict) -> str:
    """Back-cover copy: the listing description, if the project has one.

    Not authored here and not generated. If there is no description file there is
    no blurb, and the cover template leaves the back panel empty rather than
    inventing something to fill it.
    """
    path = cfg["root"] / cfg["paths"]["description"]
    if path.is_file():
        return path.read_text(encoding="utf-8").strip()
    return ""


def page_geometry(pdf: Path) -> tuple[float, float, int]:
    """(width_pt, height_pt, page_count) read out of the PDF itself.

    Read, never assumed. A page count carried forward from the last build is the
    single most common way to end up with a cover whose spine text sits on the
    front face — the spine width is a function of this number, so it has to come
    from the artifact rather than from anyone's memory of it.

    pdfinfo is preferred and optional; the fallback parses the first MediaBox and
    counts page objects, which is sufficient for a file this toolchain produced.
    """
    if not pdf.exists():
        raise ProjectError(f"{pdf} does not exist — build it first")

    pdfinfo = shutil.which("pdfinfo")
    if pdfinfo:
        try:
            result = subprocess.run(
                [pdfinfo, str(pdf)],
                capture_output=True,
                text=True,
                errors="replace",
                check=False,
            )
        except OSError as err:
            raise ProjectError(f"could not run pdfinfo for {pdf.name}: {err}") from err

        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip() or "no diagnostic output"
            raise ProjectError(
                f"pdfinfo failed for {pdf.name} (exit {result.returncode}): {detail}"
            )

        size = re.search(r"^Page size:\s+([\d.]+) x ([\d.]+)", result.stdout, re.M)
        pages = re.search(r"^Pages:\s+(\d+)", result.stdout, re.M)
        if not size or not pages:
            raise ProjectError(
                f"pdfinfo could not report page size and page count for {pdf.name}"
            )
        return float(size.group(1)), float(size.group(2)), int(pages.group(1))

    data = pdf.read_bytes()
    box = re.search(
        rb"/MediaBox\s*\[\s*(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)", data)
    if not box:
        raise ProjectError(f"cannot read page geometry from {pdf.name}")
    w = float(box.group(3)) - float(box.group(1))
    h = float(box.group(4)) - float(box.group(2))
    return w, h, len(_PAGE_RE.findall(data))


def typst_compile(src: Path, out: Path, root: Path,
                  inputs: dict[str, str] | None = None,
                  font_path: Path | None = None) -> None:
    """Compile a Typst file, failing loudly.

    --root is the project, not the source file's directory, so a template in
    templates/ can reach assets/ one level up.

    --font-path pins bundled fonts. Without it the build takes whatever happens to
    be installed on the machine, and a book that renders correctly here renders in
    a substituted face at different metrics somewhere else — silently, because
    Typst does not warn about font substitution and exits 0 either way.
    """
    if not shutil.which("typst"):
        raise ProjectError(
            "typst is not on PATH. Install it: https://github.com/typst/typst"
        )
    cmd = ["typst", "compile", "--root", str(root)]
    if font_path and font_path.is_dir():
        cmd += ["--font-path", str(font_path)]
    for key, value in (inputs or {}).items():
        cmd += ["--input", f"{key}={value}"]
    cmd += [str(src), str(out)]

    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise ProjectError(f"typst failed:\n{proc.stderr.strip()}")
