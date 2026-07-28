DROP INDEX IF EXISTS idx_slide_ai_update_packets_slide;

ALTER TABLE slide_ai_update_packets RENAME TO slide_ai_update_packets_legacy;

CREATE TABLE slide_ai_update_packets (
    id INTEGER PRIMARY KEY,
    packet_id TEXT NOT NULL UNIQUE,
    cluster_id INTEGER NOT NULL REFERENCES lecture_knowledge_clusters(id) ON DELETE CASCADE,
    historical_slide_id INTEGER NOT NULL REFERENCES historical_slides(id) ON DELETE RESTRICT,
    historical_action TEXT NOT NULL CHECK (historical_action IN (
        'KEEP','UPDATE','EXPAND','MERGE','SPLIT','REORDER','REPLACE','REMOVE',
        'MOVE_TO_NOTES','CREATE_NEW'
    )),
    instructor_direction TEXT NOT NULL,
    corpus_type TEXT NOT NULL DEFAULT 'SLIDE_SPECIFIC_CORPUS',
    packet_markdown TEXT NOT NULL,
    slide_corpus_json TEXT NOT NULL DEFAULT '[]',
    cluster_context_json TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'PREPARED',
    lifecycle_state TEXT NOT NULL DEFAULT 'CORPUS_READY' CHECK (lifecycle_state IN (
        'UNREVIEWED','DECISION_RECORDED','CORPUS_READY','PACKET_COPIED',
        'SENT_TO_EXTERNAL_AI','AI_RESULT_PASTED','AI_RESULT_INVALID',
        'AI_RESULT_VALIDATED','INSTRUCTOR_EDITING','MANUALLY_APPLIED',
        'REINFORCED_SLIDE_ATTACHED','INSTRUCTOR_ACCEPTED','RETURNED_FOR_REVISION'
    )),
    packet_copied_at TEXT NOT NULL DEFAULT '',
    external_ai_status TEXT NOT NULL DEFAULT 'NOT_SENT',
    active_revision_id INTEGER,
    ai_result_text TEXT NOT NULL DEFAULT '',
    validated_result_json TEXT NOT NULL DEFAULT '{}',
    validation_errors_json TEXT NOT NULL DEFAULT '[]',
    draft_label TEXT NOT NULL DEFAULT 'AI_ASSISTED_DRAFT',
    review_label TEXT NOT NULL DEFAULT 'REQUIRES_INSTRUCTOR_REVIEW',
    instructor_ruling TEXT NOT NULL DEFAULT 'NOT_YET_DECIDED',
    instructor_ruling_comment TEXT NOT NULL DEFAULT '',
    instructor_edit_status TEXT NOT NULL DEFAULT 'NOT_STARTED' CHECK (
        instructor_edit_status IN ('NOT_STARTED','IN_PROGRESS','COMPLETED','EXPLICITLY_WAIVED')
    ),
    application_note TEXT NOT NULL DEFAULT '',
    applied_by TEXT NOT NULL DEFAULT '',
    applied_at TEXT NOT NULL DEFAULT '',
    slide_file_or_version_reference TEXT NOT NULL DEFAULT '',
    reinforced_slide_reference TEXT NOT NULL DEFAULT '',
    reinforced_slide_checksum TEXT NOT NULL DEFAULT '',
    attachment_storage_path TEXT NOT NULL DEFAULT '',
    attached_at TEXT NOT NULL DEFAULT '',
    unresolved_claims_disposition TEXT NOT NULL DEFAULT 'NOT_RECORDED' CHECK (
        unresolved_claims_disposition IN ('NOT_RECORDED','RESOLVED','EXPLICITLY_DEFERRED')
    ),
    final_slide_status TEXT NOT NULL DEFAULT 'NOT_ACCEPTED',
    return_reason TEXT NOT NULL DEFAULT '',
    return_target TEXT NOT NULL DEFAULT '',
    prepared_at TEXT NOT NULL,
    sent_at TEXT NOT NULL DEFAULT '',
    result_pasted_at TEXT NOT NULL DEFAULT '',
    validated_at TEXT NOT NULL DEFAULT '',
    decided_at TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL
);

INSERT INTO slide_ai_update_packets(
    id,packet_id,cluster_id,historical_slide_id,historical_action,instructor_direction,
    packet_markdown,slide_corpus_json,cluster_context_json,status,lifecycle_state,
    external_ai_status,ai_result_text,validated_result_json,validation_errors_json,
    draft_label,review_label,instructor_ruling,instructor_ruling_comment,prepared_at,
    sent_at,result_pasted_at,validated_at,decided_at,updated_at
)
SELECT id,packet_id,cluster_id,historical_slide_id,historical_action,instructor_direction,
       packet_markdown,slide_corpus_json,cluster_context_json,status,
       CASE status
           WHEN 'PREPARED' THEN 'CORPUS_READY'
           WHEN 'SENT_TO_AI' THEN 'SENT_TO_EXTERNAL_AI'
           WHEN 'RESULT_PASTED' THEN 'AI_RESULT_PASTED'
           WHEN 'VALIDATED' THEN 'AI_RESULT_VALIDATED'
           WHEN 'RETURNED_FOR_REVISION' THEN 'RETURNED_FOR_REVISION'
           ELSE 'AI_RESULT_VALIDATED'
       END,
       CASE WHEN sent_at='' THEN 'NOT_SENT' ELSE 'SENT_MANUALLY' END,
       ai_result_text,validated_result_json,validation_errors_json,draft_label,review_label,
       instructor_ruling,instructor_ruling_comment,prepared_at,sent_at,result_pasted_at,
       validated_at,decided_at,updated_at
FROM slide_ai_update_packets_legacy;

DROP TABLE slide_ai_update_packets_legacy;

CREATE TABLE slide_ai_update_revisions (
    id INTEGER PRIMARY KEY,
    revision_id TEXT NOT NULL UNIQUE,
    packet_id INTEGER NOT NULL REFERENCES slide_ai_update_packets(id) ON DELETE CASCADE,
    sequence INTEGER NOT NULL,
    raw_result_text TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'AI_RESULT_PASTED' CHECK (status IN (
        'AI_RESULT_PASTED','AI_RESULT_INVALID','AI_RESULT_VALIDATED','INSTRUCTOR_EDITING',
        'INSTRUCTOR_EDITED','EDITING_EXPLICITLY_WAIVED','RETURNED_FOR_REVISION',
        'INSTRUCTOR_ACCEPTED'
    )),
    validated_result_json TEXT NOT NULL DEFAULT '{}',
    validation_errors_json TEXT NOT NULL DEFAULT '[]',
    instructor_edit_json TEXT NOT NULL DEFAULT '{}',
    draft_label TEXT NOT NULL DEFAULT 'AI_ASSISTED_DRAFT',
    review_label TEXT NOT NULL DEFAULT 'REQUIRES_INSTRUCTOR_REVIEW',
    pasted_at TEXT NOT NULL,
    validated_at TEXT NOT NULL DEFAULT '',
    editing_started_at TEXT NOT NULL DEFAULT '',
    editing_completed_at TEXT NOT NULL DEFAULT '',
    returned_at TEXT NOT NULL DEFAULT '',
    return_reason TEXT NOT NULL DEFAULT '',
    return_target TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(packet_id, sequence)
);

CREATE INDEX idx_slide_ai_update_packets_slide
ON slide_ai_update_packets(cluster_id, historical_slide_id, id DESC);

CREATE INDEX idx_slide_ai_update_revisions_packet
ON slide_ai_update_revisions(packet_id, sequence DESC);
