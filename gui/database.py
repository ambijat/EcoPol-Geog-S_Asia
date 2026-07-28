from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE = PROJECT_ROOT / "gui" / "database" / "is529n_cockpit.sqlite3"
MIGRATIONS = Path(__file__).resolve().parent / "migrations"
HISTORICAL_LABEL = "<HISTORICAL_RESOURCE_REPOSITORY>"


def connect(path: Path = DEFAULT_DATABASE) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def migrate(connection: sqlite3.Connection, migrations: Path = MIGRATIONS) -> None:
    connection.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations "
        "(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
    )
    applied = {
        row[0] for row in connection.execute("SELECT version FROM schema_migrations")
    }
    for path in sorted(migrations.glob("[0-9][0-9][0-9]_*.sql")):
        version = int(path.name.split("_", 1)[0])
        if version in applied:
            continue
        connection.executescript(path.read_text(encoding="utf-8"))
        connection.execute(
            "INSERT INTO schema_migrations(version, applied_at) VALUES (?, ?)",
            (version, datetime.now(timezone.utc).isoformat(timespec="seconds")),
        )
        connection.commit()


def seed_lectures(connection: sqlite3.Connection) -> None:
    for number in range(1, 16):
        lecture_id = f"IS529N-L{number:02d}"
        connection.execute(
            "INSERT OR IGNORE INTO lecture_pairs"
            "(lecture_id, lecture_number, week, weekly_title) VALUES (?, ?, ?, ?)",
            (lecture_id, number, number, f"Lecture {number} — title pending instructor confirmation"),
        )
        pair_id = connection.execute(
            "SELECT id FROM lecture_pairs WHERE lecture_id = ?", (lecture_id,)
        ).fetchone()[0]
        for part, day, time in (("A", "TUESDAY", "09:00-11:00"), ("B", "FRIDAY", "09:00-11:00")):
            connection.execute(
                "INSERT OR IGNORE INTO lecture_parts"
                "(lecture_pair_id, part, identifier, scheduled_day, scheduled_time, title) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    pair_id,
                    part,
                    f"{lecture_id}-{part}",
                    day,
                    time,
                    f"Part {part} — title pending instructor confirmation",
                ),
            )
    connection.commit()


def seed_reinforcement_clusters(connection: sqlite3.Connection) -> None:
    """Seed the governed Lecture 1A cluster map after lecture rows exist."""
    if connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='lecture_knowledge_clusters'"
    ).fetchone() is None:
        return
    pair = connection.execute(
        "SELECT id FROM lecture_pairs WHERE lecture_id='IS529N-L01'"
    ).fetchone()
    if pair is None:
        return
    records = (
        ("KC01", "Regional imagination and ways of knowing South Asia", 3, 18,
         "Establish how South Asia has been imagined, observed and mapped across successive knowledge traditions.", 1),
        ("KC02", "Environment and society", 19, 27,
         "Connect physical structures, environmental processes and social formations.", 0),
        ("KC03", "Population and political economy", 28, 39,
         "Relate population, economy and territorial political change.", 0),
        ("KC04", "Concept of region", 40, 46,
         "Introduce the conceptual vocabulary used to test regional formation.", 0),
        ("KC05", "South Asia as regional formation", 47, 56,
         "Test the strengths and limits of South Asian regional formation.", 0),
        ("KC06", "Comparative indicators", 57, 60,
         "Compare regional indicators while preserving their date and source limits.", 0),
    )
    initial = json.dumps({
        "historical": "READY", "cluster": "LOCKED", "resources": "LOCKED",
        "units": "LOCKED", "patterns": "LOCKED", "choice": "LOCKED",
        "slides": "LOCKED", "rehearsal": "LOCKED", "acceptance": "LOCKED",
        "build": "LOCKED",
    }, sort_keys=True)
    for cluster_id, title, start, end, function, active in records:
        connection.execute(
            """INSERT OR IGNORE INTO lecture_knowledge_clusters(
            cluster_id,lecture_pair_id,part,title,slide_start,slide_end,thematic_function,
            resource_group_id,historical_deck_id,status,active,workflow_state,created_at,updated_at)
            VALUES (?,?,'A',?,?,?,?,?,'L01-DECK-005','NOT_STARTED',?,?,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)""",
            (cluster_id, pair[0], title, start, end, function, "LEC_RES_1", active,
             initial if active else "{}"),
        )
    connection.commit()


