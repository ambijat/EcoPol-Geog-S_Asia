# Artifact Foundation — Stage 0 Preservation Audit

## Architectural ruling

The inherited implementation is lecture-first. It remains preserved under
`gui/` and `qt_gui/` as a reference implementation. The new artifact-domain
source uses the neutral internal package path `course_artifacts/`, and the
primary interface adapter begins under `desktop/`. This package name is not a
course concept or product identity. No inherited files are relocated or deleted
in the first implementation cycle.

## Reusable technical components

- `gui/database.py` demonstrates ordered SQLite migrations, foreign-key activation, and repeatable seeds.
- `qt_gui/database/connection.py` demonstrates short-lived SQLite connections.
- `qt_gui/models/table_model.py` provides a reusable pattern for dictionary-backed Qt table models.
- `qt_gui/widgets/watermark_container.py` provides a safe decorative SVG renderer.
- `qt_gui/services/pdf_service.py` contains read-only PDF metadata, text, and thumbnail inspection patterns.
- `qt_gui/services/pptx_service.py` contains read-only `python-pptx` inspection patterns.
- `qt_gui/services/historical_deck_service.py` preserves checksum-bound ODP conversion and source immutability checks.
- `qt_gui/resources/styles/application.qss` supplies the restrained scholarly colour and typography baseline.

These are patterns or later-stage candidates for adaptation. The new artifact
domain does not import lecture services.

## Domain logic embedded in inherited GUI code

- `qt_gui/main_window.py` constructs lecture services and fixes lecture workflows directly into navigation.
- `qt_gui/views/dashboard_view.py` assumes 15 lecture cards are the application root.
- `qt_gui/views/resource_cluster_view.py` assigns resources only through a lecture and part.
- `qt_gui/views/historical_deck_view.py` mixes inspection, lecture assignment, slide classification, and instructor decisions in one view.
- `gui/app.py` binds business operations directly to lecture-oriented HTTP routes.

These modules remain reference implementations and are not extended by the artifact-first cycle.

## Data preservation and compatibility

- New migrations retain the internal compatibility table
  `course_artifact_schema_migrations`, avoiding collision with inherited
  `schema_migrations`.
- New artifact tables do not reference inherited lecture tables.
- A synthetic migration test opens a database containing a legacy
  `lecture_pairs` table, adds artifact tables, and confirms that the legacy row
  survives.
- Future legacy mapping is isolated behind `artifact_legacy_links` and requires preview and supervised acceptance.

## Source repository boundary

The first cycle performs no repository scan or mass import. Artifact registration opens a selected file only for metadata and SHA-256 calculation. A filesystem test verifies that source bytes and modification time remain unchanged.

Absolute physical paths stay in the ignored local SQLite database. Browser-safe projections remove `physical_path` and retain symbolic locators.

## Current working tree

The repository had extensive pre-existing uncommitted and untracked content before the reset. No unrelated working-tree change is committed, reverted, or rewritten by this implementation.
