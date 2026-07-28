CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS lecture_pairs (
    id INTEGER PRIMARY KEY,
    lecture_id TEXT NOT NULL UNIQUE,
    lecture_number INTEGER NOT NULL UNIQUE,
    week INTEGER NOT NULL,
    weekly_title TEXT NOT NULL,
    weekly_central_question TEXT NOT NULL DEFAULT '',
    weekly_argument TEXT NOT NULL DEFAULT '',
    relationship_between_parts TEXT NOT NULL DEFAULT '',
    concepts_introduced_in_a TEXT NOT NULL DEFAULT '',
    applications_developed_in_b TEXT NOT NULL DEFAULT '',
    shared_resources TEXT NOT NULL DEFAULT '',
    duplication_warnings TEXT NOT NULL DEFAULT '',
    unresolved_gaps TEXT NOT NULL DEFAULT '',
    assessment_alignment TEXT NOT NULL DEFAULT '',
    instructor_status TEXT NOT NULL DEFAULT 'NOT_REVIEWED',
    lifecycle_status TEXT NOT NULL DEFAULT 'UNMAPPED'
);

CREATE TABLE IF NOT EXISTS lecture_parts (
    id INTEGER PRIMARY KEY,
    lecture_pair_id INTEGER NOT NULL REFERENCES lecture_pairs(id),
    part TEXT NOT NULL CHECK(part IN ('A','B')),
    identifier TEXT NOT NULL UNIQUE,
    scheduled_day TEXT NOT NULL,
    scheduled_time TEXT NOT NULL,
    title TEXT NOT NULL,
    lifecycle_status TEXT NOT NULL DEFAULT 'UNMAPPED',
    fidelity_status TEXT NOT NULL DEFAULT 'F0',
    approval_status TEXT NOT NULL DEFAULT 'NOT_REVIEWED',
    class_status TEXT NOT NULL DEFAULT 'NOT_CONDUCTED',
    UNIQUE(lecture_pair_id, part)
);

