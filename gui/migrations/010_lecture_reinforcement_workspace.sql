CREATE TABLE IF NOT EXISTS lecture_knowledge_clusters (
    id INTEGER PRIMARY KEY,
    cluster_id TEXT NOT NULL UNIQUE,
    lecture_pair_id INTEGER NOT NULL REFERENCES lecture_pairs(id) ON DELETE CASCADE,
    part TEXT NOT NULL CHECK (part IN ('A','B')),
    title TEXT NOT NULL,
    slide_start INTEGER NOT NULL,
    slide_end INTEGER NOT NULL,
    thematic_function TEXT NOT NULL,
    resource_group_id TEXT NOT NULL,
    historical_deck_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'NOT_STARTED' CHECK (
        status IN ('NOT_STARTED','IN_PROGRESS','REVIEW_REQUIRED','ACCEPTED','RETURNED')
    ),
    active INTEGER NOT NULL DEFAULT 0 CHECK (active IN (0,1)),
    selected_rotation TEXT NOT NULL DEFAULT '',
    selected_pattern_id TEXT NOT NULL DEFAULT '',
    historical_slide_decisions TEXT NOT NULL DEFAULT '{}',
    workflow_state TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL DEFAULT '',
    updated_by TEXT NOT NULL DEFAULT 'Application',
    CHECK (slide_start > 0 AND slide_end >= slide_start)
);

CREATE TABLE IF NOT EXISTS cluster_resource_alignments (
    id INTEGER PRIMARY KEY,
    alignment_id TEXT NOT NULL UNIQUE,
    cluster_id INTEGER NOT NULL REFERENCES lecture_knowledge_clusters(id) ON DELETE CASCADE,
    resource_id INTEGER REFERENCES resources(id) ON DELETE RESTRICT,
    source_identifier TEXT NOT NULL,
    resource_group_id TEXT NOT NULL,
    title TEXT NOT NULL,
    author TEXT NOT NULL DEFAULT '',
    publication_year TEXT NOT NULL DEFAULT '',
    resource_type TEXT NOT NULL DEFAULT '',
    symbolic_location TEXT NOT NULL,
    main_subjects TEXT NOT NULL DEFAULT '[]',
    cluster_alignment TEXT NOT NULL DEFAULT '',
    matching_historical_slides TEXT NOT NULL DEFAULT '[]',
    current_use_level TEXT NOT NULL DEFAULT 'UNRESOLVED' CHECK (
        current_use_level IN ('EXTENSIVELY_USED','PARTIALLY_USED','UNDERUSED',
        'UNUSED_BUT_RELEVANT','OUT_OF_DOMAIN','UNRESOLVED')
    ),
    source_quality TEXT NOT NULL DEFAULT 'UNASSESSED',
    currency_status TEXT NOT NULL DEFAULT 'UNVERIFIED',
    maps_or_figures TEXT NOT NULL DEFAULT '',
    relevant_pages_or_sections TEXT NOT NULL DEFAULT '',
    recommended_use TEXT NOT NULL DEFAULT '',
    verification_status TEXT NOT NULL DEFAULT 'NOT_STARTED',
    generated_recommendation TEXT NOT NULL DEFAULT '',
    instructor_action TEXT NOT NULL DEFAULT 'NOT_YET_DECIDED',
    instructor_comment TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL DEFAULT '',
    UNIQUE(cluster_id, source_identifier)
);

