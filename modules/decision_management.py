
import json
from datetime import datetime

from config.database import get_connection


VALID_OUTCOMES = [
    "no_violation",
    "violation",
    "inconclusive",
    "more_evidence_required",
    "reversed"
]

VALID_STAGES = ["initial", "appeal"]


def make_decision(
    case_id,
    reviewer_id,
    decision_outcome,
    decision_rationale,
    decision_stage="initial"
):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        # 1. Validate inputs
        if decision_outcome not in VALID_OUTCOMES:
            raise ValueError("Invalid decision outcome.")

        if decision_stage not in VALID_STAGES:
            raise ValueError("Invalid decision stage.")

        if not decision_rationale or not decision_rationale.strip():
            raise ValueError("Decision rationale cannot be empty.")

        if decision_stage == "initial" and decision_outcome == "reversed":
            raise ValueError(
                "The reversed outcome is only valid for appeal decisions."
            )

        # 2. Find and lock the case
        cursor.execute("""
            SELECT case_pk, case_id, case_status
            FROM cases
            WHERE case_id = %s
            FOR UPDATE
        """, (case_id,))

        case = cursor.fetchone()

        if not case:
            raise ValueError("Case not found.")

        case_pk, actual_case_id, case_status = case

        # 3. Find active reviewer
        cursor.execute("""
            SELECT reviewer_pk
            FROM reviewers
            WHERE reviewer_id = %s
              AND reviewer_status = 'active'
        """, (reviewer_id,))

        reviewer = cursor.fetchone()

        if not reviewer:
            raise ValueError("Active reviewer not found.")

        reviewer_pk = reviewer[0]

        appeal_pk = None
        appeal_id = None
        original_decision_pk = None
        independent_assignment_pk = None

        # 4. Find the correct assignment
        if decision_stage == "initial":

            if case_status not in ("open", "decision_pending"):
                raise ValueError(
                    "Case is not ready for an initial decision."
                )

            cursor.execute("""
                SELECT assignment_pk
                FROM case_reviewers
                WHERE case_pk = %s
                  AND reviewer_pk = %s
                  AND assignment_role = 'primary'
                  AND assignment_status IN ('assigned', 'accepted')
                ORDER BY assignment_pk DESC
                LIMIT 1
            """, (case_pk, reviewer_pk))

        else:

            if case_status != "appeal_pending":
                raise ValueError(
                    "Case is not awaiting an appeal decision."
                )

            cursor.execute("""
                SELECT
                    appeal_pk,
                    appeal_id,
                    original_decision_pk,
                    independent_assignment_pk
                FROM appeals
                WHERE case_pk = %s
                  AND appeal_status = 'under_review'
                ORDER BY submitted_at DESC
                LIMIT 1
                FOR UPDATE
            """, (case_pk,))

            appeal = cursor.fetchone()

            if not appeal:
                raise ValueError(
                    "No appeal is currently under review."
                )

            (
                appeal_pk,
                appeal_id,
                original_decision_pk,
                independent_assignment_pk
            ) = appeal

            if independent_assignment_pk is None:
                raise ValueError(
                    "Appeal has no independent reviewer assignment."
                )

            cursor.execute("""
                SELECT assignment_pk
                FROM case_reviewers
                WHERE assignment_pk = %s
                  AND case_pk = %s
                  AND reviewer_pk = %s
                  AND assignment_role = 'independent_appeal'
                  AND assignment_status IN ('assigned', 'accepted')
            """, (
                independent_assignment_pk,
                case_pk,
                reviewer_pk
            ))

        assignment = cursor.fetchone()

        if not assignment:
            raise ValueError(
                "Reviewer does not have the required active assignment."
            )

        assignment_pk = assignment[0]

        # 5. Prevent original reviewer from deciding the appeal
        if decision_stage == "appeal":

            cursor.execute("""
                SELECT assignment_pk
                FROM decisions
                WHERE decision_pk = %s
            """, (original_decision_pk,))

            original_decision = cursor.fetchone()

            if not original_decision:
                raise ValueError("Original decision not found.")

            cursor.execute("""
                SELECT reviewer_pk
                FROM case_reviewers
                WHERE assignment_pk = %s
            """, (original_decision[0],))

            original_reviewer = cursor.fetchone()

            if (
                original_reviewer
                and original_reviewer[0] == reviewer_pk
            ):
                raise ValueError(
                    "Original reviewer cannot decide their own appeal."
                )

        # 6. Check conflict of interest
        cursor.execute("""
            SELECT COUNT(*)
            FROM cases c
            JOIN similarity_reports sr
                ON c.similarity_pk = sr.similarity_pk
            JOIN submissions s
                ON sr.submission_pk = s.submission_pk
            JOIN reviewer_conflicts rc
                ON rc.learner_pk = s.learner_pk
            WHERE c.case_pk = %s
              AND rc.reviewer_pk = %s
              AND rc.effective_from <= CURDATE()
              AND (
                  rc.effective_to IS NULL
                  OR rc.effective_to >= CURDATE()
              )
        """, (case_pk, reviewer_pk))

        if cursor.fetchone()[0] > 0:
            raise ValueError(
                "Conflict of interest detected."
            )

        # 7. Prevent duplicate decisions
        cursor.execute("""
            SELECT COUNT(*)
            FROM decisions
            WHERE case_pk = %s
              AND decision_stage = %s
        """, (case_pk, decision_stage))

        if cursor.fetchone()[0] > 0:
            raise ValueError(
                "A decision already exists for this case and stage."
            )

        # 8. Generate a unique decision ID
        cursor.execute("""
            SELECT COALESCE(
                MAX(CAST(SUBSTRING(decision_id, 10) AS UNSIGNED)),
                0
            )
            FROM decisions
            WHERE decision_id LIKE 'DEC-2026-%'
        """)

        decision_number = int(cursor.fetchone()[0]) + 1
        decision_id = f"DEC-2026-{decision_number:06d}"

        # 9. Determine lifecycle transition
        if decision_stage == "initial":

            if decision_outcome in ("no_violation", "violation"):
                new_case_status = "closed"

            elif decision_outcome == "more_evidence_required":
                new_case_status = "awaiting_evidence"

            else:
                new_case_status = "decision_pending"

            new_appeal_status = None

        else:

            if decision_outcome == "reversed":
                new_case_status = "closed"
                new_appeal_status = "accepted"

            elif decision_outcome == "more_evidence_required":
                new_case_status = "awaiting_evidence"
                new_appeal_status = "awaiting_information"

            elif decision_outcome == "inconclusive":
                new_case_status = "decision_pending"
                new_appeal_status = "awaiting_information"

            else:
                new_case_status = "closed"
                new_appeal_status = "rejected"

        # 10. Insert decision
        decided_at = datetime.now()

        cursor.execute("""
            INSERT INTO decisions (
                decision_id,
                case_pk,
                assignment_pk,
                decision_stage,
                decision_outcome,
                decision_rationale,
                decided_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            decision_id,
            case_pk,
            assignment_pk,
            decision_stage,
            decision_outcome,
            decision_rationale.strip(),
            decided_at
        ))

        decision_pk = cursor.lastrowid

        # 11. Complete reviewer assignment
        cursor.execute("""
            UPDATE case_reviewers
            SET assignment_status = 'completed',
                completed_at = %s
            WHERE assignment_pk = %s
              AND case_pk = %s
              AND reviewer_pk = %s
        """, (
            decided_at,
            assignment_pk,
            case_pk,
            reviewer_pk
        ))

        if cursor.rowcount != 1:
            raise RuntimeError(
                "Reviewer assignment could not be marked completed."
            )

        # 12. Update appeal when this is an appeal decision
        if decision_stage == "appeal":

            resolved_at = (
                decided_at
                if new_appeal_status in ("accepted", "rejected")
                else None
            )

            cursor.execute("""
                UPDATE appeals
                SET appeal_decision_pk = %s,
                    appeal_status = %s,
                    resolved_at = %s
                WHERE appeal_pk = %s
            """, (
                decision_pk,
                new_appeal_status,
                resolved_at,
                appeal_pk
            ))

        # 13. Update case status
        closed_at = (
            decided_at
            if new_case_status == "closed"
            else None
        )

        cursor.execute("""
            UPDATE cases
            SET case_status = %s,
                closed_at = %s
            WHERE case_pk = %s
        """, (
            new_case_status,
            closed_at,
            case_pk
        ))

        # 14. Create audit log
        new_values = {
            "decision_id": decision_id,
            "case_id": actual_case_id,
            "decision_stage": decision_stage,
            "decision_outcome": decision_outcome,
            "decision_rationale": decision_rationale.strip(),
            "reviewer_id": reviewer_id,
            "assignment_pk": assignment_pk,
            "case_status": new_case_status
        }

        if decision_stage == "appeal":
            new_values["appeal_id"] = appeal_id
            new_values["appeal_status"] = new_appeal_status

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
                %s, 'decision', %s, 'DECISION',
                NULL, %s, %s, NOW()
            )
        """, (
            reviewer_pk,
            decision_id,
            json.dumps(new_values),
            "Decision recorded by assigned reviewer."
        ))

        # 15. Commit all changes together
        connection.commit()

        print("Decision recorded successfully!")
        print("Decision ID:", decision_id)
        print("Case ID:", actual_case_id)
        print("Decision stage:", decision_stage)
        print("Decision outcome:", decision_outcome)
        print("Case status:", new_case_status)
        print("Reviewer assignment status: completed")

        if decision_stage == "appeal":
            print("Appeal ID:", appeal_id)
            print("Appeal status:", new_appeal_status)

        return decision_id

    except Exception as error:
        connection.rollback()
        print("Decision registration failed:", error)
        raise

    finally:
        cursor.close()
        connection.close()


def get_case_decisions(case_id):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT
                c.case_id,
                d.decision_id,
                d.decision_stage,
                d.decision_outcome,
                d.decision_rationale,
                d.decided_at,
                r.reviewer_name
            FROM decisions d
            JOIN cases c
                ON d.case_pk = c.case_pk
            JOIN case_reviewers cr
                ON d.assignment_pk = cr.assignment_pk
            JOIN reviewers r
                ON cr.reviewer_pk = r.reviewer_pk
            WHERE c.case_id = %s
            ORDER BY d.decided_at
        """, (case_id,))

        return cursor.fetchall()

    finally:
        cursor.close()
        connection.close()


def get_decision_audit(decision_id):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT
                entity_id,
                action_type,
                old_values,
                new_values,
                action_reason,
                action_timestamp,
                actor_reviewer_pk
            FROM audit_logs
            WHERE entity_type = 'decision'
              AND entity_id = %s
            ORDER BY action_timestamp
        """, (decision_id,))

        return cursor.fetchall()

    finally:
        cursor.close()
        connection.close()
