PRAGMA foreign_keys = OFF;

ALTER TABLE resource_assignments RENAME TO resource_assignments_v1;
CREATE TABLE resource_assignments (
    id INTEGER PRIMARY KEY,
    resource_id INTEGER NOT NULL REFERENCES resources(id),
    lecture_pair_id INTEGER NOT NULL REFERENCES lecture_pairs(id),
    part TEXT NOT NULL CHECK(part IN (
        'SHARED','A','B','BOTH','SUPPLEMENTARY','UNCLASSIFIED','ARCHIVE_ONLY','EXCLUDED'
    )),
    assigned_by TEXT NOT NULL DEFAULT 'Application',
    updated_at TEXT NOT NULL DEFAULT '',
    UNIQUE(resource_id, lecture_pair_id)
);
INSERT INTO resource_assignments(id,resource_id,lecture_pair_id,part)
SELECT id,resource_id,lecture_pair_id,part FROM resource_assignments_v1;
DROP TABLE resource_assignments_v1;
PRAGMA foreign_keys = ON;

ALTER TABLE resources ADD COLUMN source_type TEXT NOT NULL DEFAULT 'HISTORICAL_FILE';
ALTER TABLE resources ADD COLUMN classification_confidence TEXT NOT NULL DEFAULT 'UNASSESSED';
ALTER TABLE resources ADD COLUMN instructor_status TEXT NOT NULL DEFAULT 'NOT_REVIEWED';
ALTER TABLE resources ADD COLUMN instructor_comment TEXT NOT NULL DEFAULT '';
ALTER TABLE resources ADD COLUMN extraction_status TEXT NOT NULL DEFAULT 'NOT_EXTRACTED';
ALTER TABLE resources ADD COLUMN updated_at TEXT NOT NULL DEFAULT '';
ALTER TABLE resources ADD COLUMN updated_by TEXT NOT NULL DEFAULT 'Application';

ALTER TABLE historical_decks ADD COLUMN extracted_title TEXT NOT NULL DEFAULT '';
ALTER TABLE historical_decks ADD COLUMN inferred_lecture_number TEXT NOT NULL DEFAULT '';
ALTER TABLE historical_decks ADD COLUMN inferred_part TEXT NOT NULL DEFAULT 'REQUIRES_INSPECTION';
ALTER TABLE historical_decks ADD COLUMN source_evidence TEXT NOT NULL DEFAULT '';
ALTER TABLE historical_decks ADD COLUMN confidence TEXT NOT NULL DEFAULT 'UNASSESSED';
ALTER TABLE historical_decks ADD COLUMN sequence_mismatch_warning TEXT NOT NULL DEFAULT '';
ALTER TABLE historical_decks ADD COLUMN instructor_assignment TEXT NOT NULL DEFAULT 'REQUIRES_INSPECTION';
ALTER TABLE historical_decks ADD COLUMN instructor_confirmation_required INTEGER NOT NULL DEFAULT 1;
ALTER TABLE historical_decks ADD COLUMN updated_at TEXT NOT NULL DEFAULT '';
ALTER TABLE historical_decks ADD COLUMN updated_by TEXT NOT NULL DEFAULT 'Application';

ALTER TABLE historical_slides ADD COLUMN layout_name TEXT NOT NULL DEFAULT '';
ALTER TABLE historical_slides ADD COLUMN image_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE historical_slides ADD COLUMN chart_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE historical_slides ADD COLUMN table_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE historical_slides ADD COLUMN speaker_note_available INTEGER NOT NULL DEFAULT 0;
ALTER TABLE historical_slides ADD COLUMN page_status TEXT NOT NULL DEFAULT '';
ALTER TABLE historical_slides ADD COLUMN confidence TEXT NOT NULL DEFAULT 'UNASSESSED';
ALTER TABLE historical_slides ADD COLUMN approval_status TEXT NOT NULL DEFAULT 'WORKING_DRAFT';
ALTER TABLE historical_slides ADD COLUMN updated_at TEXT NOT NULL DEFAULT '';
ALTER TABLE historical_slides ADD COLUMN updated_by TEXT NOT NULL DEFAULT 'Application';

ALTER TABLE revised_notes ADD COLUMN historical_slide_ids TEXT NOT NULL DEFAULT '[]';
ALTER TABLE revised_notes ADD COLUMN verification_status TEXT NOT NULL DEFAULT 'NOT_YET_VERIFIED';
ALTER TABLE revised_notes ADD COLUMN instructor_origin_declared INTEGER NOT NULL DEFAULT 0;
ALTER TABLE revised_notes ADD COLUMN updated_at TEXT NOT NULL DEFAULT '';
ALTER TABLE revised_notes ADD COLUMN updated_by TEXT NOT NULL DEFAULT 'Application';

ALTER TABLE slide_plan_entries ADD COLUMN updated_at TEXT NOT NULL DEFAULT '';
ALTER TABLE slide_plan_entries ADD COLUMN updated_by TEXT NOT NULL DEFAULT 'Application';

ALTER TABLE historical_derivatives ADD COLUMN derivative_status TEXT NOT NULL DEFAULT 'READ_ONLY_DERIVATIVE';
ALTER TABLE historical_derivatives ADD COLUMN extraction_tool TEXT NOT NULL DEFAULT '';

CREATE TABLE IF NOT EXISTS resource_classification_history (
    id INTEGER PRIMARY KEY,
    resource_id INTEGER NOT NULL REFERENCES resources(id),
    lecture_pair_id INTEGER NOT NULL REFERENCES lecture_pairs(id),
    old_part TEXT NOT NULL,
    new_part TEXT NOT NULL,
    old_classification TEXT NOT NULL,
    new_classification TEXT NOT NULL,
    changed_by TEXT NOT NULL,
    changed_at TEXT NOT NULL,
    instructor_comment TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS note_historical_slide_links (
    id INTEGER PRIMARY KEY,
    note_id INTEGER NOT NULL REFERENCES revised_notes(id) ON DELETE CASCADE,
    historical_slide_id INTEGER NOT NULL REFERENCES historical_slides(id),
    created_at TEXT NOT NULL,
    UNIQUE(note_id, historical_slide_id)
);

CREATE TABLE IF NOT EXISTS slide_note_links (
    id INTEGER PRIMARY KEY,
    slide_plan_id INTEGER NOT NULL REFERENCES slide_plan_entries(id) ON DELETE CASCADE,
    note_id INTEGER NOT NULL REFERENCES revised_notes(id),
    created_at TEXT NOT NULL,
    UNIQUE(slide_plan_id, note_id)
);

CREATE TABLE IF NOT EXISTS slide_historical_links (
    id INTEGER PRIMARY KEY,
    slide_plan_id INTEGER NOT NULL REFERENCES slide_plan_entries(id) ON DELETE CASCADE,
    historical_slide_id INTEGER NOT NULL REFERENCES historical_slides(id),
    created_at TEXT NOT NULL,
    UNIQUE(slide_plan_id, historical_slide_id)
);

CREATE INDEX IF NOT EXISTS idx_resource_history_resource ON resource_classification_history(resource_id);
CREATE INDEX IF NOT EXISTS idx_note_historical_note ON note_historical_slide_links(note_id);
CREATE INDEX IF NOT EXISTS idx_slide_note_slide ON slide_note_links(slide_plan_id);
CREATE INDEX IF NOT EXISTS idx_slide_historical_slide ON slide_historical_links(slide_plan_id);