CREATE TABLE IF NOT EXISTS knowledge_units (
    id INTEGER PRIMARY KEY,
    knowledge_unit_id TEXT NOT NULL UNIQUE,
    cluster_id INTEGER NOT NULL REFERENCES lecture_knowledge_clusters(id) ON DELETE CASCADE,
    resource_id INTEGER REFERENCES resources(id) ON DELETE RESTRICT,
    source_identifier TEXT NOT NULL,
    historical_slide_ids TEXT NOT NULL DEFAULT '[]',
    unit_type TEXT NOT NULL CHECK (unit_type IN (
        'CLAIM','DEFINITION','CONCEPT','HISTORICAL_EPISODE','MAP','FIGURE','DATASET',
        'CAUSAL_RELATIONSHIP','RELATIONAL_PATTERN','COUNTERARGUMENT','QUOTATION',
        'EXAMPLE','LIMITATION'
    )),
    unit_text TEXT NOT NULL,
    source_pages TEXT NOT NULL,
    source_location TEXT NOT NULL,
    verification_status TEXT NOT NULL DEFAULT 'REQUIRES_INSTRUCTOR_REVIEW',
    alignment_score REAL NOT NULL DEFAULT 0 CHECK (alignment_score >= 0 AND alignment_score <= 1),
    temporal_scope TEXT NOT NULL DEFAULT '',
    spatial_scope TEXT NOT NULL DEFAULT 'South Asia',
    pedagogical_value TEXT NOT NULL DEFAULT '',
    candidate_slide_role TEXT NOT NULL DEFAULT '',
    instructor_status TEXT NOT NULL DEFAULT 'NOT_YET_DECIDED',
    origin TEXT NOT NULL DEFAULT 'SYSTEM_EXTRACTED',
    created_at TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL DEFAULT '',
    CHECK (source_location LIKE '<%>/%' OR source_location LIKE '<%>')
);

