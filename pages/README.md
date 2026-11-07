# Streamlit Pages Directory

The current AIMS application implements its ten navigation sections inside the root `app.py` file.

This directory is intentionally kept free of duplicate page scripts so that Streamlit does not discover additional pages and create a second navigation system.

If the project is deliberately migrated to Streamlit's native multipage structure in the future:

1. Plan the migration before moving any code.
2. Move one section at a time.
3. Preserve shared database and workflow functions.
4. Test navigation, session state, and all write operations.
5. Remove the old in-file navigation only after the new structure is verified.

Until then, keep this README and leave this directory without page modules.
