from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from course_artifacts.config import CourseArtifactConfig, DEFAULT_CLASS_CONFIG, DEFAULT_RELATIONSHIP_CONFIG
from course_artifacts.database.connection import CourseArtifactDatabase
from course_artifacts.domain.models import ArtifactRegistration, RelationshipRegistration
from course_artifacts.repositories.artifact_repository import ArtifactRepository
from course_artifacts.repositories.class_repository import ArtifactClassRepository
from course_artifacts.repositories.relationship_repository import RelationshipRepository
from course_artifacts.services.artifact_service import ArtifactService
from course_artifacts.services.relationship_service import RelationshipService


class CourseArtifactDomainTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        config = CourseArtifactConfig(
            project_root=self.root,
            database_path=self.root / "local_state/database/course_artifacts.sqlite3",
            class_config_path=DEFAULT_CLASS_CONFIG,
            relationship_config_path=DEFAULT_RELATIONSHIP_CONFIG,
        )
        self.database = CourseArtifactDatabase(config)
        self.database.initialise()
        self.classes = ArtifactClassRepository(self.database)
        self.artifacts = ArtifactService(self.database)
        self.artifact_repository = ArtifactRepository(self.database)
        self.relationships = RelationshipService(self.database)

    def tearDown(self):
        self.temporary.cleanup()

    def register(self, title: str, class_code: str, suffix: str = ".txt") -> int:
        path = self.root / f"{title.replace(' ', '_')}{suffix}"
        path.write_text(f"synthetic fixture: {title}\n", encoding="utf-8")
        return self.artifacts.register(ArtifactRegistration(
            artifact_class_code=class_code,
            title=title,
            physical_path=path,
            symbolic_locator=f"<RESOURCE_REPOSITORY>/{path.name}",
            provenance="Synthetic temporary test fixture",
            source_repository="RESOURCE_REPOSITORY",
        ))

    def test_configuration_driven_six_classes(self):
        classes = self.classes.list()
        self.assertEqual(len(classes), 6)
        self.assertEqual(classes[0]["code"], "PUBLISHED_PRESENTATION_PDF")
        knowledge_maps = self.classes.get("INSTRUCTOR_DEFINED_CLASS_5")
        self.assertEqual(knowledge_maps["status"], "ACTIVE")
        self.assertEqual(
            knowledge_maps["label"], "Knowledge Maps and Visualisations"
        )
        self.assertIn(".canvas", knowledge_maps["accepted_extensions"])
        self.assertIn(".graphml", knowledge_maps["accepted_extensions"])
        self.assertIn(".mm", knowledge_maps["accepted_extensions"])
        self.assertIn(".cypher", knowledge_maps["accepted_extensions"])
        self.assertIn(".odp", self.classes.get("PRESENTATION_WORKBENCH")["accepted_extensions"])
        self.assertEqual(
            self.classes.get("FOUNDATIONAL_RESOURCE")["label"],
            "Lecture Raw Material",
        )
        self.assertEqual(classes[-1]["code"], "SPATIAL_RESOURCE")
        self.assertEqual(classes[-1]["label"], "Spatial Raw Material")
        self.assertEqual(classes[-1]["status"], "ACTIVE")

    def test_legacy_foundational_label_is_upgraded_without_schema_migration(self):
        with self.database.connection() as connection:
            connection.execute(
                """UPDATE artifact_classes SET label='Foundational Resources'
                WHERE code='FOUNDATIONAL_RESOURCE'"""
            )
        self.database.initialise()
        self.assertEqual(
            self.classes.get("FOUNDATIONAL_RESOURCE")["label"],
            "Lecture Raw Material",
        )
        with self.database.connection() as connection:
            self.assertEqual(
                connection.execute(
                    "SELECT COUNT(*) FROM course_artifact_schema_migrations"
                ).fetchone()[0],
                2,
            )

    def test_fifth_class_rename_requires_no_migration(self):
        fifth = self.classes.get("INSTRUCTOR_DEFINED_CLASS_5")
        self.classes.update(fifth["code"], {
            **fifth,
            "label": "Instructor Archive",
            "description": "Instructor-defined test label",
            "status": "ACTIVE",
        })
        self.database.initialise()
        renamed = self.classes.get("INSTRUCTOR_DEFINED_CLASS_5")
        self.assertEqual(renamed["label"], "Instructor Archive")
        self.assertEqual(renamed["status"], "ACTIVE")
        with self.database.connection() as connection:
            self.assertEqual(
                connection.execute(
                    "SELECT COUNT(*) FROM course_artifact_schema_migrations"
                ).fetchone()[0],
                2,
            )

    def test_artifact_registration_uses_lightweight_metadata(self):
        path = self.root / "Source_chapter.txt"
        artifact_pk = self.register("Source chapter", "FOUNDATIONAL_RESOURCE")
        artifact = self.artifact_repository.get(artifact_pk)
        self.assertEqual(artifact["file_extension"], ".txt")
        self.assertEqual(artifact["checksum_sha256"], "")
        self.assertEqual(artifact["physical_path"], "")
        duplicate_pk = self.artifacts.register(ArtifactRegistration(
            artifact_class_code="FOUNDATIONAL_RESOURCE",
            title="Second manual record",
            physical_path=path,
        ))
        self.assertNotEqual(artifact_pk, duplicate_pk)
        self.assertEqual(
            self.artifact_repository.get(duplicate_pk)["checksum_sha256"], ""
        )

    def test_directed_undirected_and_confirmed_relationships(self):
        source = self.register("Book chapter", "FOUNDATIONAL_RESOURCE")
        target = self.register("Working deck", "PRESENTATION_WORKBENCH", ".odp")
        directed = self.relationships.create(RelationshipRegistration(
            source, target, "CANDIDATE_INGREDIENT_FOR", status="SYSTEM_SUGGESTED"
        ))
        self.relationships.confirm(directed, "Instructor accepted the relationship")
        related = RelationshipRepository(self.database).list()
        self.assertEqual(related[0]["status"], "INSTRUCTOR_CONFIRMED")
        self.assertEqual(related[0]["directionality"], "DIRECTED")
        third = self.register("Corroborating source", "FOUNDATIONAL_RESOURCE")
        self.relationships.create(RelationshipRegistration(
            source, third, "CORROBORATES", directionality="UNDIRECTED"
        ))
        self.assertEqual(RelationshipRepository(self.database).list()[0]["directionality"], "UNDIRECTED")

    def test_self_relationship_is_prevented(self):
        artifact = self.register("Single source", "FOUNDATIONAL_RESOURCE")
        with self.assertRaisesRegex(ValueError, "itself"):
            self.relationships.create(RelationshipRegistration(
                artifact, artifact, "DERIVED_FROM"
            ))

    def test_source_to_ai_output_provenance(self):
        source = self.register("Empirical source", "FOUNDATIONAL_RESOURCE")
        ai_output = self.register("ChatGPT output", "AI_GENERATED_ARTIFACT")
        relationship = self.relationships.create(RelationshipRegistration(
            source, ai_output, "PROCESSED_BY_CHATGPT",
            status="INSTRUCTOR_CONFIRMED", evidence="Externally executed packet record",
        ))
        row = next(item for item in RelationshipRepository(self.database).list() if item["id"] == relationship)
        self.assertEqual(row["relationship_type"], "PROCESSED_BY_CHATGPT")
        self.assertEqual(row["status"], "INSTRUCTOR_CONFIRMED")

    def test_version_and_odp_to_pdf_publication_chains(self):
        odp_v1 = self.register("ODP v0.1", "PRESENTATION_WORKBENCH", ".odp")
        odp_v2 = self.register("ODP v0.2", "PRESENTATION_WORKBENCH", ".odp")
        pdf = self.register("Published PDF v0.2", "PUBLISHED_PRESENTATION_PDF", ".pdf")
        self.relationships.create(RelationshipRegistration(
            odp_v2, odp_v1, "SUPERSEDES", status="INSTRUCTOR_CONFIRMED"
        ))
        self.relationships.create(RelationshipRegistration(
            pdf, odp_v2, "EXPORT_OF", status="INSTRUCTOR_CONFIRMED"
        ))
        rows = RelationshipRepository(self.database).list()
        self.assertEqual({row["relationship_type"] for row in rows}, {"SUPERSEDES", "EXPORT_OF"})
        self.assertTrue(all(row["status"] == "INSTRUCTOR_CONFIRMED" for row in rows))

    def test_browser_safe_projection_excludes_physical_path(self):
        artifact = self.register("Private local source", "FOUNDATIONAL_RESOURCE")
        safe = self.artifacts.browser_safe(artifact)
        self.assertNotIn("physical_path", safe)
        self.assertTrue(safe["symbolic_locator"].startswith("<RESOURCE_REPOSITORY>"))


if __name__ == "__main__":
    unittest.main()
