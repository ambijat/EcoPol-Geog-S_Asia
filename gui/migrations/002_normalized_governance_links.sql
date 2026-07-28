CREATE TABLE IF NOT EXISTS note_source_links (
    id INTEGER PRIMARY KEY,
    note_id INTEGER NOT NULL REFERENCES revised_notes(id) ON DELETE CASCADE,
    resource_id INTEGER NOT NULL REFERENCES resources(id),
    link_role TEXT NOT NULL DEFAULT 'EVIDENCE_SOURCE',
    created_at TEXT NOT NULL,
    UNIQUE(note_id, resource_id, link_role)
);

CREATE TABLE IF NOT EXISTS slide_source_links (
    id INTEGER PRIMARY KEY,
    slide_plan_id INTEGER NOT NULL REFERENCES slide_plan_entries(id) ON DELETE CASCADE,
    resource_id INTEGER NOT NULL REFERENCES resources(id),
    link_role TEXT NOT NULL DEFAULT 'CITATION_SOURCE',
    created_at TEXT NOT NULL,
    UNIQUE(slide_plan_id, resource_id, link_role)
);

CREATE TABLE IF NOT EXISTS approval_decisions (
    id INTEGER PRIMARY KEY,
    lecture_pair_id INTEGER NOT NULL REFERENCES lecture_pairs(id),
    object_type TEXT NOT NULL CHECK(object_type IN ('SLIDE_PLAN_ENTRY','LECTURE_PART')),
    object_id INTEGER NOT NULL,
    decision TEXT NOT NULL,
    comment TEXT NOT NULL DEFAULT '',
    decided_by TEXT NOT NULL DEFAULT 'INSTRUCTOR',
    decided_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS historical_derivatives (
    id INTEGER PRIMARY KEY,
    deck_id INTEGER NOT NULL REFERENCES historical_decks(id),
    historical_slide_id INTEGER REFERENCES historical_slides(id),
    derivative_type TEXT NOT NULL CHECK(derivative_type IN ('PREVIEW','TEXT_EXTRACT')),
    relative_path TEXT NOT NULL UNIQUE,
    source_locator TEXT NOT NULL,
    source_sha256 TEXT NOT NULL,
    generated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_note_source_links_note ON note_source_links(note_id);
CREATE INDEX IF NOT EXISTS idx_slide_source_links_slide ON slide_source_links(slide_plan_id);
CREATE INDEX IF NOT EXISTS idx_approval_decisions_object ON approval_decisions(object_type, object_id);
CREATE INDEX IF NOT EXISTS idx_historical_derivatives_deck ON historical_derivatives(deck_id);
