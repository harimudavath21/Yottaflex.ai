import unittest

from config.database import get_connection


class TestLifecycleIntegration(unittest.TestCase):

    def setUp(self):
        self.connection = get_connection()
        self.cursor = self.connection.cursor()

    def tearDown(self):
        self.cursor.close()
        self.connection.close()

    def test_database_connection(self):
        self.cursor.execute("SELECT DATABASE()")
        database = self.cursor.fetchone()[0]

        self.assertEqual(database, "yottaflex")

    def test_appeal_assignment_completed(self):
        self.cursor.execute("""
            SELECT
                cr.assignment_status,
                cr.completed_at,
                d.decision_stage
            FROM case_reviewers cr
            JOIN decisions d
                ON cr.assignment_pk = d.assignment_pk
            WHERE d.decision_id = 'DEC-2026-000002'
        """)

        result = self.cursor.fetchone()

        self.assertIsNotNone(result)
        self.assertEqual(result[0], "completed")
        self.assertIsNotNone(result[1])
        self.assertEqual(result[2], "appeal")


if __name__ == "__main__":
    unittest.main(verbosity=2)