def seed_lecture_one_census(connection: sqlite3.Connection, census_path: Path) -> int:
    if not census_path.is_file():
        return 0
    records = json.loads(census_path.read_text(encoding="utf-8")).get("records", [])
    selected = [
        record for record in records
        if str(record.get("relative_context", "")).startswith("LECTURE1/")
        and str(record.get("extension", "")).lower() in {".pdf", ".pptx", ".odp"}
    ]
    pair_id = connection.execute(
        "SELECT id FROM lecture_pairs WHERE lecture_number = 1"
    ).fetchone()[0]
    for index, record in enumerate(selected, start=1):
        relative = record["relative_context"]
        resource_id = f"L01-CENSUS-{index:03d}"
        locator = f"{HISTORICAL_LABEL}/{relative}"
        connection.execute(
            "INSERT OR IGNORE INTO resources"
            "(resource_id,title,source_locator,provenance,source_layer,file_type,"
            "historical_status,content_sha256) VALUES (?,?,?,?,?,?,?,?)",
            (
                resource_id,
                record["filename"],
                locator,
                "Authorised local source census metadata",
                record.get("source_layer", "UNKNOWN"),
                record.get("extension", ""),
                "HISTORICAL_READ_ONLY",
                record.get("content_sha256", ""),
            ),
        )
        resource_pk = connection.execute(
            "SELECT id FROM resources WHERE resource_id = ?", (resource_id,)
        ).fetchone()[0]
        connection.execute(
            "INSERT OR IGNORE INTO resource_assignments"
            "(resource_id,lecture_pair_id,part) VALUES (?,?,'UNCLASSIFIED')",
            (resource_pk, pair_id),
        )
        connection.execute(
            "INSERT OR IGNORE INTO historical_decks"
            "(deck_id,lecture_pair_id,title,source_locator,file_type,source_layer,content_sha256)"
            " VALUES (?,?,?,?,?,?,?)",
            (
                f"L01-DECK-{index:03d}", pair_id, record["filename"], locator,
                record.get("extension", ""), record.get("source_layer", "UNKNOWN"),
                record.get("content_sha256", ""),
            ),
        )
    connection.commit()
    return len(selected)


