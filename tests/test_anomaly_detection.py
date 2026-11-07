import unittest
from unittest.mock import MagicMock

from validation.validate_lifecycle import (
    validate_automatic_guilt,
    validate_reviewer_conflicts,
    validate_evidence_audit,
    validate_independent_appeals
)


class TestAnomalyDetection(unittest.TestCase):

    def setUp(self):
        self.cursor = MagicMock()

    def test_automatic_guilt_detection(self):
        self.cursor.fetchall.return_value = [
            ("INT-TEST-001", "DEC-TEST-001", "violation")
        ]

        results = validate_automatic_guilt(self.cursor)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0][0], "INT-TEST-001")

    def test_reviewer_conflict_detection(self):
        self.cursor.fetchall.return_value = [
            (
                "INT-TEST-002",
                "Test Reviewer",
                "Conflict of interest"
            )
        ]

        results = validate_reviewer_conflicts(self.cursor)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0][0], "INT-TEST-002")

    def test_evidence_audit_detection(self):
        self.cursor.fetchall.return_value = [
            (
                "INT-TEST-003",
                "EVD-TEST-001",
                "2026-11-06 16:00:00"
            )
        ]

        results = validate_evidence_audit(self.cursor)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0][1], "EVD-TEST-001")

    def test_independent_appeal_detection(self):
        self.cursor.fetchall.return_value = [
            (
                "APL-TEST-001",
                "accepted",
                None,
                10
            )
        ]

        results = validate_independent_appeals(self.cursor)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0][0], "APL-TEST-001")


if __name__ == "__main__":
    unittest.main(verbosity=2)
