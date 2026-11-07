# AIMS Workflow Guide

## 1. Submission intake

A learner's work is represented by a submission associated with a learner and an assessment. The submission view exposes submission details such as learner, department, assessment, date, status, and file reference.

## 2. Similarity screening

A similarity report is associated with a submission and includes a score, category, report reference, and generation timestamp.

The reviewed category values are:

- `normal`
- `review_required`
- `high_priority`

A similarity score or category should initiate review according to institutional policy; it should not automatically establish a violation.

## 3. Investigation case

A case is created for a report requiring investigation. Case information includes a case identifier, status, priority/type, timestamps, and description. The case view can display assigned reviewers.

## 4. Reviewer assignment

Reviewer assignments connect a reviewer to a case and record an assignment role and status. The application includes conflict-of-interest checks and an independent appeal-review path.

Before assigning a reviewer, confirm eligibility, workload, conflict status, and any institutional separation-of-duties requirements.

## 5. Evidence management

Evidence records store descriptive metadata and a reference. Evidence is associated with a case. Evidence descriptions and references should be complete enough to support a later review.

Do not store confidential evidence in a public Git repository. Use approved private storage and access controls for real institutional records.

## 6. Decision management

A decision records an outcome and rationale and is associated with the relevant case/reviewer assignment. A decision should be based on the case record and evidence, with a clear rationale.

The application validation logic checks for missing decision rationale and checks that violation decisions are associated with completed assignments.

## 7. Appeals

An appeal references an original decision. The application includes appeal submission, independent reviewer assignment, appeal history, and appeal decision handling.

The independent reviewer should not be the original decision reviewer. Conflict-of-interest checks should be applied before assignment. An appeal outcome should be recorded only after the independent review process is complete.

## 8. Audit and timelines

Audit history and event records provide traceability for relevant operations. Reviewers and administrators should use these records to understand what changed, when it changed, and which actor was recorded.

Actor attribution and authorization must be verified in the current implementation before relying on audit logs as a complete security control.

## 9. Data validation

The validation area checks selected data-quality, workflow, and due-process conditions. Treat validation output as a set of controls implemented in code, not as a certification that the system is free of every defect.
