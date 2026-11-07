# AIMS Database Overview

## Purpose

The AIMS database stores the records required to manage submissions and academic-integrity review. This document is a conceptual guide, not a replacement for the project's authoritative MySQL schema.

## Main entities identified in the application and data generator

| Entity/table | Purpose |
|---|---|
| `learners` | Learner identity and academic information |
| `assessments` | Assessments to which learners submit work |
| `integrity_rules` | Rules or thresholds used by the screening workflow |
| `reviewers` | Staff/reviewer records |
| `submissions` | Learner submission records |
| `similarity_reports` | Similarity screening output associated with submissions |
| `cases` | Investigation records associated with similarity reports |
| `case_reviewers` | Reviewer assignments to investigation cases |
| `reviewer_conflicts` | Conflict-of-interest records used by reviewer assignment logic |
| `evidence_items` | Evidence metadata |
| `case_evidence` | Association between cases and evidence items |
| `decisions` | Recorded case or appeal decisions |
| `appeals` | Learner appeals against an original decision |
| `audit_logs` | Audit events for tracked operations |
| `case_events` | Case timeline events |
| `appeal_events` | Appeal timeline events |

The exact set of columns, indexes, constraints, and nullability must be taken from the actual database schema.

## Relationship overview

The application queries establish these important relationships:

- A submission references a learner and an assessment.
- A similarity report references a submission.
- A case references a similarity report.
- A case can have reviewer assignments through `case_reviewers`.
- A case can be associated with evidence through `case_evidence`.
- A decision is associated with a case and a reviewer assignment.
- An appeal references an original decision and may reference an independent reviewer assignment and an appeal decision.

Confirm exact foreign-key names and delete/update rules in MySQL before writing migrations.

## Data integrity

The project's validation logic checks, among other things:

- Similarity scores are present and within the 0–100 range.
- Similarity categories use the expected values: `normal`, `review_required`, or `high_priority`.
- Decisions include a rationale.
- Evidence includes a description and reference.
- Appeal resolution does not precede appeal submission.
- Completed assignments have a completion timestamp.
- Violation decisions are associated with completed reviewer assignments.
- Resolved appeals have the expected independent-review and appeal-decision relationships.

These checks describe validation rules found in the reviewed project code. They do not guarantee that every possible integrity condition is covered.

## Safe database setup

1. Inspect the authoritative schema SQL.
2. Confirm the target database name.
3. Back up any database containing important records.
4. Apply schema creation only to the intended new/empty database.
5. Use the existing generator only after confirming its empty-table preconditions.
6. Run read-only validation queries after setup.

## Seed data warning

The supplied `seed_data.sql` is deliberately read-only. It provides record counts and basic integrity inspection queries; it does not populate tables.

The Python generator is the project's existing synthetic-data creation path. Do not run it again against the current populated database.
