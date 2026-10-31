"""Tests for conservative KDP listing checks."""

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "listing_audit", ROOT / "scripts" / "listing_audit.py"
)
audit = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(audit)


class ListingAuditTests(unittest.TestCase):
    def test_clean_listing_has_no_warnings(self):
        self.assertEqual(
            audit.audit_listing(
                "A practical guide for home gardening.",
                ["container plants", "indoor herbs"],
                ["Gardening"],
            ),
            [],
        )

    def test_detects_duplicate_keywords_case_insensitively(self):
        warnings = audit.audit_listing(
            "A description.", ["Home Gardening", " home   gardening "], []
        )
        self.assertTrue(any("duplicates keyword" in item for item in warnings))

    def test_detects_category_word_repeated_in_keyword(self):
        warnings = audit.audit_listing(
            "A description.", ["Gardening for beginners"], ["Gardening"]
        )
        self.assertTrue(any("repeats category word" in item for item in warnings))

    def test_flags_quotes_claims_and_time_sensitive_terms(self):
        warnings = audit.audit_listing(
            "A description.", ['"best new gardening 2026"'], []
        )
        self.assertTrue(any("quotation marks" in item for item in warnings))
        self.assertTrue(any("promotional/ranking claim" in item for item in warnings))
        self.assertTrue(any("time-sensitive" in item for item in warnings))

    def test_flags_empty_and_excess_fields(self):
        warnings = audit.audit_listing("", ["", "a", "b", "c", "d", "e", "f", "g"], ["", "x", "y", "z"])
        self.assertTrue(any("description is empty" in item for item in warnings))
        self.assertTrue(any("keyword 1 is empty" in item for item in warnings))
        self.assertTrue(any("limit is 7" in item for item in warnings))
        self.assertTrue(any("limit is 3" in item for item in warnings))
        self.assertTrue(any("category 1 is empty" in item for item in warnings))

    def test_does_not_mutate_user_values(self):
        keywords = ["  quiet gardens  "]
        audit.audit_listing("Description.", keywords, [])
        self.assertEqual(keywords, ["  quiet gardens  "])


if __name__ == "__main__":
    unittest.main()
