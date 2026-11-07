# Academic Integrity Management System (AIMS)

A Streamlit and MySQL application for managing academic-integrity workflows, from student submissions and similarity screening through investigation, reviewer assignment, evidence management, decisions, appeals, and audit review.

## Project Overview

AIMS centralizes the operational records required to review potential academic-integrity concerns.

Similarity results are treated as review signals, not final findings of misconduct. Cases can move through human review, evidence collection, decision recording, and an independent appeal workflow.

## Main Features

- Institutional dashboard with record and workflow summaries.
- Student submission browsing.
- Similarity report review and classification.
- Investigation case tracking.
- Reviewer assignment and workload visibility.
- Evidence recording and case association.
- Decision recording with rationale.
- Appeal submission and independent-review workflow.
- Audit-history inspection.
- Data-validation checks.

> The application currently implements its navigation and sections in the root `app.py`. The `pages/` directory is intentionally not used for duplicate Streamlit pages.

## Technology Stack

- Python 3.14.6 (current validated development environment)
- Streamlit
- MySQL 8.0
- MySQL Connector/Python
- Pandas
- NumPy
- Plotly
- Python-dotenv
- Faker
- Pytest

See `requirements.txt` for the dependency list.

## Project Structure

```text
Yottaflex.ai/
│
├── app.py
├── config/
│   ├── database.py
│   └── __init__.py
│
├── data/
│   └── database/
│       ├── schema.sql
│       └── seed_data.sql
│
├── docs/
│   ├── architecture.md
│   ├── database.md
│   ├── development.md
│   └── workflows.md
│
├── generator/
│   ├── generate_data.py
│   └── generate_report_files.py
│
├── modules/
│   ├── appeal_management.py
│   ├── decision_management.py
│   ├── evidence_management.py
│   └── reviewer_assignment.py
│
├── pages/
│   └── README.md
│
├── synthetic/
│   └── reports/          # Excluded from Git
│
├── tests/
│   ├── test_anomaly_detection.py
│   └── test_lifecycle_integration.py
│
├── validation/
│   ├── check_reproducibility.py
│   ├── validate_data.py
│   ├── validate_foreign_keys.py
│   └── validate_lifecycle.py
│
├── .env.example
├── .gitignore
├── README.md
└── requirements.txt
```

Generated files, virtual environments, local credentials, and database-mutating demonstration scripts are excluded from the public repository.

## Prerequisites

- Python 3.14.6 (the version used in the current development environment).
- MySQL Server 8.0.
- Git.
- MySQL Workbench (optional).

## Local Setup

### 1. Clone the repository

```bash
git clone https://github.com/harimudavath21/Yottaflex.ai.git
cd Yottaflex.ai
```

### 2. Create a virtual environment

For Windows PowerShell:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### 4. Configure environment variables

Create your local `.env` file using `.env.example` as a reference.

Example:

```env
DB_HOST=localhost
DB_USER=your_mysql_username
DB_PASSWORD=your_mysql_password
DB_NAME=your_database_name
```

Replace the placeholders with your own local MySQL configuration.

**Security requirements:**

- Never commit `.env`.
- Never publish database passwords or API keys.
- Do not include production credentials in screenshots, documentation, or issue reports.
- `.env.example` contains placeholders only and can be published.

### 5. Database setup

The database connection configuration is available in:

```text
config/database.py
```

The file `data/database/schema.sql` is currently an empty placeholder. A complete verified schema is not included in this repository yet.

A fresh database therefore cannot be initialized from this file. The database schema must be prepared and verified before setting up a new database.

**Important:** Do not execute incomplete SQL files or run the synthetic-data generator against an already-populated database.

### 6. Run the application

```powershell
streamlit run app.py
```

Streamlit will provide a local URL to access the application in your browser.

## Synthetic Data

The project includes a deterministic synthetic-data generator:

```text
generator/generate_data.py
```

It generates example academic-integrity records, including learners, assessments, reviewers, submissions, similarity reports, and investigation cases.

The generator checks whether its core tables already contain records and aborts when they do.

**Do not run the generator against an existing populated database.** Do not delete existing database records to make it run.

Generated similarity report files are stored under:

```text
synthetic/reports/
```

These generated files are excluded from the public Git repository.

## Data Verification

The following SQL file contains read-only inspection and verification queries:

```text
data/database/seed_data.sql
```

It includes queries for:

- Core record counts.
- Similarity category distribution.
- Investigation case status.
- Reviewer assignment status.
- Similarity score validation.
- Missing decision rationale.
- Evidence metadata validation.
- Appeal resolution timestamps.
- Completed assignment timestamps.

This file is not a data-seeding script. It contains `SELECT` queries and does not insert, update, or delete records.

Run these queries only after selecting the intended database in MySQL Workbench.

## Testing and Validation

The project contains automated tests under:

```text
tests/
```

It also includes validation scripts under:

```text
validation/
```

Examples of checks:

```powershell
python -m compileall app.py config modules validation
pytest tests/ -v
```

Review scripts before execution, especially scripts that connect to MySQL.

Some standalone root-level test scripts demonstrate workflows that modify database records. They are excluded from the public repository and should not be run against a database containing important data.

## Security and Privacy

- Use synthetic or anonymized records in public demonstrations.
- Never publish `.env` or database credentials.
- Do not commit real student submissions or personally identifiable information.
- Do not publish confidential evidence or investigation case details.
- Keep generated reports and temporary files out of the public repository.
- Similarity scores are screening indicators, not proof of misconduct.
- Human review and documented due process are important before recording an outcome.

## Documentation

Additional project documentation:

- [Architecture](docs/architecture.md)
- [Database Overview](docs/database.md)
- [Workflow Guide](docs/workflows.md)
- [Development and Safety Notes](docs/development.md)

## Current Implementation Notes

This project documents the current implementation and development direction.

Authentication, role-based authorization, deployment automation, and production hardening should not be considered complete unless independently verified in the application code.

The current repository is intended for development and demonstration purposes.

## License

A license has not yet been selected. Add a license after deciding the terms under which others may use, modify, and distribute this project.