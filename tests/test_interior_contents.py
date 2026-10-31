"""Tests for the generated interior contents page configuration."""

import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

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

    @patch.object(builder, "compile_pass")
    def test_build_repeats_for_parity_and_gutter_tier(self, compile_pass):
        compile_pass.side_effect = [
            (Path("interior.pdf"), 301),
            (Path("interior.pdf"), 302),
        ]
        out, pages, history = builder.build_until_stable({})
        self.assertEqual(pages, 302)
        self.assertEqual(len(history), 2)
        self.assertEqual(compile_pass.call_args_list[0].kwargs,
                         {"pages_est": 300, "parity": False})
        self.assertEqual(compile_pass.call_args_list[1].kwargs,
                         {"pages_est": 302, "parity": True})

    @patch.object(builder, "compile_pass")
    def test_no_parity_still_corrects_gutter_tier(self, compile_pass):
        compile_pass.side_effect = [
            (Path("interior.pdf"), 301),
            (Path("interior.pdf"), 301),
        ]
        _, pages, history = builder.build_until_stable({}, no_parity=True)
        self.assertEqual(pages, 301)
        self.assertEqual(len(history), 2)
        self.assertEqual(compile_pass.call_args_list[1].kwargs,
                         {"pages_est": 301, "parity": False})

    @patch.object(builder, "compile_pass")
    def test_build_stops_when_geometry_never_stabilises(self, compile_pass):
        compile_pass.return_value = (Path("interior.pdf"), 301)
        with self.assertRaises(builder.proj.ProjectError):
            builder.build_until_stable({}, max_passes=2)

    def test_template_has_front_matter_and_body_page_numbering(self):
        template = (ROOT / "templates" / "interior.typ").read_text(encoding="utf-8")
        self.assertIn('numbering: none', template)
        self.assertIn('numbering: "i"', template)
        self.assertIn('counter(page).update(1)', template)
        self.assertIn('numbering: "1"', template)

    def test_template_generates_outline_from_heading_levels_one_and_two(self):
        template = (ROOT / "templates" / "interior.typ").read_text(encoding="utf-8")
        self.assertIn('outline(title: none, depth: 2)', template)
        self.assertIn('sys.inputs.at("toc", default: "true")', template)


if __name__ == "__main__":
    unittest.main()
