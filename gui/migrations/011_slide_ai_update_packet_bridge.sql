CREATE TABLE IF NOT EXISTS slide_ai_update_packets (
    id INTEGER PRIMARY KEY,
    packet_id TEXT NOT NULL UNIQUE,
    cluster_id INTEGER NOT NULL REFERENCES lecture_knowledge_clusters(id) ON DELETE CASCADE,
    historical_slide_id INTEGER NOT NULL REFERENCES historical_slides(id) ON DELETE RESTRICT,
    historical_action TEXT NOT NULL CHECK (
        historical_action IN ('UPDATE','EXPAND','MERGE','SPLIT','REPLACE','CREATE_NEW')
    ),
    instructor_direction TEXT NOT NULL,
    packet_markdown TEXT NOT NULL,
    slide_corpus_json TEXT NOT NULL DEFAULT '[]',
    cluster_context_json TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'PREPARED' CHECK (
        status IN ('PREPARED','SENT_TO_AI','RESULT_PASTED','VALIDATED',
        'ACCEPTED_PROPOSED_REVISION','RETURNED_FOR_REVISION')
    ),
    ai_result_text TEXT NOT NULL DEFAULT '',
    validated_result_json TEXT NOT NULL DEFAULT '{}',
    validation_errors_json TEXT NOT NULL DEFAULT '[]',
    draft_label TEXT NOT NULL DEFAULT 'AI_ASSISTED_DRAFT',
    review_label TEXT NOT NULL DEFAULT 'REQUIRES_INSTRUCTOR_REVIEW',
    instructor_ruling TEXT NOT NULL DEFAULT 'NOT_YET_DECIDED',
    instructor_ruling_comment TEXT NOT NULL DEFAULT '',
    prepared_at TEXT NOT NULL,
    sent_at TEXT NOT NULL DEFAULT '',
    result_pasted_at TEXT NOT NULL DEFAULT '',
    validated_at TEXT NOT NULL DEFAULT '',
    decided_at TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_slide_ai_update_packets_slide
ON slide_ai_update_packets(cluster_id, historical_slide_id, id DESC);
