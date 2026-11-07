# AIMS Architecture

## 1. Purpose

The Academic Integrity Management System (AIMS) organizes academic-integrity review as a traceable workflow. It brings together submissions, similarity screening, investigation cases, reviewer assignments, evidence, decisions, appeals, and audit records.

## 2. High-level architecture

```text
User
 |
 v
Streamlit interface (app.py)
 |
 +--> Dashboard and navigation
 |
 +--> Submission / similarity / case views
 |
 +--> Reviewer assignment and evidence workflows
 |
 +--> Decision and appeal workflows
 |
 +--> Audit history and data validation
 |
 v
Application modules
 |
 +--> config/database.py
 +--> modules/evidence_management.py
 +--> modules/decision_management.py
 +--> modules/appeal_management.py
 |
 v
MySQL database
 |
 +--> Learners and reviewers
 +--> Assessments and submissions
 +--> Integrity rules and similarity reports
 +--> Cases and reviewer assignments
 +--> Evidence and decisions
 +--> Appeals and audit history
```

The diagram is conceptual. Use the actual source files and database schema as the authority for exact module boundaries and relationships.

## 3. Application layer

The root `app.py` is the Streamlit entry point. It presents the navigation and application sections, retrieves data from MySQL, and calls workflow functions where appropriate.

Supporting modules separate selected operations:

- `modules/evidence_management.py`: evidence-related operations.
- `modules/decision_management.py`: decision creation and decision/audit retrieval.
- `modules/appeal_management.py`: appeal submission, independent reviewer assignment, and appeal-history retrieval.
- `config/database.py`: database connection configuration.

## 4. Data layer

MySQL stores the operational records. The application uses relational keys to connect learners, assessments, submissions, similarity reports, cases, reviewers, assignments, evidence, decisions, and appeals.

Consult the actual schema file and MySQL foreign-key metadata for exact column definitions, constraints, and cardinalities. Do not infer a production schema from this conceptual overview.

## 5. Synthetic data and report artifacts

`generator/generate_data.py` creates deterministic synthetic records using a fixed seed. The reviewed generator configuration specifies:

- 1,000 learners
- 100 assessments
- 50 reviewers
- 10,000 submissions
- 1,000 flagged similarity records
- 300 investigation cases

The generator includes a guard that checks core tables before inserting data. It is intended for an empty setup, not for rerunning against an existing populated database.

The `synthetic/reports/` directory contains generated JSON report artifacts. Confirm the data is synthetic and review repository size before publishing those files.

## 6. Design principles

1. **Human review:** a similarity score is a screening signal, not a final misconduct decision.
2. **Traceability:** preserve case events, decisions, appeal history, and audit records.
3. **Evidence-based outcomes:** decisions should have a recorded rationale and supporting evidence where applicable.
4. **Independent appeal review:** the appeal workflow should avoid assignment to the original decision reviewer.
5. **Data integrity:** use relational constraints and validation checks to detect inconsistent records.
6. **Privacy:** public demonstrations must use synthetic or anonymized information.

## 7. Known scope boundary

The architecture description does not assert that the application has complete login authentication, authorization enforcement, or production deployment controls. These require separate implementation and verification.
