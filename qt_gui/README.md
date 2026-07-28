# Native Qt Course Production Cockpit

This is the Phase 1 PySide6 desktop interface for **Economic and Political Geography of South Asia**, course code IS529N, Semester 2026. It is local and offline. It contains no AI client, remote-storage integration, Git write command, or canonical-ledger append control.

## Launch

```bash
.venv/bin/pip install -r requirements-qt.txt
.venv/bin/python -m qt_gui.app
```

The application uses the existing ignored local SQLite database by default. Override it only with an ignored machine-local path: `.venv/bin/python -m qt_gui.app --database qt_gui/local_state/cockpit.sqlite3`.

Implemented in Phase 1: native main window, course header, eleven-item navigation, 15-card dashboard, controlled title manager, paired Lecture workspace, read-only governance status, shared-schema adapters, and explicit Phase 2 placeholders.

The FastAPI/Jinja implementation under `gui/` remains the operational reference and acceptance baseline. It has not been deleted, moved, or renamed.

## Phase 2 workflow

The native cockpit now implements the bounded preparation chain:

`Lecture pair → Resource cluster → Historical deck inspection → Revised notes → Slide revision plan`

Resources are displayed with symbolic locators. The physical mapping is read from the ignored `config/public_projection_paths.local.json` or the `IS529N_HISTORICAL_RESOURCE_REPOSITORY` environment variable and is never stored in the live records. PDF inspection uses `pdfinfo`, `pdftotext`, and `pdftoppm`; PPTX inspection uses `python-pptx`. OCR is deliberately disabled.

Phase 2 working records and derivatives are local-only. See `PHASE2_ACCEPTANCE.md` for the supervised Lecture 1A acceptance sequence.

## Phase 3 workflow

Phase 3 adds a gated local transition from an accepted evidence chain to versioned draft PPTX, PDF, thumbnails, preview, validation, instructor review, class records, and isolated draft ledger events. Real generation stays disabled until the persisted evidence gate passes. Approved generation additionally requires verified and instructor-approved slides plus an F4 lecture part.

ODP inspection uses a checksum-protected LibreOffice headless conversion to an ignored PDF derivative. The resulting rendering is evidence of the PDF appearance only; it is not represented as native ODP-object fidelity.

See `PHASE3_ACCEPTANCE.md` and `docs/DELIVERABLE_VERSIONING_POLICY.md` before producing a real Lecture 1 draft.

## Phase 4 workflow

Phase 4 adds topic-wise three-way triangulation across the historical classroom deck, raw scholarly or empirical resources, and the Wikidot student-learning layer. Findings and recommendations remain advisory until explicit instructor confirmation. Registry candidates are prepared separately and never enter the canonical registry automatically.

The fixed weekly allocation is Tuesday Part A and Friday Part B, both 9:00–11:00. High-fidelity inherited titles do not require routine reconfirmation. See `PHASE4_TRIANGULATION.md` and `docs/INSTRUCTOR_OPERATING_MANUAL.md`.
