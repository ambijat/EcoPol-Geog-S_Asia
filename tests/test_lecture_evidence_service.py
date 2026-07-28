"""Tests for the read-only lecture evidence adapter.

Every test builds its own synthetic lecture database in a temporary directory,
so the suite never depends on — and never touches — the instructor's own
databases. One test asserts read-only behaviour by attempting a write through
the adapter's connection and requiring it to fail.
"""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
import warnings
from pathlib import Path

from course_artifacts.config import CourseArtifactConfig
from course_artifacts.services.candidate_pool_service import (
    CandidatePoolService,
    CandidatePoolUnavailable,
    lecture_of,
)
from course_artifacts.services.lecture_evidence_service import (
    ROW_KEYS,
    UNAVAILABLE,
    UNMAPPED,
    LectureDatabaseIncompatible,
    LectureDatabaseUnavailable,
    LectureEvidenceService,
    read_only_connection,
)


def make_pool_service(root: Path) -> CandidatePoolService:
    """A CandidatePoolService pointed at a synthetic artifact database.

    Keeps LectureEvidenceRowTests fully isolated from the instructor's real
    ``local_state/database/course_artifacts.sqlite3`` — without this, the
    service's lazily-constructed default CandidatePoolService would resolve
    to the real project path.
    """
    artifact_database = root / "local_state/database/course_artifacts.sqlite3"
    build_artifact_database(artifact_database)
    return CandidatePoolService(
        CourseArtifactConfig(project_root=root, database_path=artifact_database)
    )


LECTURE_SCHEMA = """
CREATE TABLE lecture_pairs (
    id INTEGER PRIMARY KEY,
    lecture_id TEXT NOT NULL,
    lecture_number INTEGER NOT NULL,
    weekly_title TEXT NOT NULL DEFAULT ''
);
CREATE TABLE lecture_parts (
    id INTEGER PRIMARY KEY,
    lecture_pair_id INTEGER NOT NULL,
    part TEXT NOT NULL,
    identifier TEXT NOT NULL DEFAULT '',
    lifecycle_status TEXT NOT NULL DEFAULT '',
    approval_status TEXT NOT NULL DEFAULT ''
);
CREATE TABLE lecture_knowledge_clusters (
    id INTEGER PRIMARY KEY,
    cluster_id TEXT NOT NULL,
    lecture_pair_id INTEGER NOT NULL,
    part TEXT NOT NULL,
    title TEXT NOT NULL DEFAULT '',
    slide_start INTEGER,
    slide_end INTEGER,
    thematic_function TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT '',
    workflow_state TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE deliverable_bundles (
    id INTEGER PRIMARY KEY,
    lecture_pair_id INTEGER NOT NULL,
    part TEXT NOT NULL,
    version TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT '',
    approved INTEGER NOT NULL DEFAULT 0,
    visibility TEXT NOT NULL DEFAULT '',
    classroom_use_status TEXT NOT NULL DEFAULT '',
    validation_status TEXT NOT NULL DEFAULT '',
    pptx_path TEXT NOT NULL DEFAULT '',
    pdf_path TEXT NOT NULL DEFAULT '',
    page_count INTEGER
);
CREATE TABLE cluster_resource_alignments (
    id INTEGER PRIMARY KEY,
    alignment_id TEXT NOT NULL,
    cluster_id INTEGER NOT NULL,
    resource_id INTEGER,
    title TEXT NOT NULL DEFAULT ''
);
"""

ARTIFACT_SCHEMA = """
CREATE TABLE scan_sessions (
    id INTEGER PRIMARY KEY,
    scan_id TEXT NOT NULL,
    symbolic_root TEXT NOT NULL,
    status TEXT NOT NULL,
    completed_at TEXT NOT NULL DEFAULT '',
    file_count INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE scan_candidates (
    id INTEGER PRIMARY KEY,
    scan_session_id INTEGER NOT NULL,
    relative_path TEXT NOT NULL,
    proposed_class_code TEXT NOT NULL DEFAULT '',
    candidate_status TEXT NOT NULL DEFAULT 'AWAITING_REVIEW'
);
"""

