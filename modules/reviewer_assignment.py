from datetime import datetime

from config.database import get_connection


def assign_primary_reviewers():
    connection = get_connection()
    cursor = connection.cursor()

    try:
        # 1. Fetch active eligible reviewers.
        cursor.execute("""
            SELECT reviewer_pk
            FROM reviewers
            WHERE reviewer_status = 'active'
              AND reviewer_role IN ('instructor', 'academic_admin')
            ORDER BY reviewer_pk
        """)

        reviewers = [row[0] for row in cursor.fetchall()]

        if not reviewers:
            raise RuntimeError("No active eligible reviewers found.")

        # 2. Fetch cases and their associated learners.
        cursor.execute("""
            SELECT
                c.case_pk,
                s.learner_pk,
                c.opened_at
            FROM cases c
            JOIN similarity_reports sr
                ON c.similarity_pk = sr.similarity_pk
            JOIN submissions s
                ON sr.submission_pk = s.submission_pk
            ORDER BY c.case_pk
        """)

        cases = cursor.fetchall()

        # 3. Count existing primary assignments for workload balancing.
        cursor.execute("""
            SELECT reviewer_pk, COUNT(*)
            FROM case_reviewers
            WHERE assignment_role = 'primary'
            GROUP BY reviewer_pk
        """)

        assignment_counts = {
            reviewer_pk: total
            for reviewer_pk, total in cursor.fetchall()
        }

        for reviewer_pk in reviewers:
            assignment_counts.setdefault(reviewer_pk, 0)

        assigned_count = 0
        skipped_count = 0

        # 4. Process each case.
        for case_pk, learner_pk, opened_at in cases:

            # Skip cases that already have a primary reviewer.
            cursor.execute("""
                SELECT assignment_pk
                FROM case_reviewers
                WHERE case_pk = %s
                  AND assignment_role = 'primary'
            """, (case_pk,))

            if cursor.fetchone():
                skipped_count += 1
                continue

            # 5. Find reviewers without an active conflict.
            cursor.execute("""
                SELECT reviewer_pk
                FROM reviewer_conflicts
                WHERE learner_pk = %s
                  AND effective_from <= CURDATE()
                  AND (
                      effective_to IS NULL
                      OR effective_to >= CURDATE()
                  )
            """, (learner_pk,))

            conflicted_reviewers = {
                row[0] for row in cursor.fetchall()
            }

            eligible_reviewers = [
                reviewer_pk
                for reviewer_pk in reviewers
                if reviewer_pk not in conflicted_reviewers
            ]

            if not eligible_reviewers:
                raise RuntimeError(
                    f"No eligible reviewer available for case {case_pk}"
                )

            # 6. Choose the reviewer with the lowest workload.
            selected_reviewer = min(
                eligible_reviewers,
                key=lambda reviewer_pk: (
                    assignment_counts[reviewer_pk],
                    reviewer_pk
                )
            )

            # Never assign a case before it was opened.
            assigned_at = max(datetime.now(), opened_at)

            # 7. Insert the assignment.
            cursor.execute("""
                INSERT INTO case_reviewers (
                    case_pk,
                    reviewer_pk,
                    assignment_role,
                    assignment_status,
                    assigned_at
                )
                VALUES (%s, %s, 'primary', 'assigned', %s)
            """, (
                case_pk,
                selected_reviewer,
                assigned_at
            ))

            assignment_counts[selected_reviewer] += 1
            assigned_count += 1

        connection.commit()

        print("Reviewer assignment completed successfully!")
        print("New assignments:", assigned_count)
        print("Previously assigned cases skipped:", skipped_count)

    except Exception as error:
        connection.rollback()
        print("Reviewer assignment failed:", error)
        raise

    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    assign_primary_reviewers()