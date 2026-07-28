CREATE TABLE IF NOT EXISTS triangulation_topics (
    id INTEGER PRIMARY KEY,
    triangulation_topic_id TEXT NOT NULL UNIQUE,
    lecture_pair_id INTEGER NOT NULL REFERENCES lecture_pairs(id),
    lecture_id TEXT NOT NULL,
    part TEXT NOT NULL CHECK(part IN ('A','B')),
    topic TEXT NOT NULL,
    central_question TEXT NOT NULL DEFAULT '',
    historical_slide_ids TEXT NOT NULL DEFAULT '[]',
    working_note_ids TEXT NOT NULL DEFAULT '[]',
    slide_plan_ids TEXT NOT NULL DEFAULT '[]',
    status TEXT NOT NULL DEFAULT 'INCOMPLETE',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS triangulation_evidence (
    id INTEGER PRIMARY KEY,
    evidence_id TEXT NOT NULL UNIQUE,
    triangulation_topic_id INTEGER NOT NULL REFERENCES triangulation_topics(id) ON DELETE CASCADE,
    evidence_layer TEXT NOT NULL CHECK(evidence_layer IN (
        'HISTORICAL_PPT_LAYER','RAW_RESOURCE_LAYER','WEBSITE_LEARNING_LAYER'
    )),
    source_identifier TEXT NOT NULL,
    source_title TEXT NOT NULL DEFAULT '',
    source_type TEXT NOT NULL DEFAULT '',
    symbolic_location TEXT NOT NULL DEFAULT '',
    source_sha256 TEXT NOT NULL DEFAULT '',
    treatment_level INTEGER NOT NULL DEFAULT 0 CHECK(treatment_level BETWEEN 0 AND 4),
    alignment_level TEXT NOT NULL DEFAULT 'UNRESOLVED' CHECK(alignment_level IN (
        'HIGH_ALIGNMENT','MODERATE_ALIGNMENT','LOW_ALIGNMENT','OUT_OF_DOMAIN','UNRESOLVED'
    )),
    evidentiary_value TEXT NOT NULL DEFAULT 'UNKNOWN' CHECK(evidentiary_value IN ('HIGH','MEDIUM','LOW','UNKNOWN')),
    verification_status TEXT NOT NULL DEFAULT 'NOT_YET_VERIFIED',
    currency_status TEXT NOT NULL DEFAULT 'DATE_UNCERTAIN' CHECK(currency_status IN (
        'CURRENT','NEEDS_UPDATE','HISTORICAL_ONLY','DATE_UNCERTAIN','NOT_APPLICABLE'
    )),
    instructor_status TEXT NOT NULL DEFAULT 'ADVISORY',
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(triangulation_topic_id,evidence_layer,source_identifier)
);

CREATE TABLE IF NOT EXISTS website_notes (
    id INTEGER PRIMARY KEY,
    website_note_id TEXT NOT NULL UNIQUE,
    page_title TEXT NOT NULL,
    page_url TEXT NOT NULL DEFAULT '',
    lecture_id TEXT NOT NULL,
    part TEXT NOT NULL CHECK(part IN ('A','B','SHARED','UNRESOLVED')),
    topic TEXT NOT NULL DEFAULT '',
    displayed_revision TEXT NOT NULL DEFAULT '',
    displayed_last_edit TEXT NOT NULL DEFAULT '',
    generated_by_ai INTEGER,
    ai_generation_status TEXT NOT NULL DEFAULT 'UNKNOWN_ORIGIN' CHECK(ai_generation_status IN (
        'HISTORICAL_AI_NOTE','AI_NOTE_UNDER_REVIEW','SOURCE_VERIFIED_AI_NOTE',
        'INSTRUCTOR_REVISED_NOTE','CURRENT_STUDENT_REFERENCE','SUPERSEDED_NOTE',
        'ARCHIVE_ONLY','UNKNOWN_ORIGIN'
    )),
    instructor_review_status TEXT NOT NULL DEFAULT 'NOT_YET_REVIEWED',
    source_links_present INTEGER NOT NULL DEFAULT 0,
    linked_raw_resource_ids TEXT NOT NULL DEFAULT '[]',
    claims_extracted INTEGER NOT NULL DEFAULT 0,
    claims_verified INTEGER NOT NULL DEFAULT 0,
    relationship_to_ppt TEXT NOT NULL DEFAULT 'UNRESOLVED',
    student_facing_status TEXT NOT NULL DEFAULT 'NOT_YET_VERIFIED',
    recommended_action TEXT NOT NULL DEFAULT 'REQUIRES_FURTHER_REVIEW',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS website_note_sources (
    id INTEGER PRIMARY KEY,
    website_note_id INTEGER NOT NULL REFERENCES website_notes(id) ON DELETE CASCADE,
    source_identifier TEXT NOT NULL,
    source_role TEXT NOT NULL DEFAULT 'LINKED_SOURCE',
    verification_status TEXT NOT NULL DEFAULT 'NOT_YET_VERIFIED',
    UNIQUE(website_note_id,source_identifier)
);

CREATE TABLE IF NOT EXISTS website_link_records (
    id INTEGER PRIMARY KEY,
    website_link_id TEXT NOT NULL UNIQUE,
    website_note_id INTEGER REFERENCES website_notes(id) ON DELETE CASCADE,
    page_url TEXT NOT NULL,
    link_label TEXT NOT NULL DEFAULT '',
    link_type TEXT NOT NULL DEFAULT 'PAGE',
    symbolic_target TEXT NOT NULL DEFAULT '',
    inspection_status TEXT NOT NULL DEFAULT 'METADATA_ONLY',
    download_authorised INTEGER NOT NULL DEFAULT 0,
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS triangulation_claims (
    id INTEGER PRIMARY KEY,
    claim_id TEXT NOT NULL UNIQUE,
    triangulation_topic_id INTEGER NOT NULL REFERENCES triangulation_topics(id) ON DELETE CASCADE,
    claim_text TEXT NOT NULL,
    origin_layer TEXT NOT NULL CHECK(origin_layer IN (
        'HISTORICAL_PPT_LAYER','RAW_RESOURCE_LAYER','WEBSITE_LEARNING_LAYER'
    )),
    historical_slide_ids TEXT NOT NULL DEFAULT '[]',
    raw_resource_ids TEXT NOT NULL DEFAULT '[]',
    website_note_ids TEXT NOT NULL DEFAULT '[]',
    verification_status TEXT NOT NULL DEFAULT 'NOT_YET_VERIFIED',
    support_level TEXT NOT NULL DEFAULT 'UNKNOWN' CHECK(support_level IN ('HIGH','MEDIUM','LOW','UNKNOWN')),
    contradiction_status TEXT NOT NULL DEFAULT 'UNRESOLVED',
    currency_status TEXT NOT NULL DEFAULT 'DATE_UNCERTAIN' CHECK(currency_status IN (
        'CURRENT','NEEDS_UPDATE','HISTORICAL_ONLY','DATE_UNCERTAIN','NOT_APPLICABLE'
    )),
    instructor_comment TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS triangulation_findings (
    id INTEGER PRIMARY KEY,
    finding_id TEXT NOT NULL UNIQUE,
    triangulation_topic_id INTEGER NOT NULL REFERENCES triangulation_topics(id) ON DELETE CASCADE,
    finding_type TEXT NOT NULL CHECK(finding_type IN (
        'TRIANGULATED_CORE','CREATE_OR_EXPAND_STUDENT_NOTE','CANDIDATE_FOR_NEW_SLIDE',
        'SOURCE_VERIFICATION_REQUIRED','UNUSED_RELEVANT_RESOURCE','UNVERIFIED_WEBSITE_NOTE',
        'OUT_OF_DOMAIN','ARCHIVE_ONLY','NEW_SOURCE_REQUIRED','INCOMPLETE'
    )),
    summary TEXT NOT NULL DEFAULT '',
    evidence_gap TEXT NOT NULL DEFAULT '',
    recommended_action TEXT NOT NULL DEFAULT 'REQUIRES_FURTHER_REVIEW',
    instructor_status TEXT NOT NULL DEFAULT 'ADVISORY',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(triangulation_topic_id,finding_type)
);

CREATE TABLE IF NOT EXISTS triangulation_decisions (
    id INTEGER PRIMARY KEY,
    decision_id TEXT NOT NULL UNIQUE,
    triangulation_topic_id INTEGER NOT NULL REFERENCES triangulation_topics(id) ON DELETE CASCADE,
    finding_id INTEGER REFERENCES triangulation_findings(id),
    recommended_action TEXT NOT NULL,
    instructor_decision TEXT NOT NULL DEFAULT 'NOT_YET_DECIDED',
    instructor_comment TEXT NOT NULL DEFAULT '',
    confirmed INTEGER NOT NULL DEFAULT 0,
    decided_at TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS source_coverage_reconstructions (
    id INTEGER PRIMARY KEY,
    reconstruction_id TEXT NOT NULL UNIQUE,
    historical_slide_id TEXT NOT NULL,
    candidate_source_id TEXT NOT NULL,
    lexical_overlap REAL NOT NULL DEFAULT 0 CHECK(lexical_overlap BETWEEN 0 AND 1),
    concept_overlap REAL NOT NULL DEFAULT 0 CHECK(concept_overlap BETWEEN 0 AND 1),
    data_overlap REAL NOT NULL DEFAULT 0 CHECK(data_overlap BETWEEN 0 AND 1),
    visual_overlap REAL NOT NULL DEFAULT 0 CHECK(visual_overlap BETWEEN 0 AND 1),
    citation_match INTEGER NOT NULL DEFAULT 0,
    probable_lineage TEXT NOT NULL DEFAULT 'UNCONFIRMED',
    use_level INTEGER NOT NULL DEFAULT 0 CHECK(use_level BETWEEN 0 AND 4),
    confidence TEXT NOT NULL DEFAULT 'UNKNOWN' CHECK(confidence IN ('HIGH','MEDIUM','LOW','UNKNOWN')),
    instructor_confirmation INTEGER NOT NULL DEFAULT 0,
    analytical_label TEXT NOT NULL DEFAULT 'RETROSPECTIVE_SOURCE_RECONSTRUCTION',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS candidate_registry_records (
    id INTEGER PRIMARY KEY,
    candidate_id TEXT NOT NULL UNIQUE,
    triangulation_topic_id INTEGER NOT NULL REFERENCES triangulation_topics(id) ON DELETE CASCADE,
    evidence_layer TEXT NOT NULL CHECK(evidence_layer IN (
        'HISTORICAL_PPT_LAYER','RAW_RESOURCE_LAYER','WEBSITE_LEARNING_LAYER'
    )),
    source_identifier TEXT NOT NULL,
    title TEXT NOT NULL DEFAULT '',
    symbolic_location TEXT NOT NULL DEFAULT '',
    source_sha256 TEXT NOT NULL DEFAULT '',
    admission_status TEXT NOT NULL DEFAULT 'PENDING_INSTRUCTOR_ADMISSION',
    instructor_decision TEXT NOT NULL DEFAULT 'NOT_YET_DECIDED',
    canonical_registration_performed INTEGER NOT NULL DEFAULT 0,
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS student_learning_packages (
    id INTEGER PRIMARY KEY,
    learning_package_id TEXT NOT NULL UNIQUE,
    lecture_pair_id INTEGER NOT NULL REFERENCES lecture_pairs(id),
    lecture_id TEXT NOT NULL,
    part TEXT NOT NULL CHECK(part IN ('A','B')),
    classroom_deck_id INTEGER REFERENCES deliverable_bundles(id),
    website_note_ids TEXT NOT NULL DEFAULT '[]',
    raw_resource_ids TEXT NOT NULL DEFAULT '[]',
    public_link_ids TEXT NOT NULL DEFAULT '[]',
    verification_status TEXT NOT NULL DEFAULT 'NOT_YET_VERIFIED',
    public_approval_status TEXT NOT NULL DEFAULT 'NOT_APPROVED',
    instructor_status TEXT NOT NULL DEFAULT 'WORKING_DRAFT',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_triangulation_topic_lecture ON triangulation_topics(lecture_pair_id,part);
CREATE INDEX IF NOT EXISTS idx_triangulation_evidence_topic ON triangulation_evidence(triangulation_topic_id,evidence_layer);
CREATE INDEX IF NOT EXISTS idx_triangulation_claim_topic ON triangulation_claims(triangulation_topic_id);
CREATE INDEX IF NOT EXISTS idx_triangulation_finding_topic ON triangulation_findings(triangulation_topic_id);
CREATE INDEX IF NOT EXISTS idx_candidate_registry_topic ON candidate_registry_records(triangulation_topic_id);
CREATE INDEX IF NOT EXISTS idx_learning_package_lecture ON student_learning_packages(lecture_pair_id,part);

-- High-fidelity inherited A/B titles and fixed weekly allocation do not require routine confirmation.
UPDATE historical_decks
SET instructor_confirmation_required = 0
WHERE confidence = 'HIGH'
  AND sequence_mismatch_warning = ''
  AND inferred_part IN ('L01A','L01B');
