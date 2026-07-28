# Local Acceptance Procedure

This procedure validates the course-production cockpit without adopting course content, accessing historical source bytes, appending the canonical ledger, or publishing the repository.

## Real capabilities

- persistent SQLite migrations and foreign keys;
- 15 weekly lecture pairs with Tuesday Part A and Friday Part B;
- Lecture 1 census-metadata browsing and classification;
- note provenance, slide planning, individual approval decisions, and part approval gates;
- versioned PPTX, provenance sidecar, teaching brief, PDF, and thumbnail generation;
- post-class record forms, isolated draft-event preparation, and read-only Git readiness;
- explicit public-candidate/local-private classification.

## Placeholders and bounded limitations

- lecture titles and substantive academic claims remain instructor-supplied;
- historical slide previews and text extracts are manually registered; the cockpit does not open or extract source-repository files;
- rendered layout validation is evidenced by PDF/thumbnails, but automated overflow geometry remains heuristic;
- AI generation, automatic Git writes, publication, and canonical-ledger append are disabled.

## Reproduce

```bash
.venv/bin/python -m unittest discover -s gui/tests -v
.venv/bin/python -m gui.acceptance_fixture
.venv/bin/uvicorn gui.app:app --host 127.0.0.1 --port 8529
.venv/bin/python -m gui.capture_screenshots
```

Open the local URL printed by the server and inspect the dashboard, Lecture 1 workspace, resource browser, historical-deck browser, revised notes, slide plan, deliverables, class record, and governance readiness screens.

Open **Lecture Titles**, verify that 15 weekly and 30 part records are present, select **Reload lecture titles** to preview changes, inspect any conflicts, and confirm only the non-conflicting synchronization. A title is not instructor-confirmed until its checkbox is explicitly selected and saved.

Fixture outputs and browser screenshots belong under `reports/gui_acceptance/`. They are local-only evidence excluded from the public candidate manifest. The fixture generator refuses to overwrite an existing evidence directory; use a fresh `--output` path for another run.
