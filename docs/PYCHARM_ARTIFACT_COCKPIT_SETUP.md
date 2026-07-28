# PyCharm Setup — Course Artifact Cockpit

The primary application is a local PySide6 desktop program. It does not require FastAPI, Uvicorn, a browser, or a network connection.

## Configure the project

1. In PyCharm, select **Open** and choose the repository root.
2. Create a virtual environment at `.venv` using Python 3.12.
3. Open **Settings → Project → Python Interpreter** and select `.venv/bin/python`.
4. Install the pinned dependencies:

   ```bash
   .venv/bin/pip install -r requirements-desktop.txt
   ```

5. Mark the repository root as **Sources Root** and use it as the working directory.
6. PyCharm normally adds a Sources Root to `PYTHONPATH`. If it does not, add the repository root to `PYTHONPATH` in the run configuration.

## Application run configuration

Create a **Python** run configuration with:

- Name: `IS529N Course Artifact Cockpit`
- Module name: `desktop.app`
- Working directory: the repository root
- Python interpreter: `.venv/bin/python`

Equivalent terminal commands:

```bash
.venv/bin/python -m desktop.app
.venv/bin/python desktop/app.py
```

The ignored live database is
`local_state/database/course_artifacts.sqlite3`. Override it for an isolated run with:

```bash
.venv/bin/python -m desktop.app --database local_state/database/course-artifacts-test.sqlite3
```

Physical artifact roots are stored separately in ignored `config/local_paths.json`.
On first launch, configure them in the native wizard or later through
**Artifact Repository Paths**. The committed example contains no machine paths.

## Test configuration

Create a **Python tests → Unittests** configuration with:

- Target: repository `tests` directory
- Working directory: repository root
- Environment variable: `QT_QPA_PLATFORM=offscreen`

Equivalent command:

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/python -m unittest discover -s tests -v
```

Headless mode is only for automated GUI tests. Do not set `QT_QPA_PLATFORM=offscreen` for normal desktop use.

## Application boundaries

The desktop application writes only to ignored local working areas. Source repositories are read-only. The browser sidecar is optional and never starts automatically.
