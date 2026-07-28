# Economic and Political Geography of South Asia

IS529N Semester 2026 Paired Lecture Production Cockpit

The cockpit is a local FastAPI and SQLite application organised around `WeeklyLecturePair`, with Tuesday Part A and Friday Part B shown together. It does not call an AI model, modify historical source files, append the canonical ledger, or perform Git writes.

## Start

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-gui.txt
.venv/bin/uvicorn gui.app:app --host 127.0.0.1 --port 8529
```

Open `http://127.0.0.1:8529/`. Local SQLite state is stored under `gui/database/` and ignored by Git.

The reproducible local validation workflow, including its explicit real-versus-placeholder boundary, is documented in [ACCEPTANCE.md](ACCEPTANCE.md).

Lecture 1 is seeded from authorised source-census metadata only. Historical paths are stored using `<HISTORICAL_RESOURCE_REPOSITORY>` rather than an absolute location. Titles remain pending instructor confirmation, and no substantive academic content is generated automatically.

Lecture titles are controlled through `course/lecture_titles.txt` and `course/lecture_part_titles.txt`. The **Lecture Titles** screen validates and previews registry changes, protects instructor-confirmed titles, exposes historical evidence, and exports confirmed values atomically with ignored local backups.

## Boundaries

- PPTX output is versioned and written into the appropriate lecture-part `deck_source/` directory.
- Provenance sidecars and separate teaching briefs accompany generated decks.
- PDF conversion is permitted only through the locally detected LibreOffice executable.
- Visual validation is heuristic unless a rendered preview is available.
- Draft ledger events are written only beneath `course_ledger/drafts/gui/`.
- Git readiness is read-only; staging, commits, pushes, and publication are disabled.