CREATE TABLE IF NOT EXISTS knowledge_patterns (
    id INTEGER PRIMARY KEY,
    pattern_id TEXT NOT NULL UNIQUE,
    cluster_id INTEGER NOT NULL REFERENCES lecture_knowledge_clusters(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    central_proposition TEXT NOT NULL,
    analytical_lenses TEXT NOT NULL DEFAULT '[]',
    historical_slides_retained TEXT NOT NULL DEFAULT '[]',
    historical_slides_condensed TEXT NOT NULL DEFAULT '[]',
    historical_slides_removed TEXT NOT NULL DEFAULT '[]',
    new_relationships TEXT NOT NULL DEFAULT '[]',
    source_basis TEXT NOT NULL DEFAULT '[]',
    counter_evidence TEXT NOT NULL DEFAULT '[]',
    evidence_strength TEXT NOT NULL DEFAULT 'PROVISIONAL',
    teaching_value TEXT NOT NULL DEFAULT '',
    estimated_time INTEGER NOT NULL DEFAULT 0,
    risks_or_limitations TEXT NOT NULL DEFAULT '[]',
    sequence_json TEXT NOT NULL DEFAULT '[]',
    status TEXT NOT NULL DEFAULT 'REVIEW_REQUIRED' CHECK (
        status IN ('REVIEW_REQUIRED','SELECTED','CONFIRMED','RETURNED','REJECTED','SAVED_FOR_LATER')
    ),
    origin TEXT NOT NULL DEFAULT 'SYSTEM_GENERATED_DRAFT',
    instructor_comment TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL DEFAULT '',
    updated_by TEXT NOT NULL DEFAULT 'Application'
);

CREATE TABLE IF NOT EXISTS knowledge_pattern_units (
    id INTEGER PRIMARY KEY,
    pattern_id INTEGER NOT NULL REFERENCES knowledge_patterns(id) ON DELETE CASCADE,
    knowledge_unit_id INTEGER NOT NULL REFERENCES knowledge_units(id) ON DELETE CASCADE,
    sequence INTEGER NOT NULL,
    relationship_note TEXT NOT NULL DEFAULT '',
    UNIQUE(pattern_id, knowledge_unit_id)
);

CREATE TABLE IF NOT EXISTS reinforced_slides (
    id INTEGER PRIMARY KEY,
    reinforced_slide_id TEXT NOT NULL UNIQUE,
    cluster_id INTEGER NOT NULL REFERENCES lecture_knowledge_clusters(id) ON DELETE CASCADE,
    pattern_id INTEGER NOT NULL REFERENCES knowledge_patterns(id) ON DELETE RESTRICT,
    sequence INTEGER NOT NULL,
    title TEXT NOT NULL,
    central_proposition TEXT NOT NULL,
    historical_slide_lineage TEXT NOT NULL DEFAULT '[]',
    knowledge_units TEXT NOT NULL DEFAULT '[]',
    resource_support TEXT NOT NULL DEFAULT '[]',
    visual_recommendation TEXT NOT NULL DEFAULT '',
    speaker_cue TEXT NOT NULL DEFAULT '',
    citation_footer TEXT NOT NULL DEFAULT '',
    verification_status TEXT NOT NULL DEFAULT 'REQUIRES_INSTRUCTOR_REVIEW',
    estimated_time INTEGER NOT NULL DEFAULT 0,
    transition_in TEXT NOT NULL DEFAULT '',
    transition_out TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'REVIEW_REQUIRED' CHECK (
        status IN ('REVIEW_REQUIRED','ACCEPT','REVISE','MERGE','SPLIT','MOVE','DELETE',
        'MOVE_DETAIL_TO_NOTES','REQUEST_NEW_VISUAL','RETURN_TO_PATTERN')
    ),
    instructor_comment TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL DEFAULT '',
    UNIQUE(cluster_id, sequence)
);

CREATE TABLE IF NOT EXISTS cluster_rehearsals (
    id INTEGER PRIMARY KEY,
    rehearsal_id TEXT NOT NULL UNIQUE,
    cluster_id INTEGER NOT NULL REFERENCES lecture_knowledge_clusters(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'IN_PROGRESS' CHECK (
        status IN ('IN_PROGRESS','PAUSED','COMPLETE','ABANDONED')
    ),
    started_at TEXT NOT NULL,
    ended_at TEXT NOT NULL DEFAULT '',
    target_seconds INTEGER NOT NULL DEFAULT 1200,
    actual_seconds INTEGER NOT NULL DEFAULT 0,
    skipped_slides TEXT NOT NULL DEFAULT '[]',
    instructor_comments TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cluster_rehearsal_events (
    id INTEGER PRIMARY KEY,
    event_id TEXT NOT NULL UNIQUE,
    rehearsal_id INTEGER NOT NULL REFERENCES cluster_rehearsals(id) ON DELETE CASCADE,
    reinforced_slide_id INTEGER REFERENCES reinforced_slides(id) ON DELETE SET NULL,
    event_type TEXT NOT NULL CHECK (event_type IN (
        'START','PREVIOUS','NEXT','PAUSE','RESUME','SHOW_NOTES','HIDE_NOTES',
        'SHOW_EVIDENCE','MARK_KEEP','MARK_REVISE','MARK_REMOVE',
        'ADD_TEACHING_COMMENT','END_REHEARSAL'
    )),
    elapsed_seconds INTEGER NOT NULL DEFAULT 0 CHECK (elapsed_seconds >= 0),
    comment TEXT NOT NULL DEFAULT '',
    occurred_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cluster_acceptance_records (
    id INTEGER PRIMARY KEY,
    acceptance_id TEXT NOT NULL UNIQUE,
    cluster_id INTEGER NOT NULL REFERENCES lecture_knowledge_clusters(id) ON DELETE CASCADE,
    selected_pattern_id INTEGER NOT NULL REFERENCES knowledge_patterns(id) ON DELETE RESTRICT,
    rehearsal_id INTEGER NOT NULL REFERENCES cluster_rehearsals(id) ON DELETE RESTRICT,
    ruling TEXT NOT NULL CHECK (ruling IN (
        'ACCEPT_CLUSTER','RETURN_TO_SLIDES','RETURN_TO_SOURCES','RETURN_TO_PATTERNS','DEFER'
    )),
    summary_json TEXT NOT NULL DEFAULT '{}',
    instructor_name TEXT NOT NULL DEFAULT 'Instructor',
    instructor_comment TEXT NOT NULL DEFAULT '',
    decided_at TEXT NOT NULL,
    UNIQUE(cluster_id, decided_at)
);

CREATE INDEX IF NOT EXISTS idx_reinforcement_cluster_status
ON lecture_knowledge_clusters(lecture_pair_id, part, status);

CREATE INDEX IF NOT EXISTS idx_reinforcement_resources
ON cluster_resource_alignments(cluster_id, resource_group_id);

CREATE INDEX IF NOT EXISTS idx_reinforcement_units
ON knowledge_units(cluster_id, unit_type, instructor_status);

CREATE INDEX IF NOT EXISTS idx_reinforcement_patterns
ON knowledge_patterns(cluster_id, status);

CREATE INDEX IF NOT EXISTS idx_reinforcement_slides
ON reinforced_slides(cluster_id, sequence);

INSERT OR IGNORE INTO lecture_knowledge_clusters(
    cluster_id,lecture_pair_id,part,title,slide_start,slide_end,thematic_function,
    resource_group_id,historical_deck_id,status,active,workflow_state,created_at,updated_at
)
SELECT 'KC01',id,'A','Regional imagination and ways of knowing South Asia',3,18,
       'Establish how South Asia has been imagined, observed and mapped across successive knowledge traditions.',
       'LEC_RES_1','L01-DECK-005','NOT_STARTED',1,
       '{"historical":"READY","cluster":"LOCKED","resources":"LOCKED","units":"LOCKED","patterns":"LOCKED","choice":"LOCKED","slides":"LOCKED","rehearsal":"LOCKED","acceptance":"LOCKED","build":"LOCKED"}',
       CURRENT_TIMESTAMP,CURRENT_TIMESTAMP
FROM lecture_pairs WHERE lecture_id='IS529N-L01';

INSERT OR IGNORE INTO lecture_knowledge_clusters(
    cluster_id,lecture_pair_id,part,title,slide_start,slide_end,thematic_function,
    resource_group_id,historical_deck_id,status,active,workflow_state,created_at,updated_at
)
SELECT 'KC02',id,'A','Environment and society',19,27,
       'Connect physical structures, environmental processes and social formations.',
       'LEC_RES_1','L01-DECK-005','NOT_STARTED',0,'{}',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP
FROM lecture_pairs WHERE lecture_id='IS529N-L01';

INSERT OR IGNORE INTO lecture_knowledge_clusters(
    cluster_id,lecture_pair_id,part,title,slide_start,slide_end,thematic_function,
    resource_group_id,historical_deck_id,status,active,workflow_state,created_at,updated_at
)
SELECT 'KC03',id,'A','Population and political economy',28,39,
       'Relate population, economy and territorial political change.',
       'LEC_RES_1','L01-DECK-005','NOT_STARTED',0,'{}',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP
FROM lecture_pairs WHERE lecture_id='IS529N-L01';

INSERT OR IGNORE INTO lecture_knowledge_clusters(
    cluster_id,lecture_pair_id,part,title,slide_start,slide_end,thematic_function,
    resource_group_id,historical_deck_id,status,active,workflow_state,created_at,updated_at
)
SELECT 'KC04',id,'A','Concept of region',40,46,
       'Introduce the conceptual vocabulary used to test regional formation.',
       'LEC_RES_1','L01-DECK-005','NOT_STARTED',0,'{}',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP
FROM lecture_pairs WHERE lecture_id='IS529N-L01';

INSERT OR IGNORE INTO lecture_knowledge_clusters(
    cluster_id,lecture_pair_id,part,title,slide_start,slide_end,thematic_function,
    resource_group_id,historical_deck_id,status,active,workflow_state,created_at,updated_at
)
SELECT 'KC05',id,'A','South Asia as regional formation',47,56,
       'Test the strengths and limits of South Asian regional formation.',
       'LEC_RES_1','L01-DECK-005','NOT_STARTED',0,'{}',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP
FROM lecture_pairs WHERE lecture_id='IS529N-L01';

INSERT OR IGNORE INTO lecture_knowledge_clusters(
    cluster_id,lecture_pair_id,part,title,slide_start,slide_end,thematic_function,
    resource_group_id,historical_deck_id,status,active,workflow_state,created_at,updated_at
)
SELECT 'KC06',id,'A','Comparative indicators',57,60,
       'Compare regional indicators while preserving their date and source limits.',
       'LEC_RES_1','L01-DECK-005','NOT_STARTED',0,'{}',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP
FROM lecture_pairs WHERE lecture_id='IS529N-L01';
