#!/usr/bin/env python3
"""Conservative manuscript lint checks for a KDP Typst project.

Reads the configured [paths].body source. It never edits the manuscript or
claims to judge writing quality. Findings are warnings unless --strict is used.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kdp_project as proj  # noqa: E402

HEADING_RE = re.compile(r"^\s*(=+)\s+(.+?)\s*$")
IMAGE_RE = re.compile(r'\bimage\s*\(\s*(?:path\s*:\s*)?"([^"]+)"')
PLACEHOLDER_RE = re.compile(
    r"\b(?:TODO|FIXME|TBD|TK)\b|lorem\s+ipsum|your\s+text\s+here|"
    r"\[\s*insert\b",
    re.IGNORECASE,
)


def strip_typst_comments(source: str) -> str:
    """Remove line and nested block comments while preserving strings and line numbers."""
    output: list[str] = []
    index = 0
    block_depth = 0
    in_string = False
    escaped = False
    in_line_comment = False

    while index < len(source):
        char = source[index]
        nxt = source[index + 1] if index + 1 < len(source) else ""

        if in_line_comment:
            if char == "\n":
                in_line_comment = False
                output.append(char)
            else:
                output.append(" ")
            index += 1
            continue

        if block_depth:
            if char == "/" and nxt == "*":
                block_depth += 1
                output.extend((" ", " "))
                index += 2
            elif char == "*" and nxt == "/":
                block_depth -= 1
                output.extend((" ", " "))
                index += 2
            else:
                output.append("\n" if char == "\n" else " ")
                index += 1
            continue

        if in_string:
            output.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            index += 1
            continue

        if char == "/" and nxt == "/":
            in_line_comment = True
            output.extend((" ", " "))
            index += 2
        elif char == "/" and nxt == "*":
            block_depth = 1
            output.extend((" ", " "))
            index += 2
        else:
            output.append(char)
            if char == '"':
                in_string = True
            index += 1

    return "".join(output)


def source_files(body: Path) -> list[Path]:
    """Return manuscript Typst files in a stable order."""
    if body.is_file():
        return [body] if body.suffix.lower() == ".typ" else []
    if body.is_dir():
        return sorted(p for p in body.rglob("*.typ") if p.is_file())
    return []


def analyze_file(path: Path, display_root: Path) -> list[dict]:
    """Find likely editorial leftovers and structurally empty/duplicate headings."""
    findings: list[dict] = []
    try:
        source = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError) as err:
        return [{
            "file": str(path.relative_to(display_root)),
            "line": 1,
            "code": "READ_ERROR",
            "message": f"Cannot read manuscript source: {err}",
        }]

    relative = str(path.relative_to(display_root))
    clean_source = strip_typst_comments(source)
    lines = clean_source.splitlines()
    headings: dict[str, list[int]] = defaultdict(list)
    parsed_headings: list[tuple[int, str]] = []

    for number, raw in enumerate(lines, 1):
        stripped = raw.strip()
        if not stripped or stripped.startswith("//"):
            continue

        heading = HEADING_RE.match(raw)
        if heading:
            title = heading.group(2).strip()
            parsed_headings.append((number, title))
            headings[title.casefold()].append(number)

        if PLACEHOLDER_RE.search(raw):
            findings.append({
                "file": relative,
                "line": number,
                "code": "PLACEHOLDER",
                "message": "Possible draft placeholder or editorial note remains.",
            })

    # Scan the complete comment-stripped source so a function call split over
    # multiple lines is still checked. A leading slash is Typst-root-relative.
    for image_match in IMAGE_RE.finditer(clean_source):
        image_name = image_match.group(1)
        line_number = clean_source.count("\n", 0, image_match.start()) + 1
        if re.match(r"^[A-Za-z]:[\\/]", image_name):
            findings.append({
                "file": relative,
                "line": line_number,
                "code": "NON_PORTABLE_IMAGE_PATH",
                "message": f"Image path '{image_name}' is an absolute Windows path; use a project-relative path.",
            })
            continue
        if image_name.startswith("/"):
            image_path = display_root / image_name.lstrip("/\\")
        else:
            image_path = path.parent / image_name
        try:
            image_display = str(image_path.relative_to(display_root))
        except ValueError:
            image_display = str(image_path)
        if not image_path.is_file():
            findings.append({
                "file": relative,
                "line": line_number,
                "code": "MISSING_IMAGE",
                "message": f"Image file '{image_name}' was not found at {image_display}.",
            })

    # A heading immediately followed by another heading (or end of file) is
    # suspicious, but may be intentional, so it is reported as a warning only.
    for index, (line_number, title) in enumerate(parsed_headings):
        next_line = (parsed_headings[index + 1][0]
                     if index + 1 < len(parsed_headings) else len(lines) + 1)
        has_body = any(
            lines[pos - 1].strip() and not lines[pos - 1].lstrip().startswith("//")
            and not HEADING_RE.match(lines[pos - 1])
            for pos in range(line_number + 1, next_line)
        )
        if not has_body:
            findings.append({
                "file": relative,
                "line": line_number,
                "code": "EMPTY_SECTION",
                "message": f"Heading '{title}' has no visible source content before the next heading.",
            })

    for title, locations in headings.items():
        if len(locations) > 1:
            display_title = next(
                title_text for _, title_text in parsed_headings
                if title_text.casefold() == title
            )
            findings.append({
                "file": relative,
                "line": locations[1],
                "code": "DUPLICATE_HEADING",
                "message": f"Heading '{display_title}' appears {len(locations)} times in this file.",
            })

    return findings


def structure_summary(files: list[Path]) -> dict:
    """Count Typst heading levels without assuming every level-one heading is a chapter."""
    counts = {"top_level_headings": 0, "section_headings": 0, "subheadings": 0}
    for path in files:
        try:
            lines = strip_typst_comments(path.read_text(encoding="utf-8-sig")).splitlines()
        except (OSError, UnicodeError):
            continue
        for raw in lines:
            if raw.strip().startswith("//"):
                continue
            match = HEADING_RE.match(raw)
            if not match:
                continue
            level = len(match.group(1))
            if level == 1:
                counts["top_level_headings"] += 1
            elif level == 2:
                counts["section_headings"] += 1
            else:
                counts["subheadings"] += 1
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--project", type=Path, default=None,
                        help="book project directory (defaults to current/parent directory)")
    parser.add_argument("--strict", action="store_true",
                        help="exit with status 1 when warnings are found")
    parser.add_argument("--json", action="store_true",
                        help="print machine-readable findings")
    args = parser.parse_args()

    try:
        cfg = proj.load(proj.find_project(args.project))
    except (proj.ProjectError, OSError, ValueError) as err:
        print(f"! {err}", file=sys.stderr)
        return 2

    root = cfg["root"]
    body = root / cfg["paths"]["body"]
    files = source_files(body)
    if not files:
        print(
            f"! no .typ manuscript source found at {body.relative_to(root)} "
            "(check [paths].body in book.toml)",
            file=sys.stderr,
        )
        return 2

    findings: list[dict] = []
    for path in files:
        findings.extend(analyze_file(path, root))

    structure = structure_summary(files)
    if args.json:
        print(json.dumps({
            "project": str(root),
            "files_scanned": len(files),
            "structure": structure,
            "warning_count": len(findings),
            "findings": findings,
        }, indent=2, ensure_ascii=False))
    else:
        print(f"Manuscript review: {len(files)} source file(s)")
        print(
            "Structure: "
            f"{structure['top_level_headings']} top-level heading(s), "
            f"{structure['section_headings']} section(s), "
            f"{structure['subheadings']} subheading(s)."
        )
        if not findings:
            print("PASS  No common placeholders, empty sections or duplicate headings found.")
        else:
            for item in findings:
                print(f"WARN  {item['file']}:{item['line']} [{item['code']}] {item['message']}")
            print(f"\n{len(findings)} warning(s). Review them manually; some may be intentional.")

    return 1 if findings and args.strict else 0


if __name__ == "__main__":
    raise SystemExit(main())
