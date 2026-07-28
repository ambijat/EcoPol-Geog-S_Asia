# Economic and Political Geography of South Asia

```yaml
course_code: IS529N
semester: Semester 2026
instructor: Professor Ambrish Dhaka
```

This repository is the controlled working environment for IS529N. It develops instructor-governed course materials from immutable historical sources, explicitly authorised online captures, and verified external evidence.

## Which interface do I use?

This repository contains four interface layers with distinct, non-competing roles:

- **Artifact administration — `desktop/`.** The primary application direction for repository archaeology, path configuration, scanning, candidate review, registration, relationships, and lineage. See [Course Artifact Cockpit](#course-artifact-cockpit) below.
- **Lecture-production workflow — `gui/` (browser cockpit).** The current operational cockpit for the lecture-pair workspace, resource metadata, revised notes, slide planning, PPTX generation, validation, and class records. See [Course Production Cockpit](#course-production-cockpit) below.
- **Native lecture-production migration — `qt_gui/`.** An in-progress native PySide6 reimplementation of the same lecture-production workflow as `gui/`, built for eventual functional parity. `gui/` remains the operational reference and acceptance baseline; `qt_gui/MIGRATION_PLAN.md` reserves any retirement of `gui/` for an explicit instructor ruling that has not been made. Treat the two as parallel, not `gui/`-as-legacy. See [Native Qt Phase 1 cockpit](#native-qt-phase-1-cockpit) below.
- **Historical implementations.** Any prior lecture-first or deliverable-first prototypes preserved only as reference material; they are not academic authorities and do not compete with the three interfaces above.

`desktop/` and the lecture-production layers (`gui/`/`qt_gui/`) solve different problems — artifact administration versus lecture production — and are not alternatives to each other. Do not read either "primary" or "final direction" language below as claiming precedence over the other layer; each phrase is scoped to its own layer.

## Course Artifact Cockpit

The primary application direction for artifact administration is an artifact-first PySide6 desktop cockpit. It begins with discoverable artifacts, provenance, inspection state, and explicit relationships rather than lectures or deliverables. This is a separate concern from lecture production: it does not supersede the browser or Qt lecture-production cockpits below, which remain independently operational for their own workflow (see [Which interface do I use?](#which-interface-do-i-use)).

```bash
.venv/bin/pip install -r requirements-desktop.txt
.venv/bin/python -m desktop.app
```

On Ubuntu, double-click the installed **IS529N Course Artifact Cockpit**
desktop launcher or run:

```bash
./launch_cockpit.sh
```

For a Windows copy of the repository, use `launch_cockpit.bat` after creating
the Windows `.venv`.

The application runs locally without a web server. Its ignored SQLite database
is `local_state/database/course_artifacts.sqlite3`.
See [PyCharm setup](docs/PYCHARM_ARTIFACT_COCKPIT_SETUP.md) and the
[artifact-foundation preservation audit](docs/ARTIFACT_FOUNDATION_AUDIT.md).

Physical artifact roots are configured on first launch and stored only in ignored
`config/local_paths.json`. Artifact records use secure symbolic locators; selecting
a repository folder never scans or ingests it automatically. See
[artifact path configuration](docs/ARTIFACT_PATH_CONFIGURATION.md).
When arranging Lecture Raw Material, use the
[presentation-led dressing manual](docs/PRESENTATION_LED_RAW_MATERIAL_DRESSING_MANUAL.md)
as the standard operating reference.
The complementary country/regional axis is defined in the
[spatial arrangement manual](docs/SPATIAL_RAW_MATERIAL_ARRANGEMENT_MANUAL.md).

Its teleological goal is the finished classroom material from which the instructor teaches. The canonical production unit is:

```text
Lecture N
├── Part A — Tuesday, 9:00 am–11:00 am
└── Part B — Friday, 9:00 am–11:00 am
```

The editable deck, classroom-ready PDF, teaching brief, source map, factual-verification record, and post-class record together form the controlled weekly classroom deliverables. Governance and infrastructure exist to improve their accuracy, usability, traceability, and continuity.

## Authority and boundaries

- The instructor is the sole academic authority.
- Historical and instructor originals are immutable.
- The external historical repository is a strictly read-only source layer.
- Every controlled working derivative is created inside this project and retains its source identity; `sanitised working derivative` is used only when an actual sanitisation process occurred.
- Only instructor-approved materials may be published or used as final course authority.
- Wikidot is a student-facing reference and distribution layer, not the authoritative Semester 2026 archive.
- Git and GitHub record file-level technical evolution across annual course runs.
- The course ledger records academic decisions and actual classroom conduct; Git does not replace it.
- Self-authored project material is freely shareable under CC0 1.0; public exports still exclude private data, credentials, restricted assessments, and imported files.

## Main areas

- `resources/`: controlled source intake, never generated teaching output.
- `resource_registry/`: canonical JSONL registry, capture logs, manifests, and duplicate reports.
- `course/`: working and reviewed course artifacts, separated by function.
- `course/lectures/`: the central 15-week, two-part lecture-production workspace.
- `templates/`: controlled planning, session, verification, and alignment templates.
- `course_ledger/`: append-only academic event chain.
- `scripts/`: registration, ledger, and repository-validation utilities.
- `reports/`: generated technical validation reports.

Start with [resource governance](docs/RESOURCE_GOVERNANCE.md), then follow the [content lifecycle](docs/CONTENT_LIFECYCLE.md). The [Git versioning policy](docs/GIT_VERSIONING_POLICY.md), [public-repository boundary](docs/PUBLIC_REPOSITORY_BOUNDARY.md), and [annual release protocol](docs/ANNUAL_RELEASE_PROTOCOL.md) govern publication. Validate the repository with:

```bash
python3 scripts/validate_course_repository.py
```

No content in this repository is instructor-approved merely because it is present, validated, well formatted, or tracked by Git.

## Course Production Cockpit

The local browser cockpit connects the lecture-pair workspace, authorised resource metadata, revised notes, slide planning, versioned PPTX generation, validation, class records, isolated draft ledger events, and read-only Git readiness.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-gui.txt
.venv/bin/uvicorn gui.app:app --host 127.0.0.1 --port 8529
```

Open `http://127.0.0.1:8529/`. The cockpit does not call an AI service, append the canonical ledger, stage files, commit, or push.

## Native Qt Phase 1 cockpit

`qt_gui/` is the in-progress native PySide6 successor candidate for the lecture-production workflow above, aiming for functional parity with the browser cockpit. The Phase 1 implementation is separate under `qt_gui/`; the browser cockpit (`gui/`) remains its reference implementation, parity baseline, and the current operational lecture-production cockpit until an explicit instructor ruling under `qt_gui/MIGRATION_PLAN.md` Stage C says otherwise. This is a lecture-production migration decision only — it has no bearing on `desktop/`, the separate artifact-administration cockpit above.

```bash
.venv/bin/pip install -r requirements-qt.txt
.venv/bin/python -m qt_gui.app
```

See `qt_gui/README.md`, `qt_gui/ACCEPTANCE.md`, and `qt_gui/MIGRATION_PLAN.md` for scope and migration boundaries.

Qt Phase 3 adds evidence-gated, local-only draft PPTX/PDF production, native preview, validation, instructor review, class records, and isolated draft ledger events. Follow `qt_gui/PHASE3_ACCEPTANCE.md`; generation remains blocked until the instructor completes a real evidence chain.
