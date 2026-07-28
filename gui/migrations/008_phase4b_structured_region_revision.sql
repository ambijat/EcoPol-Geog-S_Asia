ALTER TABLE revised_notes ADD COLUMN review_status TEXT NOT NULL DEFAULT 'NOT_YET_REVIEWED';

ALTER TABLE slide_plan_entries ADD COLUMN revision_status TEXT NOT NULL DEFAULT 'ACTIVE';
ALTER TABLE slide_plan_entries ADD COLUMN generation_sequence INTEGER NOT NULL DEFAULT 0;
ALTER TABLE slide_plan_entries ADD COLUMN supersedes_slide_ids TEXT NOT NULL DEFAULT '[]';

ALTER TABLE candidate_registry_records ADD COLUMN candidate_role TEXT NOT NULL DEFAULT '';
ALTER TABLE candidate_registry_records ADD COLUMN record_function TEXT NOT NULL DEFAULT '';

ALTER TABLE student_learning_packages ADD COLUMN local_note_ids TEXT NOT NULL DEFAULT '[]';

ALTER TABLE deliverable_bundles ADD COLUMN visibility TEXT NOT NULL DEFAULT 'PRIVATE';
ALTER TABLE deliverable_bundles ADD COLUMN classroom_use_status TEXT NOT NULL DEFAULT 'NOT_FOR_CLASSROOM_USE';

CREATE TABLE IF NOT EXISTS local_student_notes (
    id INTEGER PRIMARY KEY,
    local_note_id TEXT NOT NULL UNIQUE,
    lecture_pair_id INTEGER NOT NULL REFERENCES lecture_pairs(id),
    part TEXT NOT NULL CHECK(part IN ('A','B')),
    title TEXT NOT NULL,
    relative_path TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'DRAFT_NOT_FOR_STUDENT_USE',
    review_status TEXT NOT NULL DEFAULT 'REQUIRES_INSTRUCTOR_REVIEW',
    published INTEGER NOT NULL DEFAULT 0,
    website_synced INTEGER NOT NULL DEFAULT 0,
    source_ids TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_local_student_notes_lecture
ON local_student_notes(lecture_pair_id,part);

CREATE TABLE IF NOT EXISTS slide_supersession_records (
    id INTEGER PRIMARY KEY,
    original_slide_plan_id INTEGER NOT NULL REFERENCES slide_plan_entries(id),
    original_slide_id TEXT NOT NULL UNIQUE,
    prior_content_json TEXT NOT NULL,
    prior_content_sha256 TEXT NOT NULL,
    supersession_status TEXT NOT NULL,
    replacement_slide_ids TEXT NOT NULL,
    created_at TEXT NOT NULL
);