CLUSTERS = [
    ("KC01", "Regional imagination", 3, 18, "How is South Asia imagined?",
     "IN_PROGRESS", '{"cluster": "READY", "historical": "COMPLETE"}'),
    ("KC02", "Environment and society", 19, 27, "Physical and social linkage",
     "NOT_STARTED", "{}"),
    ("KC03", "Population and political economy", 28, 39, "Population and economy",
     "NOT_STARTED", "{}"),
    ("KC04", "Concept of region", 40, 46, "Conceptual vocabulary",
     "NOT_STARTED", "{}"),
    ("KC05", "South Asia as regional formation", 47, 56, "Limits of formation",
     "NOT_STARTED", "{}"),
    ("KC06", "Comparative indicators", 57, 60, "Indicator comparison",
     "NOT_STARTED", "{}"),
]


def build_lecture_database(path: Path, *, alignments: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    try:
        connection.executescript(LECTURE_SCHEMA)
        connection.execute(
            "INSERT INTO lecture_pairs(id, lecture_id, lecture_number) "
            "VALUES (1, 'IS529N-L01', 1)"
        )
        connection.execute(
            "INSERT INTO lecture_parts(lecture_pair_id, part, identifier, "
            "lifecycle_status, approval_status) "
            "VALUES (1, 'A', 'IS529N-L01-A', 'DECK_DRAFTED', 'NOT_REVIEWED')"
        )
        for index, cluster in enumerate(CLUSTERS, start=1):
            connection.execute(
                "INSERT INTO lecture_knowledge_clusters(id, cluster_id, "
                "lecture_pair_id, part, title, slide_start, slide_end, "
                "thematic_function, status, workflow_state) "
                "VALUES (?,?,1,'A',?,?,?,?,?,?)",
                (index, cluster[0], cluster[1], cluster[2], cluster[3],
                 cluster[4], cluster[5], cluster[6]),
            )
        connection.execute(
            "INSERT INTO deliverable_bundles(lecture_pair_id, part, version, "
            "status, approved, visibility, classroom_use_status, "
            "validation_status, pptx_path, pdf_path, page_count) "
            "VALUES (1,'A','v0.4','REVISED',0,'PRIVATE',"
            "'NOT_FOR_CLASSROOM_USE','REVIEW_REQUIRED','decks/l01a.pptx',"
            "'pdf/l01a.pdf',18)"
        )
        if alignments:
            for index in range(1, 6):
                connection.execute(
                    "INSERT INTO cluster_resource_alignments"
                    "(alignment_id, cluster_id, resource_id, title) "
                    "VALUES (?,1,?,?)",
                    (f"ALIGN-{index:02d}", index, f"Source {index}"),
                )
        connection.commit()
    finally:
        connection.close()


def build_artifact_database(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    try:
        connection.executescript(ARTIFACT_SCHEMA)
        sessions = [
            (1, "SCAN-OLD", "FOUNDATIONAL_RESOURCE", "COMPLETED"),
            (2, "SCAN-NEW", "FOUNDATIONAL_RESOURCE", "COMPLETED"),
            (3, "SCAN-SPATIAL", "SPATIAL_RESOURCE", "COMPLETED"),
            (4, "SCAN-RUNNING", "AI_GENERATED_ARTIFACT", "RUNNING"),
        ]
        for session in sessions:
            connection.execute(
                "INSERT INTO scan_sessions(id, scan_id, symbolic_root, status, "
                "completed_at) VALUES (?,?,?,?,'2026-07-27T00:00:00+00:00')",
                session,
            )
        superseded = [
            "LEC_RES_1/puranas_geo/a.pdf",
            "LEC_RES_1/puranas_geo/b.pdf",
            "LEC_RES_1/puranas_geo/c.pdf",
        ]
        current = [
            "LEC_RES_1/puranas_geo/a.pdf",
            "LEC_RES_1/ohkspate/d.pdf",
            "LEC_RES_2/other/e.pdf",
        ]
        spatial = [
            "PAKISTAN/LEC_1/floods.png",
            "REGIONAL_SOUTH_ASIA/LEC_1/climate/x.png",
            "NEPAL/LEC_4/y.png",
        ]
        for path_text in superseded:
            connection.execute(
                "INSERT INTO scan_candidates(scan_session_id, relative_path, "
                "proposed_class_code) VALUES (1,?,'FOUNDATIONAL_RESOURCE')",
                (path_text,),
            )
        for path_text in current:
            connection.execute(
                "INSERT INTO scan_candidates(scan_session_id, relative_path, "
                "proposed_class_code) VALUES (2,?,'FOUNDATIONAL_RESOURCE')",
                (path_text,),
            )
        for path_text in spatial:
            connection.execute(
                "INSERT INTO scan_candidates(scan_session_id, relative_path, "
                "proposed_class_code) VALUES (3,?,'SPATIAL_RESOURCE')",
                (path_text,),
            )
        connection.commit()
    finally:
        connection.close()


class LectureEvidenceRowTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.lecture_database = self.root / "gui/database/is529n_cockpit.sqlite3"
        build_lecture_database(self.lecture_database)
        self.pool_service = make_pool_service(self.root)
        self.artifact_database = self.pool_service.database_path
        self.service = LectureEvidenceService(
            self.lecture_database, pool_service=self.pool_service
        )
        self.rows = self.service.lecture_evidence_rows(1, "A")

    def tearDown(self):
        self.temporary.cleanup()

    def test_lecture_1a_returns_exactly_six_cluster_rows(self):
        self.assertEqual(len(self.rows), 6)

    def test_rows_are_in_kc01_to_kc06_order(self):
        self.assertEqual(
            [row["cluster_id"] for row in self.rows],
            ["KC01", "KC02", "KC03", "KC04", "KC05", "KC06"],
        )

    def test_slide_ranges_and_teaching_questions_come_from_lecture_database(self):
        self.assertEqual(self.rows[0]["slide_range"], "3-18")
        self.assertEqual(self.rows[5]["slide_range"], "57-60")
        self.assertEqual(
            self.rows[0]["teaching_question"], "How is South Asia imagined?"
        )
        self.assertEqual(self.rows[3]["cluster_title"], "Concept of region")

    def test_unmapped_rather_than_zero_when_no_cluster_mapping_exists(self):
        for row in self.rows[1:]:
            self.assertEqual(row["topical_evidence_count"], UNMAPPED)
            self.assertNotEqual(row["topical_evidence_count"], 0)

    def test_integer_count_only_where_explicit_mapping_exists(self):
        self.assertEqual(self.rows[0]["topical_evidence_count"], 5)

    def test_categories_absent_from_schema_report_unavailable(self):
        for row in self.rows:
            self.assertEqual(row["spatial_evidence_count"], UNAVAILABLE)
            self.assertEqual(row["ai_note_count"], UNAVAILABLE)

    def test_missing_mapping_structure_reports_unavailable_not_unmapped(self):
        database = self.root / "no_alignments.sqlite3"
        build_lecture_database(database, alignments=False)
        connection = sqlite3.connect(database)
        connection.execute("DROP TABLE cluster_resource_alignments")
        connection.commit()
        connection.close()
        rows = LectureEvidenceService(
            database, pool_service=self.pool_service
        ).lecture_evidence_rows(1, "A")
        self.assertTrue(
            all(row["topical_evidence_count"] == UNAVAILABLE for row in rows)
        )

    def test_empty_mapping_table_reports_unmapped_not_zero(self):
        database = self.root / "empty_alignments.sqlite3"
        build_lecture_database(database, alignments=False)
        rows = LectureEvidenceService(
            database, pool_service=self.pool_service
        ).lecture_evidence_rows(1, "A")
        self.assertTrue(
            all(row["topical_evidence_count"] == UNMAPPED for row in rows)
        )

    def test_zero_only_when_mapping_structure_records_completion(self):
        connection = sqlite3.connect(self.lecture_database)
        connection.execute(
            "UPDATE lecture_knowledge_clusters "
            "SET workflow_state='{\"resources\": \"COMPLETE\"}' "
            "WHERE cluster_id='KC02'"
        )
        connection.commit()
        connection.close()
        rows = self.service.lecture_evidence_rows(1, "A")
        self.assertEqual(rows[1]["topical_evidence_count"], 0)

    def test_result_keys_conform_to_documented_contract(self):
        for row in self.rows:
            self.assertEqual(tuple(row.keys()), ROW_KEYS)

    def test_workbench_and_pdf_statuses_are_qualified_not_asserted(self):
        workbench = self.rows[0]["workbench_status"]
        published = self.rows[0]["published_pdf_status"]
        self.assertIn("PART_LEVEL", workbench)
        self.assertIn("DELIVERABLE_REFERENCED", workbench)
        self.assertIn("NOT_APPROVED", workbench)
        self.assertIn("PDF_REFERENCED", published)
        self.assertIn("18 pages", published)
        self.assertIn("NOT_FOR_CLASSROOM_USE", published)

    def test_next_action_is_plain_language_and_state_derived(self):
        self.assertEqual(self.rows[0]["next_action"], "Review teaching question")
        self.assertEqual(self.rows[1]["next_action"], "Begin cluster preparation")

    def test_unknown_lecture_or_part_returns_empty_result(self):
        self.assertEqual(self.service.lecture_evidence_rows(99, "A"), [])
        self.assertEqual(self.service.lecture_evidence_rows(1, "Z"), [])

    def test_missing_database_produces_clear_domain_error(self):
        service = LectureEvidenceService(
            self.root / "absent.sqlite3", pool_service=self.pool_service
        )
        with self.assertRaises(LectureDatabaseUnavailable) as caught:
            service.lecture_evidence_rows(1, "A")
        self.assertIn("lecture cockpit database", str(caught.exception))

    def test_incompatible_schema_produces_clear_domain_error(self):
        database = self.root / "empty.sqlite3"
        sqlite3.connect(database).close()
        with self.assertRaises(LectureDatabaseIncompatible):
            LectureEvidenceService(
                database, pool_service=self.pool_service
            ).lecture_evidence_rows(1, "A")

    def test_service_opens_the_lecture_database_read_only(self):
        with read_only_connection(self.lecture_database) as connection:
            with self.assertRaises(sqlite3.OperationalError):
                connection.execute(
                    "UPDATE lecture_knowledge_clusters SET title='tampered'"
                )

    def test_no_database_modification_occurs(self):
        lecture_before = self.lecture_database.read_bytes()
        artifact_before = self.artifact_database.read_bytes()
        self.service.lecture_evidence_rows(1, "A")
        self.service.lecture_evidence_rows(99, "B")
        self.assertEqual(self.lecture_database.read_bytes(), lecture_before)
        self.assertEqual(self.artifact_database.read_bytes(), artifact_before)

    def test_connections_close_without_resource_warning(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            LectureEvidenceService(
                self.lecture_database, pool_service=self.pool_service
            ).lecture_evidence_rows(1, "A")
        self.assertEqual(
            [w for w in caught if issubclass(w.category, ResourceWarning)], []
        )


class CandidatePoolTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.artifact_database = (
            self.root / "local_state/database/course_artifacts.sqlite3"
        )
        build_artifact_database(self.artifact_database)
        self.service = CandidatePoolService(
            CourseArtifactConfig(
                project_root=self.root, database_path=self.artifact_database
            )
        )

    def tearDown(self):
        self.temporary.cleanup()

    def test_lecture_pools_are_reported_separately_from_cluster_rows(self):
        summary = self.service.lecture_pool_summary(1)
        self.assertEqual(summary["mapping_status"], UNMAPPED)
        self.assertEqual(summary["lecture_number"], 1)

    def test_pool_counts_use_latest_completed_census_only(self):
        summary = self.service.lecture_pool_summary(1)
        # Session 1 held three superseded Lecture 1 rows; only session 2 counts.
        self.assertEqual(summary["topical_candidate_pool"], 2)

    def test_lecture_attribution_matches_any_path_segment(self):
        summary = self.service.lecture_pool_summary(1)
        self.assertEqual(summary["spatial_candidate_pool"], 2)
        self.assertEqual(lecture_of("PAKISTAN/LEC_1/floods.png"), 1)
        self.assertEqual(lecture_of("LEC_RES_12/x/y.pdf"), 12)
        self.assertIsNone(lecture_of("LEC_RES_99/x/y.pdf"))
        self.assertIsNone(lecture_of("unsorted/notes.pdf"))

    def test_category_without_completed_census_reports_unavailable(self):
        summary = self.service.lecture_pool_summary(1)
        self.assertEqual(summary["ai_note_candidate_pool"], UNAVAILABLE)

    def test_missing_artifact_database_produces_clear_domain_error(self):
        service = CandidatePoolService(
            CourseArtifactConfig(
                project_root=self.root,
                database_path=self.root / "absent.sqlite3",
            )
        )
        with self.assertRaises(CandidatePoolUnavailable):
            service.lecture_pool_summary(1)

    def test_pool_read_does_not_modify_the_artifact_database(self):
        before = self.artifact_database.read_bytes()
        self.service.lecture_pool_summary(1)
        self.assertEqual(self.artifact_database.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
