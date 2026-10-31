"""Tests for the conservative manuscript source review."""

import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "analyze_manuscript", ROOT / "scripts" / "analyze-manuscript.py"
)
review = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(review)


class ManuscriptReviewTests(unittest.TestCase):
    def analyze(self, source: str):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manuscript = root / "body.typ"
            manuscript.write_text(source, encoding="utf-8")
            return review.analyze_file(manuscript, root)

    def test_detects_common_placeholders(self):
        findings = self.analyze("= Chapter One\nTODO: finish this section\n")
        self.assertIn("PLACEHOLDER", [item["code"] for item in findings])

    def test_detects_empty_heading_section(self):
        findings = self.analyze("= Chapter One\n\n= Chapter Two\nText here.\n")
        self.assertTrue(any(item["code"] == "EMPTY_SECTION" for item in findings))

    def test_detects_duplicate_heading_in_same_file(self):
        findings = self.analyze("= Introduction\nFirst text.\n\n= introduction\nSecond text.\n")
        self.assertTrue(any(item["code"] == "DUPLICATE_HEADING" for item in findings))

    def test_ignores_comments_and_normal_prose(self):
        findings = self.analyze(
            "// TODO: this is only a comment\n"
            "= Chapter One\n"
            "This is ordinary manuscript text.\n"
        )
        self.assertEqual(findings, [])

    def test_detects_missing_literal_image_path(self):
        findings = self.analyze('= Chapter One\\n#image("images/missing.png")\\nText\\n')
        self.assertIn("MISSING_IMAGE", [item["code"] for item in findings])

    def test_existing_image_is_not_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "images").mkdir()
            (root / "images" / "cover.png").write_bytes(b"test image")
            source = root / "body.typ"
            source.write_text('= Chapter One\\n#image("images/cover.png")\\nText\\n', encoding="utf-8")
            findings = review.analyze_file(source, root)
            self.assertNotIn("MISSING_IMAGE", [item["code"] for item in findings])

    def test_reports_heading_hierarchy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "body.typ"
            source.write_text("= Chapter One\\n== Section\\n=== Subsection\\n", encoding="utf-8")
            self.assertEqual(review.structure_summary([source]), {
                "top_level_headings": 1,
                "section_headings": 1,
                "subheadings": 1,
            })

    def test_directory_finds_typst_sources_recursively(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "chapters").mkdir()
            (root / "chapters" / "one.typ").write_text("= One\nText\n", encoding="utf-8")
            (root / "notes.txt").write_text("not Typst", encoding="utf-8")
            self.assertEqual(
                [p.name for p in review.source_files(root / "chapters")],
                ["one.typ"],
            )


if __name__ == "__main__":
    unittest.main()
