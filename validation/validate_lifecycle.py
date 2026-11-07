
from config.database import get_connection


def validate_automatic_guilt(cursor):
    """
    Detect violation decisions without a valid completed
    human-review assignment.
    """

    cursor.execute("""
        SELECT
            c.case_id,
            d.decision_id,
            d.decision_outcome,
            cr.assignment_status
        FROM decisions d
        JOIN cases c
            ON d.case_pk = c.case_pk
        LEFT JOIN case_reviewers cr
            ON d.assignment_pk = cr.assignment_pk
           AND d.case_pk = cr.case_pk
        WHERE d.decision_stage = 'initial'
          AND d.decision_outcome = 'violation'
          AND (
              cr.assignment_pk IS NULL
              OR cr.assignment_role NOT IN ('primary', 'secondary')
              OR cr.assignment_status <> 'completed'
              OR cr.completed_at IS NULL
          )
    """)

    return cursor.fetchall()


def validate_reviewer_conflicts(cursor):
    """
    Detect decisions made by reviewers who had
    an active conflict of interest at decision time.
    """

    cursor.execute("""
        SELECT DISTINCT
            c.case_id,
            d.decision_id,
            r.reviewer_name,
            rc.conflict_reason
        FROM decisions d
        JOIN cases c
            ON d.case_pk = c.case_pk
        JOIN case_reviewers cr
            ON d.assignment_pk = cr.assignment_pk
        JOIN reviewers r
            ON cr.reviewer_pk = r.reviewer_pk
        JOIN reviewer_conflicts rc
            ON rc.reviewer_pk = r.reviewer_pk
        JOIN similarity_reports sr
            ON c.similarity_pk = sr.similarity_pk
        JOIN submissions s
            ON sr.submission_pk = s.submission_pk
        WHERE rc.learner_pk = s.learner_pk
          AND rc.effective_from <= DATE(d.decided_at)
          AND (
              rc.effective_to IS NULL
              OR rc.effective_to >= DATE(d.decided_at)
          )
    """)

    return cursor.fetchall()


def validate_evidence_audit(cursor):
    """
    Detect evidence uploaded after a decision without
    a corresponding audit INSERT record.
    """

    cursor.execute("""
        SELECT
            c.case_id,
            e.evidence_id,
            e.uploaded_at,
            d.decision_id
        FROM evidence_items e
        JOIN case_evidence ce
            ON e.evidence_pk = ce.evidence_pk
        JOIN cases c
            ON ce.case_pk = c.case_pk
        JOIN decisions d
            ON d.case_pk = c.case_pk
        WHERE e.uploaded_at > d.decided_at
          AND NOT EXISTS (
              SELECT 1
              FROM audit_logs al
              WHERE al.entity_type = 'evidence'
                AND al.entity_id = e.evidence_id
                AND al.action_type = 'INSERT'
                AND al.action_timestamp >= e.uploaded_at
                AND al.actor_reviewer_pk = e.uploaded_by
          )
    """)

    return cursor.fetchall()


def validate_independent_appeals(cursor):
    """
    Detect resolved appeals without a valid independent
    reviewer assignment and appeal-stage decision.
    Also detect reuse of the original reviewer.
    """

    cursor.execute("""
        SELECT
            a.appeal_id,
            a.appeal_status,
            a.independent_assignment_pk,
            a.appeal_decision_pk
        FROM appeals a

        JOIN decisions original_decision
            ON a.original_decision_pk =
               original_decision.decision_pk

        LEFT JOIN decisions appeal_decision
            ON a.appeal_decision_pk =
               appeal_decision.decision_pk

        LEFT JOIN case_reviewers independent_assignment
            ON a.independent_assignment_pk =
               independent_assignment.assignment_pk

        LEFT JOIN case_reviewers original_assignment
            ON original_decision.assignment_pk =
               original_assignment.assignment_pk

        WHERE a.appeal_status IN ('accepted', 'rejected')
          AND (
              a.independent_assignment_pk IS NULL
              OR a.appeal_decision_pk IS NULL
              OR appeal_decision.decision_stage <> 'appeal'
              OR appeal_decision.case_pk <> a.case_pk
              OR appeal_decision.assignment_pk <>
                 a.independent_assignment_pk
              OR independent_assignment.assignment_role <>
                 'independent_appeal'
              OR independent_assignment.case_pk <> a.case_pk
              OR independent_assignment.reviewer_pk =
                 original_assignment.reviewer_pk
              OR independent_assignment.assignment_status <>
                 'completed'
          )
    """)

    return cursor.fetchall()


def run_lifecycle_validation():

    connection = get_connection()
    cursor = connection.cursor()

    checks = {
        "Automatic guilt": validate_automatic_guilt,
        "Reviewer conflicts": validate_reviewer_conflicts,
        "Evidence audit history": validate_evidence_audit,
        "Independent appeal review": validate_independent_appeals
    }

    try:
        print("\nACADEMIC INTEGRITY LIFECYCLE VALIDATION")
        print("=" * 55)

        total_anomalies = 0

        for check_name, check_function in checks.items():

            results = check_function(cursor)
            total_anomalies += len(results)

            print(f"\n{check_name}")
            print("-" * 45)

            if results:
                print("ANOMALIES FOUND:", len(results))

                for record in results:
                    print(record)
            else:
                print("No anomalies detected.")

        print("\n" + "=" * 55)
        print("TOTAL ANOMALIES:", total_anomalies)
        print("Validation completed.")

    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    run_lifecycle_validation()
