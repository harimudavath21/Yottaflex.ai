from config.database import get_connection


def validate_record_counts(cursor):
    """Validate expected record counts."""

    expected_counts = {
        "assessments": 100,
        "reviewers": 50,
        "submissions": 10000,
        "similarity_reports": 10000,
        "cases": 300
    }

    all_passed = True

    for table, expected in expected_counts.items():

        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        actual = cursor.fetchone()[0]

        status = "PASS" if actual == expected else "FAIL"

        print(
            f"{table.capitalize()}: {actual} "
            f"(Expected: {expected}) - {status}"
        )

        if actual != expected:
            all_passed = False

    return all_passed


def validate_duplicate_submissions(cursor):
    """Check for duplicate submission IDs."""

    cursor.execute("""
        SELECT COUNT(*)
        FROM (
            SELECT submission_id
            FROM submissions
            GROUP BY submission_id
            HAVING COUNT(*) > 1
        ) AS duplicates
    """)

    duplicates = cursor.fetchone()[0]

    status = "PASS" if duplicates == 0 else "FAIL"

    print(
        f"Duplicate submission IDs: {duplicates} - {status}"
    )

    return duplicates == 0


def validate_similarity_reports(cursor):
    """Check similarity reports without matching submissions."""

    cursor.execute("""
        SELECT COUNT(*)
        FROM similarity_reports sr
        LEFT JOIN submissions s
            ON sr.submission_pk = s.submission_pk
        WHERE s.submission_pk IS NULL
    """)

    orphan_reports = cursor.fetchone()[0]

    status = "PASS" if orphan_reports == 0 else "FAIL"

    print(
        f"Similarity reports without submissions: "
        f"{orphan_reports} - {status}"
    )

    return orphan_reports == 0


def main():

    connection = None
    cursor = None

    try:

        connection = get_connection()
        cursor = connection.cursor()

        print("\n========== DATA VALIDATION ==========\n")

        results = []

        results.append(validate_record_counts(cursor))
        results.append(validate_duplicate_submissions(cursor))
        results.append(validate_similarity_reports(cursor))

        print("\n=====================================")

        if all(results):
            print("OVERALL RESULT: ALL CHECKS PASSED")
        else:
            print("OVERALL RESULT: SOME CHECKS FAILED")

        print("=====================================\n")

    except Exception as error:

        print(f"Validation Error: {error}")

    finally:

        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()


if __name__ == "__main__":
    main()