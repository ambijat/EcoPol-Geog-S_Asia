CREATE TABLE IF NOT EXISTS historical_resource_clusters (
    id INTEGER PRIMARY KEY,
    cluster_id TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    symbolic_location TEXT NOT NULL,
    resource_count INTEGER NOT NULL,
    type_summary TEXT NOT NULL,
    inspection_status TEXT NOT NULL,
    notes TEXT NOT NULL DEFAULT '',
    inspected_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS historical_resource_cluster_items (
    id INTEGER PRIMARY KEY,
    cluster_id INTEGER NOT NULL REFERENCES historical_resource_clusters(id) ON DELETE CASCADE,
    source_identifier TEXT NOT NULL,
    filename TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_sha256 TEXT NOT NULL,
    historical_use TEXT NOT NULL,
    alignment TEXT NOT NULL,
    relevant_dimensions TEXT NOT NULL DEFAULT '[]',
    verification_status TEXT NOT NULL,
    notes TEXT NOT NULL DEFAULT '',
    UNIQUE(cluster_id,source_identifier)
);

CREATE TABLE IF NOT EXISTS south_asia_argument_dimensions (
    id INTEGER PRIMARY KEY,
    dimension_id TEXT NOT NULL UNIQUE,
    triangulation_topic_id INTEGER NOT NULL REFERENCES triangulation_topics(id) ON DELETE CASCADE,
    dimension TEXT NOT NULL,
    historical_slides TEXT NOT NULL DEFAULT '[]',
    raw_resources TEXT NOT NULL DEFAULT '[]',
    website_material TEXT NOT NULL DEFAULT '[]',
    degree_of_historical_use TEXT NOT NULL,
    underused_material TEXT NOT NULL DEFAULT '[]',
    verification_status TEXT NOT NULL,
    recommended_teaching_role TEXT NOT NULL,
    analysis_notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_argument_dimensions_topic
ON south_asia_argument_dimensions(triangulation_topic_id);
