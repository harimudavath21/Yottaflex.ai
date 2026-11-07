
import random
from datetime import datetime, timedelta
from faker import Faker

from config.database import get_connection



# CONFIGURATION


SEED = 20261022

TOTAL_LEARNERS = 1000
TOTAL_ASSESSMENTS = 100
TOTAL_REVIEWERS = 50
TOTAL_SUBMISSIONS = 10000
TOTAL_FLAGS = 1000
TOTAL_CASES = 300

YEAR = 2026

random.seed(SEED)
fake = Faker("en_IN")
Faker.seed(SEED)



# HELPER FUNCTIONS

def generate_id(prefix, number):
    return f"{prefix}-2026-{number:06d}"


def generate_similarity_id(submission_id):
    return f"SIM-{submission_id}-01"



# CHECK DATABASE


def check_empty_database(cursor):

    tables = [
        "learners",
        "assessments",
        "integrity_rules",
        "reviewers",
        "submissions",
        "similarity_reports",
        "cases"
    ]

    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]

        if count > 0:
            raise RuntimeError(
                f"Table {table} already contains {count} records. "
                "Do not run the generator again without a reset plan."
            )



# 1. GENERATE LEARNERS


def generate_learners(cursor):

    records = []

    departments = [
        "Computer Science",
        "Information Technology",
        "Data Science",
        "Electronics",
        "Mechanical",
        "Civil"
    ]

    for i in range(1, TOTAL_LEARNERS + 1):

        records.append((
            generate_id("LRN", i),
            fake.name(),
            f"learner{i}@example.edu",
            random.choice(departments),
            fake.date_between(
                start_date="-3y",
                end_date="-30d"
            ),
            "active"
        ))

    cursor.executemany("""
        INSERT INTO learners (
            learner_id,
            full_name,
            email,
            department,
            enrollment_date,
            learner_status
        )
        VALUES (%s, %s, %s, %s, %s, %s)
    """, records)

    print("Learners generated:", len(records))


# ==========================================
# 2. GENERATE ASSESSMENTS
# ==========================================