CREATE TABLE IF NOT EXISTS resources (
    id INTEGER PRIMARY KEY,
    resource_id TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    source_locator TEXT NOT NULL,
    provenance TEXT NOT NULL,
    source_layer TEXT NOT NULL,
    file_type TEXT NOT NULL,
    historical_status TEXT NOT NULL,
    source_quality TEXT NOT NULL DEFAULT 'UNASSESSED',
    factual_currency_status TEXT NOT NULL DEFAULT 'UNVERIFIED',
    intended_use TEXT NOT NULL DEFAULT '',
    copyright_status TEXT NOT NULL DEFAULT 'REVIEW_REQUIRED',
    verification_status TEXT NOT NULL DEFAULT 'NOT_STARTED',
    content_sha256 TEXT NOT NULL DEFAULT '',
    classification TEXT NOT NULL DEFAULT 'UNCLASSIFIED',
    centrality TEXT NOT NULL DEFAULT 'SUPPORTING',
    excluded INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS resource_assignments (
    id INTEGER PRIMARY KEY,
    resource_id INTEGER NOT NULL REFERENCES resources(id),
    lecture_pair_id INTEGER NOT NULL REFERENCES lecture_pairs(id),
    part TEXT NOT NULL CHECK(part IN ('SHARED','A','B','BOTH','UNCLASSIFIED')),
    UNIQUE(resource_id, lecture_pair_id)
);

CREATE TABLE IF NOT EXISTS historical_decks (
    id INTEGER PRIMARY KEY,
    deck_id TEXT NOT NULL UNIQUE,
    lecture_pair_id INTEGER NOT NULL REFERENCES lecture_pairs(id),
    title TEXT NOT NULL,
    source_locator TEXT NOT NULL,
    file_type TEXT NOT NULL,
    source_layer TEXT NOT NULL,
    content_sha256 TEXT NOT NULL,
    read_only INTEGER NOT NULL DEFAULT 1,
    discovery_status TEXT NOT NULL DEFAULT 'METADATA_ONLY'
);

CREATE TABLE IF NOT EXISTS historical_slides (
    id INTEGER PRIMARY KEY,
    historical_slide_id TEXT NOT NULL UNIQUE,
    deck_id INTEGER NOT NULL REFERENCES historical_decks(id),
    historical_slide_number INTEGER NOT NULL,
    title TEXT NOT NULL DEFAULT '',
    visual_preview TEXT NOT NULL DEFAULT '',
    text_extract TEXT NOT NULL DEFAULT '',
    current_status TEXT NOT NULL DEFAULT 'VERIFY',
    reason TEXT NOT NULL DEFAULT '',
    factual_update_required INTEGER NOT NULL DEFAULT 0,
    visual_update_required INTEGER NOT NULL DEFAULT 0,
    target_part TEXT NOT NULL DEFAULT '',
    target_sequence INTEGER,
    linked_resource_ids TEXT NOT NULL DEFAULT '[]',
    linked_note_ids TEXT NOT NULL DEFAULT '[]',
    instructor_comment TEXT NOT NULL DEFAULT '',
    UNIQUE(deck_id, historical_slide_number)
);

CREATE TABLE IF NOT EXISTS revised_notes (
    id INTEGER PRIMARY KEY,
    note_id TEXT NOT NULL UNIQUE,
    lecture_pair_id INTEGER NOT NULL REFERENCES lecture_pairs(id),
    part TEXT NOT NULL CHECK(part IN ('A','B','SHARED')),
    topic TEXT NOT NULL,
    claim TEXT NOT NULL,
    explanation TEXT NOT NULL DEFAULT '',
    evidence TEXT NOT NULL DEFAULT '',
    source_ids TEXT NOT NULL DEFAULT '[]',
    date_relevance TEXT NOT NULL DEFAULT '',
    confidence TEXT NOT NULL DEFAULT 'UNVERIFIED',
    teaching_function TEXT NOT NULL,
    suggested_slide TEXT NOT NULL DEFAULT '',
    created_by TEXT NOT NULL,
    note_origin TEXT NOT NULL,
    instructor_status TEXT NOT NULL DEFAULT 'NOT_REVIEWED'
);

CREATE TABLE IF NOT EXISTS slide_plan_entries (
    id INTEGER PRIMARY KEY,
    slide_id TEXT NOT NULL UNIQUE,
    lecture_pair_id INTEGER NOT NULL REFERENCES lecture_pairs(id),
    part TEXT NOT NULL CHECK(part IN ('A','B')),
    sequence INTEGER NOT NULL,
    title TEXT NOT NULL,
    purpose TEXT NOT NULL,
    action TEXT NOT NULL DEFAULT 'ADD',
    historical_slide_sources TEXT NOT NULL DEFAULT '[]',
    note_ids TEXT NOT NULL DEFAULT '[]',
    resource_ids TEXT NOT NULL DEFAULT '[]',
    visual_type TEXT NOT NULL DEFAULT 'CONCEPT',
    visual_asset_path TEXT NOT NULL DEFAULT '',
    speaker_note TEXT NOT NULL DEFAULT '',
    citation_footer TEXT NOT NULL DEFAULT '',
    verification_status TEXT NOT NULL DEFAULT 'NOT_STARTED',
    approval_status TEXT NOT NULL DEFAULT 'NOT_REVIEWED',
    UNIQUE(lecture_pair_id, part, sequence)
);

CREATE TABLE IF NOT EXISTS deliverables (
    id INTEGER PRIMARY KEY,
    lecture_pair_id INTEGER NOT NULL REFERENCES lecture_pairs(id),
    part TEXT NOT NULL CHECK(part IN ('A','B')),
    deliverable_type TEXT NOT NULL,
    version TEXT NOT NULL,
    status TEXT NOT NULL,
    relative_path TEXT NOT NULL UNIQUE,
    sidecar_path TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    approved INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS verification_records (
    id INTEGER PRIMARY KEY,
    lecture_pair_id INTEGER NOT NULL REFERENCES lecture_pairs(id),
    part TEXT NOT NULL CHECK(part IN ('A','B')),
    status TEXT NOT NULL DEFAULT 'NOT_STARTED',
    unresolved_high_risk_claims INTEGER NOT NULL DEFAULT 0,
    report_json TEXT NOT NULL DEFAULT '{}',
    updated_at TEXT NOT NULL,
    UNIQUE(lecture_pair_id, part)
);

CREATE TABLE IF NOT EXISTS class_session_records (
    id INTEGER PRIMARY KEY,
    session_id TEXT NOT NULL UNIQUE,
    lecture_pair_id INTEGER NOT NULL REFERENCES lecture_pairs(id),
    part TEXT NOT NULL CHECK(part IN ('A','B')),
    scheduled_date TEXT NOT NULL DEFAULT '',
    actual_date TEXT NOT NULL DEFAULT '',
    slides_planned TEXT NOT NULL DEFAULT '',
    slides_covered TEXT NOT NULL DEFAULT '',
    slides_omitted TEXT NOT NULL DEFAULT '',
    oral_material_added TEXT NOT NULL DEFAULT '',
    student_questions TEXT NOT NULL DEFAULT '',
    conceptual_difficulties TEXT NOT NULL DEFAULT '',
    time_management TEXT NOT NULL DEFAULT '',
    topics_deferred TEXT NOT NULL DEFAULT '',
    follow_up_actions TEXT NOT NULL DEFAULT '',
    impact_on_next_session TEXT NOT NULL DEFAULT '',
    instructor_validation_status TEXT NOT NULL DEFAULT 'NOT_REVIEWED',
    UNIQUE(lecture_pair_id, part)
);

CREATE TABLE IF NOT EXISTS draft_ledger_events (
    id INTEGER PRIMARY KEY,
    event_id TEXT NOT NULL UNIQUE,
    lecture_pair_id INTEGER NOT NULL REFERENCES lecture_pairs(id),
    event_type TEXT NOT NULL,
    approval_status TEXT NOT NULL DEFAULT 'DRAFT',
    relative_path TEXT NOT NULL UNIQUE,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS git_readiness_reports (
    id INTEGER PRIMARY KEY,
    lecture_pair_id INTEGER NOT NULL REFERENCES lecture_pairs(id),
    generated_at TEXT NOT NULL,
    branch TEXT NOT NULL,
    latest_commit TEXT NOT NULL,
    modified_count INTEGER NOT NULL,
    untracked_count INTEGER NOT NULL,
    validation_state TEXT NOT NULL,
    report_json TEXT NOT NULL
);
