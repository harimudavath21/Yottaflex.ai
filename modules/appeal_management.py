
import json
from datetime import datetime

from config.database import get_connection


def submit_appeal(case_id, original_decision_id, appeal_reason):

    connection = get_connection()
    cursor = connection.cursor()

    try:
        if not appeal_reason or not appeal_reason.strip():
            raise ValueError("Appeal reason cannot be empty.")

        # 1. Find the original decision and case
        cursor.execute("""
            SELECT
                d.decision_pk,
                d.decision_id,
                d.case_pk,
                d.decision_stage,
                c.case_id,
                c.case_status
            FROM decisions d
            JOIN cases c ON d.case_pk = c.case_pk
            WHERE c.case_id = %s
              AND d.decision_id = %s
            FOR UPDATE
        """, (case_id, original_decision_id))

        decision = cursor.fetchone()

        if not decision:
            raise ValueError("Original decision not found.")

        (
            decision_pk,
            decision_id,
            case_pk,
            decision_stage,
            actual_case_id,
            case_status
        ) = decision

        if decision_stage != "initial":
            raise ValueError(
                "An appeal must reference an initial decision."
            )

        if case_status != "closed":
            raise ValueError(
                "Only a closed case can be appealed in this workflow."
            )

        # 2. Prevent duplicate active appeals
        cursor.execute("""
            SELECT appeal_pk
            FROM appeals
            WHERE case_pk = %s
              AND original_decision_pk = %s
              AND appeal_status IN (
                  'submitted',
                  'under_review',
                  'awaiting_information',
                  'accepted',
                  'rejected'
              )
        """, (case_pk, decision_pk))

        if cursor.fetchone():
            raise ValueError(
                "An appeal already exists for this decision."
            )

        # 3. Generate appeal ID
        cursor.execute("""
            SELECT COUNT(*)
            FROM appeals
        """)

        appeal_number = cursor.fetchone()[0] + 1

        appeal_id = f"APL-2026-{appeal_number:06d}"

        # 4. Insert appeal
        cursor.execute("""
            INSERT INTO appeals (
                appeal_id,
                case_pk,
                original_decision_pk,
                appeal_reason,
                appeal_status,
                submitted_at
            )
            VALUES (%s, %s, %s, %s, 'submitted', NOW())
        """, (
            appeal_id,
            case_pk,
            decision_pk,
            appeal_reason.strip()
        ))

        appeal_pk = cursor.lastrowid

        # 5. Update case status
        cursor.execute("""
            UPDATE cases
            SET case_status = 'appeal_pending',
                closed_at = NULL
            WHERE case_pk = %s
        """, (case_pk,))

        # 6. Record audit log
        new_values = {
            "appeal_id": appeal_id,
            "case_id": actual_case_id,
            "original_decision_id": decision_id,
            "appeal_reason": appeal_reason.strip(),
            "appeal_status": "submitted"
        }

        cursor.execute("""
            INSERT INTO audit_logs (
                actor_reviewer_pk,
                entity_type,
                entity_id,
                action_type,
                old_values,
                new_values,
                action_reason,
                action_timestamp
            )
            VALUES (
                NULL, 'appeal', %s, 'APPEAL',
                NULL, %s, %s, NOW()
            )
        """, (
            appeal_id,
            json.dumps(new_values),
            "Appeal submitted against an initial decision."
        ))

        connection.commit()

        print("Appeal submitted successfully!")
        print("Appeal ID:", appeal_id)
        print("Case ID:", actual_case_id)
        print("Original decision:", decision_id)
        print("Appeal status: submitted")
        print("Case status: appeal_pending")

        return appeal_id

    except Exception as error:
        connection.rollback()
        print("Appeal submission failed:", error)
        raise

    finally:
        cursor.close()
        connection.close()


