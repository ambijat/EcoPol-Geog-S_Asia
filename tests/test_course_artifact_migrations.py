from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from course_artifacts.config import CourseArtifactConfig, DEFAULT_CLASS_CONFIG, DEFAULT_RELATIONSHIP_CONFIG
from course_artifacts.database.connection import CourseArtifactDatabase


class CourseArtifactMigrationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.path = self.root / "course_artifacts.sqlite3"
        self.config = CourseArtifactConfig(
            project_root=self.root,
            database_path=self.path,
            class_config_path=DEFAULT_CLASS_CONFIG,
            relationship_config_path=DEFAULT_RELATIONSHIP_CONFIG,
        )

    def tearDown(self):
        self.temporary.cleanup()

    def test_fresh_creation_and_repeat_idempotence(self):
        database = CourseArtifactDatabase(self.config)
        database.initialise()
        database.initialise()
        with database.connection() as connection:
            tables = {
                row[0] for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            self.assertIn("artifacts", tables)
            self.assertIn("artifact_relationships", tables)
            self.assertEqual(
                connection.execute(
                    "SELECT COUNT(*) FROM course_artifact_schema_migrations"
                ).fetchone()[0],
                2,
            )
            self.assertEqual(
                connection.execute("SELECT COUNT(*) FROM artifact_classes").fetchone()[0],
                6,
            )
            self.assertEqual(
                connection.execute("SELECT COUNT(*) FROM relationship_types").fetchone()[0],
                26,
            )

    def test_retired_migration_ledger_name_is_upgraded_in_place(self):
        database = CourseArtifactDatabase(self.config)
        database.initialise()
        current_table = "course_artifact_schema_migrations"
        retired_table = "archae" + "ology_schema_migrations"
        with database.connection() as connection:
            connection.execute(
                f"ALTER TABLE {current_table} RENAME TO {retired_table}"
            )
        database.initialise()
        with database.connection() as connection:
            tables = {
                row[0] for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            self.assertIn(current_table, tables)
            self.assertNotIn(retired_table, tables)
            self.assertEqual(
                connection.execute(
                    f"SELECT COUNT(*) FROM {current_table}"
                ).fetchone()[0],
                2,
            )

    def test_five_class_database_upgrades_to_six_classes_without_loss(self):
        """A database seeded before SPATIAL_RESOURCE existed must gain the
        sixth class in place, without duplicating or disturbing the five
        classes and their existing records that were already there."""
        five_class_config = self.root / "five_class_artifact_classes.yaml"
        five_class_config.write_text(
            (DEFAULT_CLASS_CONFIG.read_text(encoding="utf-8")).replace(
                "  - code: SPATIAL_RESOURCE\n"
                "    label: Spatial Raw Material\n"
                "    description: Country, regional, and cross-border source "
                "material organized by spatial scope and lecture. The "
                "horizontal counterpart to the topical Lecture Raw Material "
                "root.\n"
                "    icon: GEO\n"
                "    display_order: 6\n"
                "    active: true\n"
                "    status: ACTIVE\n"
                "    accepted_extensions: [.pdf, .docx, .odt, .txt, .md, "
                ".csv, .xlsx, .ods, .jpg, .jpeg, .png, .svg]\n"
                "    default_relationship_suggestions: [EXTRACTED_FROM, "
                "QUOTES, CORROBORATES, RELATES_TO_TOPIC]\n",
                "",
            ),
            encoding="utf-8",
        )
        five_class_config_text = five_class_config.read_text(encoding="utf-8")
        self.assertNotIn("SPATIAL_RESOURCE", five_class_config_text)
        self.assertEqual(five_class_config_text.count("- code:"), 5)

        pre_upgrade_config = CourseArtifactConfig(
            project_root=self.root,
            database_path=self.path,
            class_config_path=five_class_config,
            relationship_config_path=DEFAULT_RELATIONSHIP_CONFIG,
        )
        database = CourseArtifactDatabase(pre_upgrade_config)
        database.initialise()

        with database.connection() as connection:
            self.assertEqual(
                connection.execute(
                    "SELECT COUNT(*) FROM artifact_classes"
                ).fetchone()[0],
                5,
            )
            foundational_id = connection.execute(
                "SELECT id FROM artifact_classes WHERE code='FOUNDATIONAL_RESOURCE'"
            ).fetchone()[0]
            workbench_id = connection.execute(
                "SELECT id FROM artifact_classes WHERE code='PRESENTATION_WORKBENCH'"
            ).fetchone()[0]
            relationship_type_id = connection.execute(
                "SELECT id FROM relationship_types WHERE code='EXTRACTED_FROM'"
            ).fetchone()[0]
            now = "2026-07-20T00:00:00+00:00"
            connection.execute(
                """INSERT INTO artifacts(
                    artifact_id,artifact_class_id,title,symbolic_locator,
                    created_at,updated_at
                ) VALUES ('ARTIFACT-PRE-UPGRADE-1',?,'Pre-upgrade source',
                    'FOUNDATIONAL_RESOURCE://book.pdf',?,?)""",
                (foundational_id, now, now),
            )
            connection.execute(
                """INSERT INTO artifacts(
                    artifact_id,artifact_class_id,title,symbolic_locator,
                    created_at,updated_at
                ) VALUES ('ARTIFACT-PRE-UPGRADE-2',?,'Pre-upgrade workbench',
                    'PRESENTATION_WORKBENCH://deck.odp',?,?)""",
                (workbench_id, now, now),
            )
            source_pk, target_pk = (
                row[0] for row in connection.execute(
                    "SELECT id FROM artifacts ORDER BY id"
                ).fetchall()
            )
            connection.execute(
                """INSERT INTO artifact_relationships(
                    relationship_id,source_artifact_id,target_artifact_id,
                    relationship_type_id,directionality,status,confidence,
                    created_by,created_at
                ) VALUES ('REL-PRE-UPGRADE-1',?,?,?,'DIRECTED','SUGGESTED',
                    'MEDIUM','test-fixture',?)""",
                (source_pk, target_pk, relationship_type_id, now),
            )
            connection.execute(
                """INSERT INTO instructor_decisions(
                    decision_id,decision_type,subject_type,subject_id,summary,created_at
                ) VALUES ('DECISION-PRE-UPGRADE-1','FIFTH_CLASS_DEFINITION',
                    'ARTIFACT_CLASS','INSTRUCTOR_DEFINED_CLASS_5',
                    'Pre-upgrade instructor decision fixture',?)""",
                (now,),
            )
            session_pk = connection.execute(
                """INSERT INTO scan_sessions(
                    scan_id,symbolic_root,physical_root,status,started_at
                ) VALUES ('SCAN-PRE-UPGRADE-1','FOUNDATIONAL_RESOURCE',
                    '/pre-upgrade/root','COMPLETED',?)""",
                (now,),
            ).lastrowid
            connection.execute(
                """INSERT INTO scan_candidates(
                    scan_session_id,candidate_id,relative_path
                ) VALUES (?,'CAND-PRE-UPGRADE-1','notes.md')""",
                (session_pk,),
            )

        # Simulate the application code being upgraded to the current
        # six-class release while the on-disk database file is untouched.
        post_upgrade_config = CourseArtifactConfig(
            project_root=self.root,
            database_path=self.path,
            class_config_path=DEFAULT_CLASS_CONFIG,
            relationship_config_path=DEFAULT_RELATIONSHIP_CONFIG,
        )
        upgraded = CourseArtifactDatabase(post_upgrade_config)
        upgraded.initialise()
        upgraded.initialise()  # idempotence under the six-class config too

        with upgraded.connection() as connection:
            classes = connection.execute(
                "SELECT code FROM artifact_classes ORDER BY code"
            ).fetchall()
            codes = [row[0] for row in classes]
            self.assertEqual(len(codes), 6)
            self.assertEqual(len(set(codes)), 6)
            self.assertIn("SPATIAL_RESOURCE", codes)
            self.assertEqual(
                connection.execute(
                    "SELECT id FROM artifact_classes WHERE code='FOUNDATIONAL_RESOURCE'"
                ).fetchone()[0],
                foundational_id,
            )
            self.assertEqual(
                connection.execute(
                    "SELECT id FROM artifact_classes WHERE code='PRESENTATION_WORKBENCH'"
                ).fetchone()[0],
                workbench_id,
            )

            self.assertEqual(
                [
                    tuple(row) for row in connection.execute(
                        "SELECT artifact_id FROM artifacts ORDER BY id"
                    ).fetchall()
                ],
                [("ARTIFACT-PRE-UPGRADE-1",), ("ARTIFACT-PRE-UPGRADE-2",)],
            )
            self.assertEqual(
                connection.execute(
                    "SELECT relationship_id FROM artifact_relationships"
                ).fetchone()[0],
                "REL-PRE-UPGRADE-1",
            )
            self.assertEqual(
                connection.execute(
                    "SELECT decision_id FROM instructor_decisions "
                    "WHERE decision_id='DECISION-PRE-UPGRADE-1'"
                ).fetchone()[0],
                "DECISION-PRE-UPGRADE-1",
            )
            self.assertEqual(
                connection.execute(
                    "SELECT candidate_id FROM scan_candidates"
                ).fetchone()[0],
                "CAND-PRE-UPGRADE-1",
            )

    def test_legacy_database_is_extended_without_deletion(self):
        connection = sqlite3.connect(self.path)
        connection.execute(
            "CREATE TABLE lecture_pairs(id INTEGER PRIMARY KEY, lecture_id TEXT NOT NULL)"
        )
        connection.execute("INSERT INTO lecture_pairs(lecture_id) VALUES ('LEGACY-L01')")
        connection.commit()
        connection.close()
        database = CourseArtifactDatabase(self.config)
        database.initialise()
        with database.connection() as connection:
            self.assertEqual(
                connection.execute("SELECT lecture_id FROM lecture_pairs").fetchone()[0],
                "LEGACY-L01",
            )
            self.assertIsNotNone(
                connection.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name='artifacts'"
                ).fetchone()
            )


if __name__ == "__main__":
    unittest.main()
