"""Regression tests for the KDP plugin's pure-Python checks.

Run from the repository root with:
    python -m unittest discover -s tests -v
"""

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import kdp_geometry as geo

_spec = importlib.util.spec_from_file_location(
    "kdp_preflight", ROOT / "scripts" / "preflight.py"
)
preflight = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(preflight)


class TrimTests(unittest.TestCase):
    def test_standard_trim_is_case_and_space_tolerant(self):
        self.assertEqual(geo.parse_trim(" 6 X 9 "), (6.0, 9.0))

    def test_literal_nonstandard_trim(self):
        self.assertEqual(geo.parse_trim("5.25x8.25"), (5.25, 8.25))
        self.assertIsNone(geo.is_standard(5.25, 8.25))

    def test_invalid_trim_without_separator(self):
        with self.assertRaises(geo.GeometryError):
            geo.parse_trim("6-by-9")

    def test_invalid_trim_numbers(self):
        with self.assertRaises(geo.GeometryError):
            geo.parse_trim("sixx9")


class GeometryTests(unittest.TestCase):
    def test_spine_width_uses_selected_paper_caliper(self):
        self.assertAlmostEqual(geo.spine_width(200, "cream-bw"), 0.5)
        self.assertAlmostEqual(geo.spine_width(200, "white-bw"), 0.4504)

    def test_colour_spine_uses_kdp_colour_caliper(self):
        self.assertAlmostEqual(geo.spine_width(100, "standard-colour"), 0.2347)
        self.assertAlmostEqual(geo.spine_width(100, "premium-colour"), 0.2347)

    def test_groundwood_spine_uses_kdp_caliper(self):
        self.assertAlmostEqual(geo.spine_width(100, "groundwood-bw"), 0.235)

    def test_paper_specific_page_limits_for_standard_trims(self):
        self.assertEqual(geo.page_limits("white-bw", "6x9"), (24, 828))
        self.assertEqual(geo.page_limits("cream-bw", "6x9"), (24, 776))
        self.assertEqual(geo.page_limits("groundwood-bw", "6x9"), (24, 812))
        self.assertEqual(geo.page_limits("standard-colour", "6x9"), (72, 600))
        self.assertEqual(geo.page_limits("premium-colour", "6x9"), (24, 828))

    def test_eight_and_a_half_by_eleven_has_lower_page_ceiling(self):
        self.assertEqual(geo.page_limits("white-bw", "8.5x11"), (24, 590))
        self.assertEqual(geo.page_limits("cream-bw", "8.5x11"), (24, 550))
        self.assertEqual(geo.page_limits("standard-colour", "8.5x11"), (72, 600))
        self.assertEqual(geo.page_limits("premium-colour", "8.5x11"), (24, 590))

    def test_a4_standard_colour_is_unavailable(self):
        self.assertIsNone(geo.page_limits("standard-colour", "8.27x11.69"))
        self.assertTrue(any(
            "not available" in item
            for item in geo.validate(200, "8.27x11.69", "standard-colour")
        ))

    def test_unknown_nonstandard_page_ceiling_is_advisory(self):
        problems = geo.validate(200, "5.25x8.25", "cream-bw")
        self.assertTrue(any(geo.is_warning(item) and "not modelled" in item
                            for item in problems))

    def test_valid_short_book_only_warns_about_spine_text(self):
        problems = geo.validate(40, "6x9", "cream-bw")
        self.assertFalse([item for item in problems if not geo.is_warning(item)])
        self.assertTrue(any("no spine text" in item for item in problems))

    def test_cream_page_limit_is_enforced(self):
        self.assertTrue(any(
            "over KDP's 776-page maximum" in item
            for item in geo.validate(778, "6x9", "cream-bw")
        ))

    def test_unknown_paper_is_rejected(self):
        with self.assertRaises(geo.GeometryError):
            geo.spine_width(100, "unknown-paper")

    def test_gutter_tier_boundaries(self):
        expected = {
            150: 0.375, 151: 0.500, 300: 0.500,
            301: 0.625, 500: 0.625, 501: 0.750,
            700: 0.750, 701: 0.875, 828: 0.875,
        }
        for pages, gutter in expected.items():
            with self.subTest(pages=pages):
                self.assertEqual(geo.min_gutter(pages), gutter)

    def test_gutter_rejects_page_count_above_supported_limit(self):
        with self.assertRaises(geo.GeometryError):
            geo.min_gutter(829)

    def test_recommended_margins_include_buffer(self):
        margins = geo.recommended_margins(6, 9, 200)
        self.assertEqual(
            margins, {"inside": 0.75, "outside": 0.63, "top": 0.675, "bottom": 0.8}
        )

    def test_bleed_changes_interior_page_size(self):
        no_bleed = geo.interior_geometry(200, "6x9", False)
        with_bleed = geo.interior_geometry(200, "6x9", True)
        self.assertEqual(no_bleed["page_size_in"], [6.0, 9.0])
        self.assertEqual(with_bleed["page_size_in"], [6.125, 9.25])

    def test_cover_dimensions_and_spine_text_threshold(self):
        below = geo.cover_dimensions(78, "6x9", "cream-bw")
        at_threshold = geo.cover_dimensions(80, "6x9", "cream-bw")
        self.assertAlmostEqual(below["spine_in"], 0.195)
        self.assertFalse(below["spine_text"]["printable"])
        self.assertTrue(at_threshold["spine_text"]["printable"])
        self.assertEqual(len(at_threshold["wrap_in"]), 2)

    def test_validation_reports_minimum_and_odd_page_count(self):
        problems = geo.validate(23)
        self.assertTrue(any("under KDP's 24-page minimum" in p for p in problems))
        self.assertTrue(any("is odd" in p for p in problems))

    def test_validation_accepts_even_standard_extent(self):
        self.assertEqual(geo.validate(200, "6x9", "cream-bw"), [])


