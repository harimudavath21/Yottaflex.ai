
import json

from config.database import get_connection


VALID_EVIDENCE_TYPES = [
    "similarity_report",
    "quoted_content",
    "document_reference",
    "template_match",
    "reviewer_note",
    "other"
]


def add_evidence(
    case_id,
    reviewer_id,
    evidence_type,
    description,
    evidence_reference=None,
    content_hash=None
):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        if evidence_type not in VALID_EVIDENCE_TYPES:
            raise ValueError("Invalid evidence type.")

        if not description or not description.strip():
            raise ValueError("Evidence description cannot be empty.")

        # 1. Find case
        cursor.execute("""
            SELECT case_pk, case_id
            FROM cases
            WHERE case_id = %s
        """, (case_id,))

        case = cursor.fetchone()

        if not case:
            raise ValueError("Case not found.")

        case_pk, actual_case_id = case

        # 2. Find active reviewer
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

        # 3. Prevent duplicate evidence references
        if evidence_reference:
            cursor.execute("""
                SELECT e.evidence_id
                FROM evidence_items e
                JOIN case_evidence ce
                    ON e.evidence_pk = ce.evidence_pk
                WHERE ce.case_pk = %s
                  AND e.evidence_reference = %s
            """, (case_pk, evidence_reference))

            if cursor.fetchone():
                raise ValueError(
                    "This evidence reference already exists for this case."
                )

        # 4. Check whether a decision already exists
        cursor.execute("""
            SELECT COUNT(*)
            FROM decisions
            WHERE case_pk = %s
        """, (case_pk,))

        decision_count = cursor.fetchone()[0]

        if decision_count > 0:
            action_reason = (
                "Evidence uploaded after a decision. "
                "Further review may be required."
            )
        else:
            action_reason = "Evidence uploaded before decision."

        # 5. Generate evidence ID
        cursor.execute("""
            SELECT COUNT(*)
            FROM case_evidence
            WHERE case_pk = %s
        """, (case_pk,))

        evidence_number = cursor.fetchone()[0] + 1

        evidence_id = (
            f"EVD-{actual_case_id}-{evidence_number:03d}"
        )

        # 6. Insert evidence metadata
        cursor.execute("""
            INSERT INTO evidence_items (
                evidence_id,
                evidence_type,
                evidence_description,
                evidence_reference,
                content_hash,
                uploaded_by,
                uploaded_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
        """, (
            evidence_id,
            evidence_type,
            description.strip(),
            evidence_reference,
            content_hash,
            reviewer_pk
        ))

        evidence_pk = cursor.lastrowid

        # 7. Link evidence to case
        cursor.execute("""
            INSERT INTO case_evidence (
                case_pk,
                evidence_pk,
                linked_by,
                linked_at
            )
            VALUES (%s, %s, %s, NOW())
        """, (
            case_pk,
            evidence_pk,
            reviewer_pk
        ))

        # 8. Prepare audit information
        new_values = {
            "evidence_id": evidence_id,
            "case_id": actual_case_id,
            "evidence_type": evidence_type,
            "description": description.strip(),
            "evidence_reference": evidence_reference,
            "content_hash": content_hash,
            "uploaded_by": reviewer_id
        }

        # 9. Insert audit log
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
                %s, %s, %s, 'INSERT',
                NULL, %s, %s, NOW()
            )
        """, (
            reviewer_pk,
            "evidence",
            evidence_id,
            json.dumps(new_values),
            action_reason
        ))

        # 10. Commit all three operations
        connection.commit()

        print("Evidence added successfully!")
        print("Evidence ID:", evidence_id)
        print("Case ID:", actual_case_id)
        print("Evidence PK:", evidence_pk)
        print("Audit log created successfully!")
        print("Action reason:", action_reason)

        return evidence_id

    except Exception as error:
        connection.rollback()
        print("Evidence registration failed:", error)
        raise

    finally:
        cursor.close()
        connection.close()


def get_case_evidence(case_id):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT
                c.case_id,
                e.evidence_id,
                e.evidence_type,
                e.evidence_description,
                e.evidence_reference,
                e.content_hash,
                r.reviewer_name,
                e.uploaded_at,
                ce.linked_at
            FROM case_evidence ce
            JOIN cases c
                ON ce.case_pk = c.case_pk
            JOIN evidence_items e
                ON ce.evidence_pk = e.evidence_pk
            JOIN reviewers r
                ON e.uploaded_by = r.reviewer_pk
            WHERE c.case_id = %s
            ORDER BY e.uploaded_at
        """, (case_id,))

        return cursor.fetchall()

    finally:
        cursor.close()
        connection.close()


def get_evidence_audit(evidence_id):
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
            WHERE entity_type = 'evidence'
              AND entity_id = %s
            ORDER BY action_timestamp
        """, (evidence_id,))

        return cursor.fetchall()

    finally:
        cursor.close()
        connection.close()
