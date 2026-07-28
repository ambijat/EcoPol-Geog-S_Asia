CREATE TABLE IF NOT EXISTS lean_revision_units (
    id INTEGER PRIMARY KEY,
    unit_id TEXT NOT NULL UNIQUE,
    cluster_id INTEGER NOT NULL REFERENCES lecture_knowledge_clusters(id) ON DELETE RESTRICT,
    unit_type TEXT NOT NULL CHECK (unit_type IN ('SINGLE_SLIDE','SLIDE_PAIR','SMALL_CLUSTER')),
    slide_ids_json TEXT NOT NULL,
    instructor_query TEXT NOT NULL,
    source_mode TEXT NOT NULL CHECK (source_mode IN ('REPOSITORY','DIRECT_LOCAL','MIXED','GOVERNED')),
    selected_sources_json TEXT NOT NULL DEFAULT '[]',
    direct_sources_json TEXT NOT NULL DEFAULT '[]',
    status TEXT NOT NULL DEFAULT 'DRAFT' CHECK (status IN (
        'DRAFT','AI_PREPARED','AI_VALIDATED','INSTRUCTOR_REVIEWED',
        'CONTENT_ACCEPTED','RETURNED'
    )),
    packet_markdown TEXT NOT NULL DEFAULT '',
    raw_result_text TEXT NOT NULL DEFAULT '',
    validated_result_json TEXT NOT NULL DEFAULT '{}',
    validation_errors_json TEXT NOT NULL DEFAULT '[]',
    validation_warnings_json TEXT NOT NULL DEFAULT '[]',
    instructor_edit_json TEXT NOT NULL DEFAULT '{}',
    accepted_record_json TEXT NOT NULL DEFAULT '{}',
    accepted_by TEXT NOT NULL DEFAULT '',
    accepted_at TEXT NOT NULL DEFAULT '',
    return_note TEXT NOT NULL DEFAULT '',
    legacy_packet_id INTEGER REFERENCES slide_ai_update_packets(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_lean_revision_units_cluster
ON lean_revision_units(cluster_id, updated_at DESC);

CREATE TABLE IF NOT EXISTS lean_revision_artefacts (
    id INTEGER PRIMARY KEY,
    artefact_id TEXT NOT NULL UNIQUE,
    revision_unit_id INTEGER NOT NULL REFERENCES lean_revision_units(id) ON DELETE CASCADE,
    reference TEXT NOT NULL,
    storage_path TEXT NOT NULL DEFAULT '',
    original_filename TEXT NOT NULL DEFAULT '',
    sha256 TEXT NOT NULL DEFAULT '',
    attached_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_lean_revision_artefacts_unit
ON lean_revision_artefacts(revision_unit_id, attached_at DESC);
