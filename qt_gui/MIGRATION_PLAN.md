# Browser-to-Qt Migration Plan

## Stage A — Functional parity

Phase 1 establishes the shared database adapter, native shell, dashboard, title governance, paired workspace, and governance inspection. Phase 2 replaces each placeholder with native resource, deck, note, slide-plan, deliverable, class-record, and preview workflows while retaining browser tests as parity checks.

## Stage B — Instructor acceptance

Run Lecture 1 end to end in Qt: title review, resource classification, historical-slide inspection, note entry, slide plan, draft PPTX, PDF preview, validation, post-class record, and isolated draft event.

## Stage C — Retirement decision

Only an explicit instructor ruling may classify `gui/` as `ARCHIVED_REFERENCE_IMPLEMENTATION`. Do not delete it automatically. Preserve its tests, documentation, screenshots, and Git context.

## Intentional Phase 2 differences

- Qt uses `QTableView` models and explicit detail editors instead of HTML forms.
- Evidence relationships use normalized link tables while retaining legacy JSON identifier fields for browser compatibility.
- A save button is the transaction boundary; unsubmitted form state is cancellable and never written automatically.
- Historical inspection resolves symbolic locators only in memory and records local derivatives without exposing physical paths.
- The Qt interface makes provisional verification and approval status visible but does not provide final deck or lecture approval in Phase 2.
- The browser routes remain enabled and continue to use the same migrations and live SQLite schema.

## Intentional Phase 3 differences

- Qt removes the browser cockpit's direct approved-generation option from ordinary draft production and exposes the evidence gate first.
- Deliverables are managed as checksum-bound bundles with rendering, preview, validation, and review state.
- Class completion has explicit date and retrospective-explanation safeguards.
- Qt draft ledger events are written only below `course_ledger/drafts/qt/`; no canonical append code is exposed.