def assign_independent_reviewer(appeal_id, reviewer_id):

    connection = get_connection()
    cursor = connection.cursor()

    try:
        # 1. Find appeal and lock it
        cursor.execute("""
            SELECT
                a.appeal_pk,
                a.case_pk,
                a.appeal_status,
                c.case_id
            FROM appeals a
            JOIN cases c ON a.case_pk = c.case_pk
            WHERE a.appeal_id = %s
            FOR UPDATE
        """, (appeal_id,))

        appeal = cursor.fetchone()

        if not appeal:
            raise ValueError("Appeal not found.")

        appeal_pk, case_pk, appeal_status, case_id = appeal

        if appeal_status != "submitted":
            raise ValueError(
                "Only submitted appeals can receive an assignment."
            )

        # 2. Find reviewer
        cursor.execute("""
            SELECT reviewer_pk, reviewer_role
            FROM reviewers
            WHERE reviewer_id = %s
              AND reviewer_status = 'active'
        """, (reviewer_id,))

        reviewer = cursor.fetchone()

        if not reviewer:
            raise ValueError("Active reviewer not found.")

        reviewer_pk, reviewer_role = reviewer

        if reviewer_role != "academic_admin":
            raise ValueError(
                "Independent appeal reviewer must be an academic administrator."
            )

        # 3. Get original decision reviewer
        cursor.execute("""
            SELECT cr.reviewer_pk
            FROM appeals a
            JOIN decisions d
                ON a.original_decision_pk = d.decision_pk
            JOIN case_reviewers cr
                ON d.assignment_pk = cr.assignment_pk
            WHERE a.appeal_pk = %s
        """, (appeal_pk,))

        original_reviewer = cursor.fetchone()

        if not original_reviewer:
            raise ValueError("Original reviewer could not be identified.")

        if reviewer_pk == original_reviewer[0]:
            raise ValueError(
                "Original reviewer cannot independently review the appeal."
            )

        # 4. Find the learner associated with the case
        cursor.execute("""
            SELECT s.learner_pk
            FROM cases c
            JOIN similarity_reports sr
                ON c.similarity_pk = sr.similarity_pk
            JOIN submissions s
                ON sr.submission_pk = s.submission_pk
            WHERE c.case_pk = %s
        """, (case_pk,))

        learner = cursor.fetchone()

        if not learner:
            raise ValueError("Learner not found for this case.")

        learner_pk = learner[0]

        # 5. Check conflict of interest
        cursor.execute("""
            SELECT COUNT(*)
            FROM reviewer_conflicts
            WHERE reviewer_pk = %s
              AND learner_pk = %s
              AND effective_from <= CURDATE()
              AND (
                  effective_to IS NULL
                  OR effective_to >= CURDATE()
              )
        """, (reviewer_pk, learner_pk))

        if cursor.fetchone()[0] > 0:
            raise ValueError(
                "Conflict of interest detected for this reviewer."
            )

        # 6. Prevent duplicate appeal assignments
        cursor.execute("""
            SELECT assignment_pk
            FROM case_reviewers
            WHERE case_pk = %s
              AND reviewer_pk = %s
              AND assignment_role = 'independent_appeal'
              AND assignment_status IN ('assigned', 'accepted')
        """, (case_pk, reviewer_pk))

        if cursor.fetchone():
            raise ValueError(
                "Reviewer already has an active appeal assignment for this case."
            )

        # 7. Create independent assignment
        cursor.execute("""
            INSERT INTO case_reviewers (
                case_pk,
                reviewer_pk,
                assignment_role,
                assignment_status,
                assigned_at
            )
            VALUES (%s, %s, 'independent_appeal', 'assigned', NOW())
        """, (case_pk, reviewer_pk))

        assignment_pk = cursor.lastrowid

        # 8. Update appeal
        cursor.execute("""
            UPDATE appeals
            SET independent_assignment_pk = %s,
                appeal_status = 'under_review'
            WHERE appeal_pk = %s
        """, (assignment_pk, appeal_pk))

        # 9. Create audit record
        new_values = {
            "appeal_id": appeal_id,
            "case_id": case_id,
            "reviewer_id": reviewer_id,
            "assignment_pk": assignment_pk,
            "assignment_role": "independent_appeal"
        }

        cursor.execute("""
            INSERT INTO audit_logs (
                actor_reviewer_pk,
                entity_type,
                entity_id,
                action_type,
                old_values,
                new_values,
                action_reason,
                action_timestamp
            )
            VALUES (
                NULL, 'appeal', %s, 'ASSIGNMENT',
                NULL, %s, %s, NOW()
            )
        """, (
            appeal_id,
            json.dumps(new_values),
            "Independent appeal reviewer assigned."
        ))

        connection.commit()

        print("Independent reviewer assigned successfully!")
        print("Appeal ID:", appeal_id)
        print("Reviewer ID:", reviewer_id)
        print("Assignment PK:", assignment_pk)

        return assignment_pk

    except Exception as error:
        connection.rollback()
        print("Independent assignment failed:", error)
        raise

    finally:
        cursor.close()
        connection.close()


def get_appeal_history(case_id):

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT
                a.appeal_id,
                c.case_id,
                a.appeal_reason,
                a.appeal_status,
                a.submitted_at,
                a.resolved_at,
                r.reviewer_name,
                a.appeal_decision_pk
            FROM appeals a
            JOIN cases c ON a.case_pk = c.case_pk
            LEFT JOIN case_reviewers cr
                ON a.independent_assignment_pk = cr.assignment_pk
            LEFT JOIN reviewers r
                ON cr.reviewer_pk = r.reviewer_pk
            WHERE c.case_id = %s
            ORDER BY a.submitted_at
        """, (case_id,))

        return cursor.fetchall()

    finally:
        cursor.close()
        connection.close()