class CoverPdfGeometryTests(unittest.TestCase):
    def test_cover_height_mismatch_is_reported(self):
        message = preflight.cover_height_mismatch(9.0, 9.25)
        self.assertIn("cover height is 9.0000in", message)
        self.assertIn("needs 9.2500in", message)

    def test_cover_height_within_tolerance_passes(self):
        self.assertIsNone(preflight.cover_height_mismatch(9.251, 9.25))


class PdfImageResolutionTests(unittest.TestCase):
    def test_parses_effective_image_ppi(self):
        output = (
            "page num type width height color comp bpc enc interp object ID "
            "x-ppi y-ppi size ratio\n"
            "1 0 image 1200 1200 rgb 3 8 image no 7 0 375 375 12K 0.1%\\n"
            "1 1 smask 1200 1200 gray 1 8 image no 7 0 375 375 4K 0.1%\\n"
        )
        records = preflight.parse_pdf_image_resolutions(output)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["width_px"], 1200)
        self.assertEqual(records[0]["x_ppi"], 375)
        self.assertEqual(records[0]["y_ppi"], 375)

    def test_low_resolution_is_a_failure(self):
        failures, warnings = preflight.classify_image_resolutions(
            [{"page": 3, "image": 0, "x_ppi": 220, "y_ppi": 300}],
            "interior",
        )
        self.assertEqual(len(failures), 1)
        self.assertIn("at least 300 PPI", failures[0])
        self.assertEqual(warnings, [])

    def test_very_high_resolution_is_a_warning(self):
        failures, warnings = preflight.classify_image_resolutions(
            [{"page": 1, "image": 0, "x_ppi": 900, "y_ppi": 900}],
            "cover",
        )
        self.assertEqual(failures, [])
        self.assertEqual(len(warnings), 1)
        self.assertIn("at or below 600 PPI", warnings[0])


class PreflightCommandTests(unittest.TestCase):
    @patch.object(preflight.subprocess, "run")
    def test_run_returns_stdout_on_success(self, mocked_run):
        mocked_run.return_value = SimpleNamespace(
            returncode=0, stdout="PDF information", stderr=""
        )
        self.assertEqual(preflight.run(["pdfinfo", "book.pdf"]), "PDF information")

    @patch.object(preflight.subprocess, "run")
    def test_run_fails_with_command_diagnostic_on_nonzero_exit(self, mocked_run):
        mocked_run.return_value = SimpleNamespace(
            returncode=2, stdout="", stderr="file not found"
        )
        with self.assertRaises(SystemExit) as raised:
            preflight.run(["pdfinfo", "missing.pdf"])
        self.assertIn("exited with code 2", str(raised.exception))
        self.assertIn("file not found", str(raised.exception))

    @patch.object(preflight.subprocess, "run", side_effect=FileNotFoundError("not installed"))
    def test_run_fails_clearly_when_command_is_missing(self, mocked_run):
        with self.assertRaises(SystemExit) as raised:
            preflight.run(["pdfinfo", "book.pdf"])
        self.assertIn("could not run 'pdfinfo'", str(raised.exception))


class PdfInfoGeometryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.pdf = Path(self.tmp.name) / "sample.pdf"
        self.pdf.write_bytes(b"%PDF-1.4\n")
    
    def tearDown(self):
        self.tmp.cleanup()

    @patch("kdp_project.shutil.which", return_value="/usr/bin/pdfinfo")
    @patch("kdp_project.subprocess.run")
    def test_pdfinfo_success_returns_measured_geometry(self, mocked_run, _which):
        import kdp_project as project
        mocked_run.return_value = SimpleNamespace(
            returncode=0,
            stdout="Pages:           120\nPage size:       432 x 648 pts (6 x 9 in)\n",
            stderr="",
        )
        self.assertEqual(project.page_geometry(self.pdf), (432.0, 648.0, 120))

    @patch("kdp_project.shutil.which", return_value="/usr/bin/pdfinfo")
    @patch("kdp_project.subprocess.run")
    def test_pdfinfo_nonzero_exit_does_not_fall_back_to_regex(self, mocked_run, _which):
        import kdp_project as project
        mocked_run.return_value = SimpleNamespace(
            returncode=1, stdout="", stderr="Syntax Error: damaged PDF"
        )
        with self.assertRaises(project.ProjectError) as raised:
            project.page_geometry(self.pdf)
        self.assertIn("pdfinfo failed", str(raised.exception))
        self.assertIn("damaged PDF", str(raised.exception))

    @patch("kdp_project.shutil.which", return_value="/usr/bin/pdfinfo")
    @patch("kdp_project.subprocess.run")
    def test_pdfinfo_success_with_unparseable_output_fails_clearly(self, mocked_run, _which):
        import kdp_project as project
        mocked_run.return_value = SimpleNamespace(
            returncode=0, stdout="not a pdfinfo report", stderr=""
        )
        with self.assertRaises(project.ProjectError) as raised:
            project.page_geometry(self.pdf)
        self.assertIn("could not report page size and page count", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