def seed_title_evidence(connection: sqlite3.Connection, report_path: Path) -> int:
    if not report_path.is_file():
        return 0
    records = json.loads(report_path.read_text(encoding="utf-8")).get("records", [])
    inserted = 0
    for record in records:
        lecture_id = record.get("associated_lecture_id")
        if not lecture_id:
            continue
        pair = connection.execute(
            "SELECT id FROM lecture_pairs WHERE lecture_id=?", (lecture_id,)
        ).fetchone()
        if pair is None:
            continue
        cursor = connection.execute(
            """INSERT OR IGNORE INTO title_evidence(lecture_pair_id,target_identifier,
            target_classification,source_filename,source_locator,source_sha256,extracted_title,
            extraction_method,extraction_confidence,instructor_confirmation_required)
            VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (pair[0], record["target_identifier"], record["historical_classification"],
             record["source_filename"], record["source_locator"], record["source_sha256"],
             record["extracted_title"], record["extraction_method"],
             record["extraction_confidence"], int(record["instructor_confirmation_required"])),
        )
        inserted += int(cursor.rowcount > 0)
    connection.commit()
    return inserted


def initialise(path: Path = DEFAULT_DATABASE, census_path: Path | None = None) -> sqlite3.Connection:
    connection = connect(path)
    migrate(connection)
    seed_lectures(connection)
    seed_reinforcement_clusters(connection)
    effective_census = census_path or PROJECT_ROOT / "reports" / "source_census.json"
    seed_lecture_one_census(connection, effective_census)
    seed_title_evidence(
        connection, effective_census.parent / "historical_lecture_title_extraction.json"
    )
    if effective_census.is_file():
        seed_qt_phase2(connection, effective_census.parent / "historical_lecture_title_extraction.json")
        seed_qt_phase4_pilot(connection, effective_census)
    return connection


LECTURE_ONE_NOTE_HEADINGS = (
    "Meaning of a region",
    "Geographical boundaries of South Asia",
    "Contested definitions of South Asia",
    "Common physical-geographical features",
    "Historical and civilisational connectivity",
    "Political fragmentation and regional identity",
)

LECTURE_ONE_SLIDE_TITLES = (
    "Title and weekly framing", "What is a region?",
    "Competing definitions of South Asia", "Political map of South Asia",
    "Physical-geographical unity", "Rivers, monsoon and ecological interdependence",
    "Historical routes and mobility", "Colonial territorial consolidation",
    "Partition and political fragmentation", "Regional disparities",
    "SAARC and institutional regionalism", "Is South Asia a coherent region?",
    "Classroom discussion", "Tuesday synthesis", "Bridge to Friday: the Himalayas",
)


def seed_qt_phase2(connection: sqlite3.Connection, title_evidence_path: Path) -> None:
    """Seed instructor-supplied structure only; never seed substantive claims."""
    pair = connection.execute(
        "SELECT id FROM lecture_pairs WHERE lecture_number=1"
    ).fetchone()
    if pair is None:
        return
    pair_id = pair[0]
    evidence_by_locator: dict[str, dict] = {}
    if title_evidence_path.is_file():
        for record in json.loads(title_evidence_path.read_text(encoding="utf-8")).get("records", []):
            if record.get("associated_lecture_id") == "IS529N-L01":
                evidence_by_locator[record.get("source_locator", "")] = record
    for deck in connection.execute(
        "SELECT id,source_locator FROM historical_decks WHERE lecture_pair_id=?", (pair_id,)
    ).fetchall():
        evidence = evidence_by_locator.get(deck["source_locator"], {})
        classification = evidence.get("historical_classification", "")
        inferred = {"PART_A": "L01A", "PART_B": "L01B"}.get(classification, "REQUIRES_INSPECTION")
        confirmation_required = int(
            not evidence.get("extracted_title")
            or bool(evidence.get("sequence_mismatch_warning"))
            or evidence.get("extraction_confidence") != "HIGH"
            or inferred == "REQUIRES_INSPECTION"
        )
        connection.execute(
            """UPDATE historical_decks SET extracted_title=?,inferred_lecture_number='L01',
            inferred_part=?,source_evidence=?,confidence=?,sequence_mismatch_warning=?,
            instructor_assignment=?,instructor_confirmation_required=?
            WHERE id=?""",
            (evidence.get("extracted_title", ""), inferred,
             evidence.get("extraction_method", "CENSUS_METADATA"),
             evidence.get("extraction_confidence", "UNASSESSED"),
             evidence.get("sequence_mismatch_warning", "") or "", inferred,
             confirmation_required, deck["id"]),
        )
    for index, topic in enumerate(LECTURE_ONE_NOTE_HEADINGS, start=1):
        connection.execute(
            """INSERT OR IGNORE INTO revised_notes(
            note_id,lecture_pair_id,part,topic,claim,teaching_function,created_by,note_origin,
            verification_status,instructor_status,instructor_origin_declared,updated_at,updated_by)
            VALUES (?,?, 'A', ?, '', 'CONCEPT', 'Instructor', 'INSTRUCTOR_AUTHORED',
            'NOT_YET_VERIFIED','WORKING_DRAFT',1,?,'Application')""",
            (f"IS529N-L01-A-N{index:03d}", pair_id, topic,
             datetime.now(timezone.utc).isoformat(timespec="seconds")),
        )
    for index, title in enumerate(LECTURE_ONE_SLIDE_TITLES, start=1):
        visual = "TITLE" if index == 1 else "DISCUSSION" if index in {12, 13} else "SYNTHESIS" if index == 14 else "CONCEPT"
        connection.execute(
            """INSERT OR IGNORE INTO slide_plan_entries(
            slide_id,lecture_pair_id,part,sequence,title,purpose,action,visual_type,
            verification_status,approval_status,updated_at,updated_by)
            VALUES (?,?,'A',?,?,?,'ADD',?,'NOT_YET_VERIFIED','WORKING_DRAFT',?,'Application')""",
            (f"IS529N-L01-A-S{index:03d}", pair_id, index, title,
             "Instructor-supplied provisional Lecture 1A structure", visual,
             datetime.now(timezone.utc).isoformat(timespec="seconds")),
        )
    connection.commit()


def seed_qt_phase4_pilot(connection: sqlite3.Connection, census_path: Path) -> None:
    """Seed only governed metadata for the accepted L01A chain and unresolved intake slots."""
    pair = connection.execute(
        "SELECT id,lecture_id FROM lecture_pairs WHERE lecture_number=1"
    ).fetchone()
    slide = connection.execute(
        "SELECT id,historical_slide_id FROM historical_slides WHERE historical_slide_id='L01-DECK-005-S041'"
    ).fetchone()
    note = connection.execute(
        "SELECT id,note_id FROM revised_notes WHERE note_id='IS529N-L01-A-N001'"
    ).fetchone()
    plan = connection.execute(
        "SELECT id,slide_id FROM slide_plan_entries WHERE slide_id='IS529N-L01-A-S002'"
    ).fetchone()
    resource = connection.execute(
        "SELECT * FROM resources WHERE resource_id='L01-CENSUS-005'"
    ).fetchone()
    if not all((pair, slide, note, plan, resource)):
        return
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    connection.execute(
        """INSERT OR IGNORE INTO triangulation_topics(triangulation_topic_id,lecture_pair_id,lecture_id,
        part,topic,central_question,historical_slide_ids,working_note_ids,slide_plan_ids,status,created_at,updated_at)
        VALUES ('TRI-L01-A-REGION-001',?,?,'A','Meaning of a region',?, ?, ?, ?,'INCOMPLETE',?,?)""",
        (pair["id"], pair["lecture_id"],
         "What makes South Asia a region across historical, scholarly, and student-facing layers?",
         json.dumps([slide["historical_slide_id"]]), json.dumps([note["note_id"]]),
         json.dumps([plan["slide_id"]]), now, now),
    )
    topic_pk = connection.execute(
        "SELECT id FROM triangulation_topics WHERE triangulation_topic_id='TRI-L01-A-REGION-001'"
    ).fetchone()[0]
    connection.execute(
        """INSERT OR IGNORE INTO triangulation_evidence(evidence_id,triangulation_topic_id,evidence_layer,
        source_identifier,source_title,source_type,symbolic_location,source_sha256,treatment_level,
        alignment_level,evidentiary_value,verification_status,currency_status,instructor_status,notes,
        created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        ("TRI-E-L01A-HIST-001", topic_pk, "HISTORICAL_PPT_LAYER", slide["historical_slide_id"],
         "Concept of a Region", "HISTORICAL_ODP_SLIDE", resource["source_locator"],
         resource["content_sha256"], 2, "HIGH_ALIGNMENT", "MEDIUM", "NOT_YET_VERIFIED",
         "HISTORICAL_ONLY", "ADVISORY", "Accepted Phase 3 chain; slide status REVISE.", now, now),
    )
    raw_record = None
    if census_path.is_file():
        raw_record = next((record for record in json.loads(census_path.read_text(encoding="utf-8")).get("records", [])
                           if record.get("census_id") == "IS529N-CENSUS-0449"), None)
    if raw_record:
        connection.execute(
            """INSERT OR IGNORE INTO triangulation_evidence(evidence_id,triangulation_topic_id,evidence_layer,
            source_identifier,source_title,source_type,symbolic_location,source_sha256,treatment_level,
            alignment_level,evidentiary_value,verification_status,currency_status,instructor_status,notes,
            created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            ("TRI-E-L01A-RAW-001", topic_pk, "RAW_RESOURCE_LAYER", raw_record["census_id"],
             raw_record["filename"], "SCHOLARLY_ARTICLE_PDF",
             f"<HISTORICAL_RESOURCE_REPOSITORY>/{raw_record['relative_context']}",
             raw_record["content_sha256"], 0, "HIGH_ALIGNMENT", "UNKNOWN", "NOT_YET_VERIFIED",
             "DATE_UNCERTAIN", "ADVISORY",
             "Title and checksum identified from the authorised census; content not inspected and relationship not confirmed.",
             now, now),
        )
    connection.execute(
        """INSERT OR IGNORE INTO website_notes(website_note_id,page_title,page_url,lecture_id,part,topic,
        displayed_revision,displayed_last_edit,generated_by_ai,ai_generation_status,
        instructor_review_status,source_links_present,linked_raw_resource_ids,claims_extracted,
        claims_verified,relationship_to_ppt,student_facing_status,recommended_action,created_at,updated_at)
        VALUES ('WIKI-REFERENCES-MA-INDEX','References MA','http://ambijat.wikidot.com/references-ma',
        'IS529N-L01','UNRESOLVED','Course reference index','549','2025-10-24 07:23',NULL,
        'UNKNOWN_ORIGIN','METADATA_ONLY',1,'[]',0,0,'UNRESOLVED','NOT_YET_VERIFIED',
        'IDENTIFY_WEBSITE_NOTE',?,?)""", (now, now),
    )
    website_pk = connection.execute(
        "SELECT id FROM website_notes WHERE website_note_id='WIKI-REFERENCES-MA-INDEX'"
    ).fetchone()[0]
    connection.execute(
        """INSERT OR IGNORE INTO website_link_records(website_link_id,website_note_id,page_url,
        link_label,link_type,symbolic_target,inspection_status,download_authorised,notes,created_at)
        VALUES ('WIKI-LINK-REFERENCES-MA',?,'http://ambijat.wikidot.com/references-ma','References MA',
        'INDEX_PAGE','<WEBSITE_LEARNING_LAYER>/references-ma','PREVIOUSLY_AUTHORISED_METADATA',0,
        'No Phase 4 crawl or attachment download performed.',?)""", (website_pk, now),
    )
    connection.execute(
        """INSERT OR IGNORE INTO triangulation_claims(claim_id,triangulation_topic_id,claim_text,
        origin_layer,historical_slide_ids,raw_resource_ids,website_note_ids,verification_status,
        support_level,contradiction_status,currency_status,instructor_comment,created_at,updated_at)
        VALUES ('TRI-C-L01A-001',?,?,?,'["L01-DECK-005-S041"]','[]','[]',
        'NOT_YET_VERIFIED','UNKNOWN','UNRESOLVED','DATE_UNCERTAIN',?,?,?)""",
        (topic_pk,
         "A region develops from physical delimitation through social relations, organised cooperation, shared values, and institutional capability.",
         "HISTORICAL_PPT_LAYER",
         "Raw candidate identified by title only; scholarly attribution and website representation require verification.",
         now, now),
    )
    candidates = (
        ("REG-CAND-L01A-HIST-001", "HISTORICAL_PPT_LAYER", "L01-CENSUS-005", "lecture1a.odp",
         resource["source_locator"], resource["content_sha256"], "PENDING_INSTRUCTOR_ADMISSION",
         "Historical source candidate only; no canonical registration."),
        ("REG-CAND-L01A-RAW-001", "RAW_RESOURCE_LAYER", "IS529N-CENSUS-0449" if raw_record else "NOT_YET_IDENTIFIED",
         raw_record["filename"] if raw_record else "Raw scholarly source not yet identified",
         f"<HISTORICAL_RESOURCE_REPOSITORY>/{raw_record['relative_context']}" if raw_record else "",
         raw_record["content_sha256"] if raw_record else "", "PENDING_SOURCE_INSPECTION",
         "Candidate inferred from census title; not admitted and not yet inspected."),
        ("REG-CAND-L01A-WEB-001", "WEBSITE_LEARNING_LAYER", "NOT_YET_IDENTIFIED",
         "Topic-specific Wikidot note not yet identified", "", "", "PENDING_IDENTIFICATION",
         "The authorised References MA index is known; no topic-specific note relationship is asserted."),
    )
    for candidate in candidates:
        connection.execute(
            """INSERT OR IGNORE INTO candidate_registry_records(candidate_id,triangulation_topic_id,
            evidence_layer,source_identifier,title,symbolic_location,source_sha256,admission_status,
            instructor_decision,canonical_registration_performed,notes,created_at)
            VALUES (?,?,?,?,?,?,?,?,'NOT_YET_DECIDED',0,?,?)""",
            (candidate[0], topic_pk, *candidate[1:], now),
        )
    pilot_findings = (
        ("TRI-F-L01A-001", "CREATE_OR_EXPAND_STUDENT_NOTE",
         "The authorised website index is known, but no topic-specific student note is identified.",
         "Website learning layer absent or insufficient", "CREATE_STUDENT_NOTE"),
        ("TRI-F-L01A-002", "UNUSED_RELEVANT_RESOURCE",
         "The Schmitt-Egner article is highly aligned by title but its governed classroom use is not established.",
         "Aligned raw source is not yet inspected or integrated", "EXPAND_USE"),
        ("TRI-F-L01A-003", "SOURCE_VERIFICATION_REQUIRED",
         "The inherited five-degree claim and attribution are not yet verified against an inspected raw source.",
         "Reliable raw scholarly support is not yet verified", "VERIFY_CLAIMS"),
    )
    for finding in pilot_findings:
        connection.execute(
            """INSERT OR IGNORE INTO triangulation_findings(finding_id,triangulation_topic_id,
            finding_type,summary,evidence_gap,recommended_action,instructor_status,created_at,updated_at)
            VALUES (?,?,?,?,?,?,'ADVISORY',?,?)""",
            (finding[0], topic_pk, finding[1], finding[2], finding[3], finding[4], now, now),
        )
    latest = connection.execute(
        """SELECT id FROM deliverable_bundles WHERE lecture_pair_id=? AND part='A'
        ORDER BY created_at DESC,id DESC LIMIT 1""", (pair["id"],)
    ).fetchone()
    connection.execute(
        """INSERT OR IGNORE INTO student_learning_packages(learning_package_id,lecture_pair_id,lecture_id,
        part,classroom_deck_id,website_note_ids,raw_resource_ids,public_link_ids,verification_status,
        public_approval_status,instructor_status,created_at,updated_at)
        VALUES ('SLP-L01-A-WORKING-001',?,?,'A',?,'[]',?,'["WIKI-LINK-REFERENCES-MA"]',
        'NOT_YET_VERIFIED','NOT_APPROVED','WORKING_DRAFT',?,?)""",
        (pair["id"], pair["lecture_id"], latest[0] if latest else None,
         json.dumps(["IS529N-CENSUS-0449"] if raw_record else []), now, now),
    )
    connection.commit()
