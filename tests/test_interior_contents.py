"""Tests for the generated interior contents page configuration."""

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "build_interior", ROOT / "scripts" / "build-interior.py"
)
builder = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(builder)


class InteriorContentsTests(unittest.TestCase):
    def test_contents_page_is_enabled_for_existing_manifests_by_default(self):
        self.assertTrue(builder.table_of_contents_enabled({}))

    def test_contents_page_can_be_disabled(self):
        self.assertFalse(builder.table_of_contents_enabled({
            "interior": {"table_of_contents": False}
        }))

    def test_contents_setting_must_be_boolean(self):
        with self.assertRaises(builder.proj.ProjectError):
            builder.table_of_contents_enabled({
                "interior": {"table_of_contents": "false"}
            })

    def test_template_generates_outline_from_heading_levels_one_and_two(self):
        template = (ROOT / "templates" / "interior.typ").read_text(encoding="utf-8")
        self.assertIn('outline(title: none, depth: 2)', template)
        self.assertIn('sys.inputs.at("toc", default: "true")', template)


if __name__ == "__main__":
    unittest.main()
