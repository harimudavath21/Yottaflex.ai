-- ============================================================
-- AIMS: READ-ONLY DATA INSPECTION / VERIFICATION QUERIES
-- ============================================================
-- IMPORTANT:
-- This file intentionally does NOT INSERT, UPDATE, DELETE,
-- TRUNCATE, DROP, or ALTER any records or database objects.
--
-- The project already has a deterministic synthetic-data
-- generator at generator/generate_data.py. That generator
-- checks that its core tables are empty before inserting data.
-- Do NOT run that generator against the existing populated DB.
--
-- Run these queries only after selecting the intended AIMS
-- database in MySQL Workbench.
-- ============================================================

-- 1. Core record counts
SELECT 'learners' AS table_name, COUNT(*) AS record_count FROM learners
UNION ALL
SELECT 'assessments', COUNT(*) FROM assessments
UNION ALL
SELECT 'reviewers', COUNT(*) FROM reviewers
UNION ALL
SELECT 'submissions', COUNT(*) FROM submissions
UNION ALL
SELECT 'similarity_reports', COUNT(*) FROM similarity_reports
UNION ALL
SELECT 'cases', COUNT(*) FROM cases
UNION ALL
SELECT 'case_reviewers', COUNT(*) FROM case_reviewers
UNION ALL
SELECT 'evidence_items', COUNT(*) FROM evidence_items
UNION ALL
SELECT 'decisions', COUNT(*) FROM decisions
UNION ALL
SELECT 'appeals', COUNT(*) FROM appeals
UNION ALL
SELECT 'audit_logs', COUNT(*) FROM audit_logs;

-- 2. Similarity category distribution
SELECT
    similarity_category,
    COUNT(*) AS report_count
FROM similarity_reports
GROUP BY similarity_category
ORDER BY similarity_category;

-- 3. Investigation case status distribution
SELECT
    case_status,
    COUNT(*) AS case_count
FROM cases
GROUP BY case_status
ORDER BY case_status;

-- 4. Reviewer assignment status distribution
SELECT
    assignment_status,
    COUNT(*) AS assignment_count
FROM case_reviewers
GROUP BY assignment_status
ORDER BY assignment_status;

-- 5. Similarity scores outside the expected range
SELECT
    similarity_id,
    similarity_score,
    similarity_category
FROM similarity_reports
WHERE similarity_score IS NULL
   OR similarity_score < 0
   OR similarity_score > 100;

-- 6. Decisions with missing rationale
SELECT
    decision_pk,
    case_pk,
    decision_outcome
FROM decisions
WHERE decision_rationale IS NULL
   OR TRIM(decision_rationale) = '';

-- 7. Evidence with missing descriptive metadata
SELECT
    evidence_pk,
    evidence_id
FROM evidence_items
WHERE evidence_description IS NULL
   OR TRIM(evidence_description) = ''
   OR evidence_reference IS NULL
   OR TRIM(evidence_reference) = '';

-- 8. Appeals resolved before submission
SELECT
    appeal_pk,
    submitted_at,
    resolved_at
FROM appeals
WHERE resolved_at IS NOT NULL
  AND resolved_at < submitted_at;

-- 9. Completed assignments without completion timestamps
SELECT
    assignment_pk,
    case_pk,
    reviewer_pk,
    assignment_status,
    completed_at
FROM case_reviewers
WHERE assignment_status = 'completed'
  AND completed_at IS NULL;

-- End of read-only inspection script.
