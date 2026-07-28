ALTER TABLE lecture_pairs ADD COLUMN title_source TEXT NOT NULL DEFAULT 'PENDING';
ALTER TABLE lecture_pairs ADD COLUMN title_status TEXT NOT NULL DEFAULT 'PENDING';
ALTER TABLE lecture_pairs ADD COLUMN title_confirmed INTEGER NOT NULL DEFAULT 0;
ALTER TABLE lecture_pairs ADD COLUMN title_last_synced_at TEXT NOT NULL DEFAULT '';

ALTER TABLE lecture_parts ADD COLUMN title_source TEXT NOT NULL DEFAULT 'PENDING';
ALTER TABLE lecture_parts ADD COLUMN title_status TEXT NOT NULL DEFAULT 'PENDING';
ALTER TABLE lecture_parts ADD COLUMN title_confirmed INTEGER NOT NULL DEFAULT 0;
ALTER TABLE lecture_parts ADD COLUMN title_last_synced_at TEXT NOT NULL DEFAULT '';

CREATE TABLE IF NOT EXISTS title_evidence (
    id INTEGER PRIMARY KEY,
    lecture_pair_id INTEGER NOT NULL REFERENCES lecture_pairs(id),
    target_identifier TEXT NOT NULL,
    target_classification TEXT NOT NULL,
    source_filename TEXT NOT NULL,
    source_locator TEXT NOT NULL,
    source_sha256 TEXT NOT NULL,
    extracted_title TEXT NOT NULL,
    extraction_method TEXT NOT NULL,
    extraction_confidence TEXT NOT NULL,
    instructor_confirmation_required INTEGER NOT NULL DEFAULT 1,
    UNIQUE(source_sha256, target_identifier, target_classification)
);

CREATE TABLE IF NOT EXISTS title_sync_batches (
    id INTEGER PRIMARY KEY,
    status TEXT NOT NULL DEFAULT 'PROPOSED',
    created_at TEXT NOT NULL,
    applied_at TEXT NOT NULL DEFAULT '',
    source_weekly_file TEXT NOT NULL,
    source_part_file TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS title_sync_proposals (
    id INTEGER PRIMARY KEY,
    batch_id INTEGER NOT NULL REFERENCES title_sync_batches(id) ON DELETE CASCADE,
    target_type TEXT NOT NULL CHECK(target_type IN ('LECTURE_PAIR','LECTURE_PART')),
    target_identifier TEXT NOT NULL,
    current_title TEXT NOT NULL,
    proposed_title TEXT NOT NULL,
    conflict INTEGER NOT NULL DEFAULT 0,
    reason TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS title_registry_conflicts (
    id INTEGER PRIMARY KEY,
    batch_id INTEGER NOT NULL REFERENCES title_sync_batches(id),
    target_identifier TEXT NOT NULL,
    protected_title TEXT NOT NULL,
    proposed_title TEXT NOT NULL,
    resolution_status TEXT NOT NULL DEFAULT 'REVIEW_REQUIRED',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_title_evidence_pair ON title_evidence(lecture_pair_id);
CREATE INDEX IF NOT EXISTS idx_title_sync_proposals_batch ON title_sync_proposals(batch_id);
