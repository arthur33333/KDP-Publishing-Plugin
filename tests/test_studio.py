"""Unit tests for the standalone local KDP Publishing Studio."""
import base64
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "studio"))
import server


class ManuscriptConversionTests(unittest.TestCase):
    def test_markdown_headings_and_paragraphs(self):
        items = server.plain_paragraphs("# Chapter one\n\nA paragraph.\n## Section\n- A list item")
        self.assertEqual(items, [
            (1, "Chapter one"),
            (0, "A paragraph."),
            (2, "Section"),
            (0, "• A list item"),
        ])

    def test_typst_output_escapes_special_characters_as_data(self):
        output = server.make_typst([(1, "A #title $100"), (0, 'Quote " and slash \\')])
        self.assertIn('#heading(level: 1)[#text("A #title $100")]', output)
        self.assertIn(r'Quote \\" and slash \\\\', output)

    def test_docx_extracts_headings_and_text(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
          <w:body>
            <w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Chapter</w:t></w:r></w:p>
            <w:p><w:r><w:t>Body text</w:t></w:r><w:r><w:tab/><w:t>continued</w:t></w:r></w:p>
          </w:body>
        </w:document>"""
        with tempfile.TemporaryDirectory() as tmp:
            docx = Path(tmp) / "sample.docx"
            with zipfile.ZipFile(docx, "w") as archive:
                archive.writestr("word/document.xml", xml)
            items = server.docx_paragraphs(docx.read_bytes())
        self.assertEqual(items, [(1, "Chapter"), (0, "Body text    continued")])

    def test_empty_manuscript_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "aucun paragraphe"):
            server.make_typst([])


class ProjectCreationTests(unittest.TestCase):
    def test_create_project_scaffolds_templates_and_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            payload = {
                "title": "Mon livre de test",
                "author": "Auteur Test",
                "subtitle": "Sous-titre",
                "filename": "manuscrit.txt",
                "file_base64": base64.b64encode(b"# Chapitre 1\nUn paragraphe.").decode("ascii"),
                "trim": "6x9",
                "paper": "cream-bw",
                "bleed": False,
                "toc": True,
                "description": "Description de test.",
            }
            with patch.object(Path, "home", return_value=home):
                result = server.new_project(payload)
            project = Path(result["project"])
            self.assertTrue((project / "book.toml").is_file())
            self.assertTrue((project / "templates" / "interior.typ").is_file())
            self.assertTrue((project / "templates" / "cover.typ").is_file())
            self.assertIn('title = "Mon livre de test"', (project / "book.toml").read_text(encoding="utf-8"))
            self.assertIn("#heading(level: 1)", (project / "manuscript" / "body.typ").read_text(encoding="utf-8"))
            self.assertEqual((project / "listing" / "description.txt").read_text(encoding="utf-8"), "Description de test.")
            self.assertEqual(result["paragraphs"], 2)

    def test_rejects_unsupported_file_type(self):
        with self.assertRaisesRegex(ValueError, "Formats acceptés"):
            server.new_project({"title": "x", "author": "y", "filename": "book.pdf"})

    def test_rejects_missing_title_or_author(self):
        with self.assertRaisesRegex(ValueError, "obligatoires"):
            server.new_project({"title": "", "author": "Auteur", "filename": "book.txt"})


if __name__ == "__main__":
    unittest.main()
