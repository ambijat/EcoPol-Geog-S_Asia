CREATE TABLE IF NOT EXISTS artifact_classes (
    id INTEGER PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    label TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    icon TEXT NOT NULL DEFAULT '',
    display_order INTEGER NOT NULL,
    active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)),
    accepted_extensions TEXT NOT NULL DEFAULT '[]',
    default_relationship_suggestions TEXT NOT NULL DEFAULT '[]',
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS artifacts (
    id INTEGER PRIMARY KEY,
    artifact_id TEXT NOT NULL UNIQUE,
    artifact_class_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    display_name TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    canonical_locator TEXT NOT NULL DEFAULT '',
    symbolic_locator TEXT NOT NULL DEFAULT '',
    physical_path TEXT NOT NULL DEFAULT '',
    file_name TEXT NOT NULL DEFAULT '',
    file_extension TEXT NOT NULL DEFAULT '',
    mime_type TEXT NOT NULL DEFAULT '',
    checksum_sha256 TEXT NOT NULL DEFAULT '',
    file_size INTEGER NOT NULL DEFAULT 0,
    created_time TEXT NOT NULL DEFAULT '',
    modified_time TEXT NOT NULL DEFAULT '',
    source_repository TEXT NOT NULL DEFAULT '',
    provenance TEXT NOT NULL DEFAULT '',
    creator_or_origin TEXT NOT NULL DEFAULT '',
    course_relevance TEXT NOT NULL DEFAULT '',
    access_status TEXT NOT NULL DEFAULT 'LOCAL_ONLY',
    inspection_status TEXT NOT NULL DEFAULT 'UNINSPECTED',
    extraction_status TEXT NOT NULL DEFAULT 'NOT_EXTRACTED',
    review_status TEXT NOT NULL DEFAULT 'NOT_REVIEWED',
    instructor_status TEXT NOT NULL DEFAULT 'AWAITING_REVIEW',
    version_label TEXT NOT NULL DEFAULT '',
    parent_artifact_id INTEGER,
    supersedes_artifact_id INTEGER,
    notes TEXT NOT NULL DEFAULT '',
    archived INTEGER NOT NULL DEFAULT 0 CHECK(archived IN (0,1)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(artifact_class_id) REFERENCES artifact_classes(id),
    FOREIGN KEY(parent_artifact_id) REFERENCES artifacts(id),
    FOREIGN KEY(supersedes_artifact_id) REFERENCES artifacts(id)
);

CREATE TABLE IF NOT EXISTS artifact_locations (
    id INTEGER PRIMARY KEY,
    artifact_id INTEGER NOT NULL,
    symbolic_root TEXT NOT NULL,
    relative_locator TEXT NOT NULL DEFAULT '',
    physical_path TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'AVAILABLE',
    checked_at TEXT NOT NULL DEFAULT '',
    FOREIGN KEY(artifact_id) REFERENCES artifacts(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS artifact_versions (
    id INTEGER PRIMARY KEY,
    artifact_id INTEGER NOT NULL,
    version_artifact_id INTEGER NOT NULL,
    sequence INTEGER NOT NULL,
    version_label TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    UNIQUE(artifact_id, version_artifact_id),
    FOREIGN KEY(artifact_id) REFERENCES artifacts(id),
    FOREIGN KEY(version_artifact_id) REFERENCES artifacts(id)
);

CREATE TABLE IF NOT EXISTS relationship_types (
    id INTEGER PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    label TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    default_directionality TEXT NOT NULL DEFAULT 'DIRECTED',
    active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS artifact_relationships (
    id INTEGER PRIMARY KEY,
    relationship_id TEXT NOT NULL UNIQUE,
    source_artifact_id INTEGER NOT NULL,
    target_artifact_id INTEGER NOT NULL,
    relationship_type_id INTEGER NOT NULL,
    directionality TEXT NOT NULL,
    status TEXT NOT NULL,
    confidence TEXT NOT NULL,
    evidence TEXT NOT NULL DEFAULT '',
    instructor_note TEXT NOT NULL DEFAULT '',
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL,
    reviewed_by TEXT NOT NULL DEFAULT '',
    reviewed_at TEXT NOT NULL DEFAULT '',
    CHECK(source_artifact_id <> target_artifact_id),
    FOREIGN KEY(source_artifact_id) REFERENCES artifacts(id),
    FOREIGN KEY(target_artifact_id) REFERENCES artifacts(id),
    FOREIGN KEY(relationship_type_id) REFERENCES relationship_types(id)
);

CREATE TABLE IF NOT EXISTS instructor_decisions (
    id INTEGER PRIMARY KEY,
    decision_id TEXT NOT NULL UNIQUE,
    decision_type TEXT NOT NULL,
    subject_type TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    summary TEXT NOT NULL,
    detail TEXT NOT NULL DEFAULT '',
    state TEXT NOT NULL DEFAULT 'PENDING',
    resolution_note TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    resolved_at TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS scan_sessions (
    id INTEGER PRIMARY KEY,
    scan_id TEXT NOT NULL UNIQUE,
    symbolic_root TEXT NOT NULL,
    physical_root TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING',
    started_at TEXT NOT NULL,
    completed_at TEXT NOT NULL DEFAULT '',
    file_count INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS scan_candidates (
    id INTEGER PRIMARY KEY,
    scan_session_id INTEGER NOT NULL,
    candidate_id TEXT NOT NULL UNIQUE,
    relative_path TEXT NOT NULL,
    file_extension TEXT NOT NULL DEFAULT '',
    checksum_sha256 TEXT NOT NULL DEFAULT '',
    file_size INTEGER NOT NULL DEFAULT 0,
    candidate_status TEXT NOT NULL DEFAULT 'AWAITING_REVIEW',
    proposed_class_code TEXT NOT NULL DEFAULT '',
    registered_artifact_id INTEGER,
    FOREIGN KEY(scan_session_id) REFERENCES scan_sessions(id),
    FOREIGN KEY(registered_artifact_id) REFERENCES artifacts(id)
);

CREATE TABLE IF NOT EXISTS application_settings (
    setting_key TEXT PRIMARY KEY,
    setting_value TEXT NOT NULL,
    local_only INTEGER NOT NULL DEFAULT 1 CHECK(local_only IN (0,1)),
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS artifact_legacy_links (
    id INTEGER PRIMARY KEY,
    artifact_id INTEGER NOT NULL,
    legacy_entity_type TEXT NOT NULL,
    legacy_entity_id TEXT NOT NULL,
    mapping_status TEXT NOT NULL DEFAULT 'CANDIDATE',
    mapping_note TEXT NOT NULL DEFAULT '',
    UNIQUE(artifact_id, legacy_entity_type, legacy_entity_id),
    FOREIGN KEY(artifact_id) REFERENCES artifacts(id)
);

CREATE INDEX IF NOT EXISTS idx_artifacts_class ON artifacts(artifact_class_id, archived);
CREATE INDEX IF NOT EXISTS idx_artifacts_checksum ON artifacts(checksum_sha256);
CREATE INDEX IF NOT EXISTS idx_relationship_source ON artifact_relationships(source_artifact_id);
CREATE INDEX IF NOT EXISTS idx_relationship_target ON artifact_relationships(target_artifact_id);
CREATE INDEX IF NOT EXISTS idx_decisions_state ON instructor_decisions(state, decision_type);
CREATE INDEX IF NOT EXISTS idx_scan_candidate_session ON scan_candidates(scan_session_id);