def generate_assessments(cursor):

    records = []

    courses = [
        "Python Programming",
        "Database Management",
        "Machine Learning",
        "Data Analytics",
        "Artificial Intelligence",
        "Statistics",
        "Software Engineering"
    ]

    types = ["assignment", "exam", "project", "quiz"]

    for i in range(1, TOTAL_ASSESSMENTS + 1):

        deadline = datetime(2026, 12, 31) - timedelta(days=i)

        records.append((
            generate_id("ASM", i),
            f"Assessment {i}",
            random.choice(courses),
            random.choice(types),
            100.00,
            deadline,
            "published"
        ))

    cursor.executemany("""
        INSERT INTO assessments (
            assessment_id,
            assessment_name,
            course_name,
            assessment_type,
            max_marks,
            submission_deadline,
            assessment_status
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, records)

    print("Assessments generated:", len(records))



# 3. GENERATE INTEGRITY RULES


def generate_integrity_rules(cursor):

    cursor.execute("""
        INSERT INTO integrity_rules (
            rule_id,
            rule_name,
            description,
            review_threshold,
            high_priority_threshold,
            effective_from,
            rule_status
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (
        "RULE-2026-000001",
        "Standard Similarity Review",
        "Similarity thresholds trigger human review, not automatic guilt.",
        30.00,
        70.00,
        "2026-01-01",
        "active"
    ))

    cursor.execute("""
        SELECT rule_pk
        FROM integrity_rules
        WHERE rule_id = %s
    """, ("RULE-2026-000001",))

    rule_pk = cursor.fetchone()[0]

    print("Integrity rules generated: 1")

    return rule_pk



# 4. GENERATE REVIEWERS


def generate_reviewers(cursor):

    records = []

    roles = [
        "instructor",
        "academic_admin",
        "support_staff"
    ]

    departments = [
        "Computer Science",
        "Data Science",
        "Information Technology",
        "Administration"
    ]

    for i in range(1, TOTAL_REVIEWERS + 1):

        records.append((
            generate_id("REV", i),
            fake.name(),
            f"reviewer{i}@example.edu",
            random.choice(roles),
            random.choice(departments),
            "active"
        ))

    cursor.executemany("""
        INSERT INTO reviewers (
            reviewer_id,
            reviewer_name,
            email,
            reviewer_role,
            department,
            reviewer_status
        )
        VALUES (%s, %s, %s, %s, %s, %s)
    """, records)

    print("Reviewers generated:", len(records))



# 5. GENERATE SUBMISSIONS


def generate_submissions(cursor):

    # Ensure every learner-assessment combination is unique.
    combinations = [
        (learner_pk, assessment_pk)
        for learner_pk in range(1, TOTAL_LEARNERS + 1)
        for assessment_pk in range(1, TOTAL_ASSESSMENTS + 1)
    ]

    selected = random.sample(
        combinations,
        TOTAL_SUBMISSIONS
    )

    records = []
    submission_ids = []

    for i, (learner_pk, assessment_pk) in enumerate(selected, 1):

        submission_id = generate_id("SUB", i)

        submission_date = datetime(2026, 1, 1) + timedelta(
            days=random.randint(0, 270),
            hours=random.randint(0, 23)
        )

        records.append((
            submission_id,
            learner_pk,
            assessment_pk,
            submission_date,
            f"synthetic/submissions/{submission_id}.pdf",
            "submitted"
        ))

        submission_ids.append(submission_id)

    cursor.executemany("""
        INSERT INTO submissions (
            submission_id,
            learner_pk,
            assessment_pk,
            submission_date,
            file_reference,
            submission_status
        )
        VALUES (%s, %s, %s, %s, %s, %s)
    """, records)

    print("Submissions generated:", len(records))

    return submission_ids



# 6. GENERATE SIMILARITY REPORTS


def generate_similarity_reports(
    cursor,
    submission_ids,
    rule_pk
):

    flagged_indexes = set(
        random.sample(
            range(TOTAL_SUBMISSIONS),
            TOTAL_FLAGS
        )
    )

    records = []

    for i, submission_id in enumerate(submission_ids):

        is_flagged = i in flagged_indexes

        if is_flagged:

            score = round(random.uniform(30, 100), 2)

            if score >= 70:
                category = "high_priority"
            else:
                category = "review_required"

        else:

            score = round(random.uniform(0, 29.99), 2)
            category = "normal"

        similarity_id = generate_similarity_id(
            submission_id
        )

        generated_at = datetime(2026, 10, 1) + timedelta(
    days=random.randint(0, 10)
)

        records.append((
            similarity_id,
            i + 1,
            rule_pk,
            score,
            category,
            f"synthetic/reports/{similarity_id}.json",
            generated_at
        ))

    cursor.executemany("""
        INSERT INTO similarity_reports (
            similarity_id,
            submission_pk,
            rule_pk,
            similarity_score,
            similarity_category,
            report_reference,
            generated_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, records)

    print("Similarity reports generated:", len(records))
    print("Flagged reports:", len(flagged_indexes))

    return flagged_indexes



# 7. GENERATE INVESTIGATION CASES


def generate_cases(cursor, flagged_indexes):

    selected_flags = random.sample(
        sorted(flagged_indexes),
        TOTAL_CASES
    )

    # Get report IDs and scores for selected flagged reports.
    selected_submission_pks = [
        index + 1 for index in selected_flags
    ]

    placeholders = ",".join(
        ["%s"] * len(selected_submission_pks)
    )

    cursor.execute(f"""
        SELECT similarity_pk, similarity_score
        FROM similarity_reports
        WHERE submission_pk IN ({placeholders})
        ORDER BY similarity_pk
    """, selected_submission_pks)

    reports = cursor.fetchall()

    records = []

    for i, (similarity_pk, score) in enumerate(reports, 1):

        case_id = generate_id("INT", i)

        if score >= 70:
            priority = "high"
        else:
            priority = "medium"

        opened_at = datetime(2026, 10, 15) + timedelta(
            days=random.randint(0, 15)
        )

        records.append((
            case_id,
            similarity_pk,
            "similarity_flag",
            priority,
            "open",
            opened_at,
            None,
            "Generated for human academic integrity review."
        ))

    cursor.executemany("""
        INSERT INTO cases (
            case_id,
            similarity_pk,
            case_type,
            case_priority,
            case_status,
            opened_at,
            closed_at,
            case_description
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, records)

    print("Investigation cases generated:", len(records))



# MAIN GENERATOR


def main():

    connection = get_connection()
    cursor = connection.cursor()

    try:

        check_empty_database(cursor)

        print("\nStarting synthetic data generation...")
        print("Fixed seed:", SEED)

        generate_learners(cursor)

        generate_assessments(cursor)

        rule_pk = generate_integrity_rules(cursor)

        generate_reviewers(cursor)

        submission_ids = generate_submissions(cursor)

        flagged_indexes = generate_similarity_reports(
            cursor,
            submission_ids,
            rule_pk
        )

        generate_cases(cursor, flagged_indexes)

        connection.commit()

        print("\n================================")
        print("DATA GENERATION SUCCESSFUL")
        print("================================")

    except Exception as error:

        connection.rollback()

        print("Generation failed:", error)
        print("All changes have been rolled back.")

        raise

    finally:

        cursor.close()
        connection.close()


if __name__ == "__main__":
    main()
