ALTER TABLE slide_plan_entries ADD COLUMN source_independence_status TEXT NOT NULL DEFAULT '';
ALTER TABLE slide_plan_entries ADD COLUMN instructor_origin_declaration TEXT NOT NULL DEFAULT '';
ALTER TABLE class_session_records ADD COLUMN retrospective_entry_explanation TEXT NOT NULL DEFAULT '';
ALTER TABLE class_session_records ADD COLUMN updated_at TEXT NOT NULL DEFAULT '';
ALTER TABLE class_session_records ADD COLUMN updated_by TEXT NOT NULL DEFAULT 'Application';

CREATE TABLE IF NOT EXISTS deliverable_bundles (
    id INTEGER PRIMARY KEY,
    lecture_pair_id INTEGER NOT NULL REFERENCES lecture_pairs(id),
    part TEXT NOT NULL CHECK(part IN ('A','B')),
    version TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('DRAFT','REVISED','APPROVED')),
    pptx_path TEXT NOT NULL UNIQUE,
    pptx_sha256 TEXT NOT NULL,
    sidecar_path TEXT NOT NULL,
    teaching_brief_path TEXT NOT NULL,
    pdf_path TEXT NOT NULL DEFAULT '',
    pdf_sha256 TEXT NOT NULL DEFAULT '',
    page_count INTEGER NOT NULL DEFAULT 0,
    thumbnail_directory TEXT NOT NULL DEFAULT '',
    thumbnail_count INTEGER NOT NULL DEFAULT 0,
    rendering_tool TEXT NOT NULL DEFAULT '',
    rendering_warnings TEXT NOT NULL DEFAULT '[]',
    validation_status TEXT NOT NULL DEFAULT 'NOT_RUN',
    validation_report TEXT NOT NULL DEFAULT '{}',
    deck_decision TEXT NOT NULL DEFAULT 'NOT_REVIEWED',
    decision_note TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    approved INTEGER NOT NULL DEFAULT 0,
    UNIQUE(lecture_pair_id, part, version)
);

CREATE TABLE IF NOT EXISTS slide_review_decisions (
    id INTEGER PRIMARY KEY,
    deliverable_bundle_id INTEGER NOT NULL REFERENCES deliverable_bundles(id) ON DELETE CASCADE,
    slide_plan_id INTEGER NOT NULL REFERENCES slide_plan_entries(id),
    decision TEXT NOT NULL,
    instructor_note TEXT NOT NULL DEFAULT '',
    decided_by TEXT NOT NULL DEFAULT 'Instructor',
    decided_at TEXT NOT NULL,
    UNIQUE(deliverable_bundle_id, slide_plan_id)
);

CREATE TABLE IF NOT EXISTS odp_conversion_records (
    id INTEGER PRIMARY KEY,
    deck_id INTEGER NOT NULL REFERENCES historical_decks(id),
    source_symbolic_reference TEXT NOT NULL,
    source_sha256 TEXT NOT NULL,
    source_format TEXT NOT NULL DEFAULT 'ODP',
    conversion_tool TEXT NOT NULL,
    conversion_timestamp TEXT NOT NULL,
    derivative_pdf TEXT NOT NULL UNIQUE,
    derivative_pdf_sha256 TEXT NOT NULL,
    page_count INTEGER NOT NULL,
    derivative_status TEXT NOT NULL DEFAULT 'READ_ONLY_DERIVATIVE'
);

CREATE INDEX IF NOT EXISTS idx_bundle_part ON deliverable_bundles(lecture_pair_id,part,created_at);
CREATE INDEX IF NOT EXISTS idx_slide_review_bundle ON slide_review_decisions(deliverable_bundle_id);
CREATE INDEX IF NOT EXISTS idx_odp_conversion_deck ON odp_conversion_records(deck_id);
