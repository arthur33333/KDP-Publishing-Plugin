#!/usr/bin/env python3
"""End-to-end Typst smoke test for interior, cover, preflight and packaging."""

from __future__ import annotations

import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import kdp_geometry as geo
import kdp_project as project


def run(command: list[str], *, cwd: Path) -> str:
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(
            f"Command failed ({result.returncode}): {' '.join(command)}\n"
            f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
    return result.stdout


def png_chunk(kind: bytes, data: bytes) -> bytes:
    return (struct.pack(">I", len(data)) + kind + data
            + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF))


def write_test_png(path: Path) -> None:
    """Write a tiny valid RGB PNG without adding a Pillow dependency."""
    width = height = 4
    rows = b"".join(b"\x00" + bytes((35, 110, 180) * width) for _ in range(height))
    payload = (
        b"\x89PNG\r\n\x1a\n"
        + png_chunk(b"IHDR", struct.pack(">2I5B", width, height, 8, 2, 0, 0, 0))
        + png_chunk(b"IDAT", zlib.compress(rows))
        + png_chunk(b"IEND", b"")
    )
    path.write_bytes(payload)


def main() -> int:
    if not shutil.which("typst"):
        raise RuntimeError("Typst is not installed or is not on PATH.")
    for tool in ("pdfinfo", "pdftotext", "pdffonts"):
        if not shutil.which(tool):
            raise RuntimeError(f"{tool} is required for the end-to-end smoke test.")

    with tempfile.TemporaryDirectory(prefix="kdp-plugin-smoke-") as temporary:
        root = Path(temporary)
        for directory in ("templates", "manuscript/assets", "listing", "dist"):
            (root / directory).mkdir(parents=True, exist_ok=True)

        shutil.copy2(ROOT / "templates" / "interior.typ", root / "templates" / "interior.typ")
        shutil.copy2(ROOT / "templates" / "cover.typ", root / "templates" / "cover.typ")
        write_test_png(root / "manuscript" / "assets" / "sample.png")

        (root / "dist" / "book.json").write_text(json.dumps({
            "title": "KDP Smoke Test",
            "title_lines": ["KDP Smoke Test"],
            "subtitle": "",
            "author": "Test Author",
            "contributors": [],
            "blurb": "A local build test for the KDP publishing pipeline.",
        }), encoding="utf-8")

        body = """= Chapter One
This chapter is included to verify automatic contents generation.

== Section One
This section verifies the level-two outline entry.

#figure(
  image("assets/sample.png", width: 70%, fit: "contain", alt: "Blue sample square"),
  caption: [Sample figure],
)

#for i in range(1100) {
  [This is a generated paragraph used only by the automated smoke test. It forces the interior to exceed the minimum paperback page count and exercises pagination, margins, and the final cover spine calculation.]
  parbreak()
}
"""
        (root / "manuscript" / "body.typ").write_text(body, encoding="utf-8")
        (root / "listing" / "description.txt").write_text(
            "A smoke-test description for a sample paperback project.\n",
            encoding="utf-8",
        )
        (root / "book.toml").write_text("""[book]
title = "KDP Smoke Test"
title_lines = ["KDP Smoke Test"]
subtitle = ""
author = "Test Author"
contributors = []

[print]
trim = "6x9"
paper = "cream-bw"
bleed = false
cover_finish = "matte"
fonts = ["Libertinus"]

[paths]
body = "manuscript/body.typ"
interior_template = "templates/interior.typ"
cover_template = "templates/cover.typ"
fonts = "assets/fonts"
description = "listing/description.txt"
dist = "dist"

[interior]
table_of_contents = true

[listing]
keywords = ["sample paperback"]
categories = ["Reference"]
""", encoding="utf-8")

        # The manuscript scanner must resolve the relative image path and find
        # no warnings in this intentionally clean fixture.
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "smoke_analyzer", ROOT / "scripts" / "analyze-manuscript.py"
        )
        analyzer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(analyzer)
        findings = analyzer.analyze_file(root / "manuscript" / "body.typ", root)
        if findings:
            raise RuntimeError(f"Unexpected manuscript findings: {findings}")

        run([sys.executable, str(ROOT / "scripts" / "build-interior.py"),
             "--project", str(root)], cwd=ROOT)
        interior = root / "dist" / "interior.pdf"
        width, height, pages = project.page_geometry(interior)
        if pages < geo.PAGE_MIN or pages % 2:
            raise RuntimeError(f"Interior has invalid page count: {pages}")
        if abs(width / project.PT - 6.0) > 0.02 or abs(height / project.PT - 9.0) > 0.02:
            raise RuntimeError(f"Unexpected interior size: {width / 72} x {height / 72} in")

        extracted = run(["pdftotext", str(interior), "-"], cwd=ROOT)
        for expected in ("Contents", "Chapter One", "Section One", "Sample figure"):
            if expected not in extracted:
                raise RuntimeError(f"Interior PDF text is missing {expected!r}")

        run([sys.executable, str(ROOT / "scripts" / "build-cover.py"),
             "--project", str(root)], cwd=ROOT)
        cover = root / "dist" / "cover.pdf"
        cover_width, cover_height, cover_pages = project.page_geometry(cover)
        expected_cover = geo.cover_dimensions(pages, "6x9", "cream-bw")
        if cover_pages != 1:
            raise RuntimeError(f"Cover must be one page, got {cover_pages}")
        if abs(cover_width / project.PT - expected_cover["wrap_in"][0]) > 0.02:
            raise RuntimeError("Cover width does not match the calculated wrap.")
        if abs(cover_height / project.PT - expected_cover["wrap_in"][1]) > 0.02:
            raise RuntimeError("Cover height does not match the calculated wrap.")

        run([sys.executable, str(ROOT / "scripts" / "preflight.py"),
             "--project", str(root)], cwd=ROOT)
        package = root / "dist" / "kdp-upload"
        package.mkdir(parents=True, exist_ok=True)
        (package / "obsolete-stale-cover.pdf").write_text("stale", encoding="utf-8")
        run([sys.executable, str(ROOT / "scripts" / "kdp-package.py"),
             "--project", str(root)], cwd=ROOT)
        required = {
            "description.txt", "title.txt", "specs.txt", "README.txt",
            "listing-review.txt",
        }
        missing = sorted(name for name in required if not (package / name).is_file())
        if missing:
            raise RuntimeError(f"Upload package is missing files: {missing}")
        if (package / "obsolete-stale-cover.pdf").exists():
            raise RuntimeError("The upload package retained a stale file from a previous build.")
        if not any(path.name.endswith("-interior.pdf") for path in package.iterdir()):
            raise RuntimeError("Upload package is missing the interior PDF.")
        if not any(path.name.endswith("-cover.pdf") for path in package.iterdir()):
            raise RuntimeError("Upload package is missing the cover PDF.")

        print(
            f"PASS  Typst interior + image + contents + pagination + cover + "
            f"preflight + upload package ({pages} interior pages)"
        )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"FAIL  {error}", file=sys.stderr)
        raise SystemExit(1)
