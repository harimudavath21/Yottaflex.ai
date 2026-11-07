# Development and Repository Safety

## Local development

Run the application from the project root after activating the existing virtual environment and configuring MySQL:

```powershell
streamlit run app.py
```

Install dependencies with:

```powershell
python -m pip install -r requirements.txt
```

## Before committing

- Check `git status`.
- Confirm `.env` is ignored.
- Confirm no passwords, tokens, private keys, or connection strings are staged.
- Review generated JSON report files and ensure they contain only synthetic data.
- Do not commit real learner submissions, evidence, or confidential case records.
- Check that the README setup instructions match the actual project files.
- Review large files before pushing.

## Test safety

Not every file named `test_*.py` is necessarily a non-mutating unit test. Some project scripts exercise workflows that create evidence, decisions, or appeals in MySQL.

Before running a script, inspect its code for `INSERT`, `UPDATE`, `DELETE`, `commit()`, and calls into write-enabled workflow functions. Prefer a disposable test database for integration tests.

## Database safety

- Never run a reset/drop script against the existing project database without a verified backup and explicit approval.
- Do not rerun the synthetic-data generator on a populated database.
- Do not treat `seed_data.sql` as a data-import script; the supplied file contains read-only inspection queries.
- Keep schema changes separate from documentation-only changes.

## Streamlit page organization

The current application has its ten sections in `app.py` and uses its own navigation control. The `pages/` folder is therefore kept as documentation-only in this package. Do not add duplicate page scripts unless you intentionally migrate to Streamlit's native multipage architecture and test the navigation changes.
