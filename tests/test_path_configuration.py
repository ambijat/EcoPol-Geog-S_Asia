from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from course_artifacts.config import (
    CourseArtifactConfig, DEFAULT_CLASS_CONFIG, DEFAULT_RELATIONSHIP_CONFIG,
)
from course_artifacts.database.connection import CourseArtifactDatabase
from course_artifacts.repositories.artifact_repository import ArtifactRepository
from course_artifacts.services.path_resolver import (
    DEFAULT_ROOTS, LocalPathStore, PathResolver, REQUIRED_ROOTS,
)
from course_artifacts.services.scan_service import ScanService
from course_artifacts.services.visualization_service import VisualizationService


class PathConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.project = self.root / "application"
        self.project.mkdir()
        self.config = CourseArtifactConfig(
            project_root=self.project,
            database_path=self.root / "state/course_artifacts.sqlite3",
            class_config_path=DEFAULT_CLASS_CONFIG,
            relationship_config_path=DEFAULT_RELATIONSHIP_CONFIG,
            local_paths_path=self.root / "machine/local_paths.json",
        )
        self.database = CourseArtifactDatabase(self.config)
        self.database.initialise()
        self.store = LocalPathStore(self.config)
        self.resolver = PathResolver(self.config)

    def tearDown(self):
        self.temporary.cleanup()

    def configure_required(self) -> dict[str, Path]:
        paths = {}
        for code in REQUIRED_ROOTS:
            path = self.root / "repositories" / code.lower()
            path.mkdir(parents=True)
            self.store.update(code, path=str(path))
            paths[code] = path
        return paths

    def test_defaults_and_machine_local_persistence(self):
        payload = self.store.load()
        self.assertEqual(set(payload["artifact_roots"]), set(DEFAULT_ROOTS))
        self.assertEqual(
            payload["artifact_roots"]["PUBLISHED_PRESENTATION_PDF"]["access_mode"],
            "read_only",
        )
        self.assertEqual(
            payload["artifact_roots"]["PRESENTATION_WORKBENCH"]["access_mode"],
            "read_write",
        )
        chosen = self.root / "repositories/published"
        chosen.mkdir(parents=True)
        self.store.update("PUBLISHED_PRESENTATION_PDF", path=str(chosen))
        restarted = LocalPathStore(self.config).load()
        self.assertEqual(
            restarted["artifact_roots"]["PUBLISHED_PRESENTATION_PDF"]["path"],
            str(chosen),
        )
        self.assertTrue(self.config.local_paths_path.is_file())

    def test_required_roots_operational_with_optional_fifth_missing(self):
        self.configure_required()
        results = self.resolver.validate_all()
        self.assertTrue(self.resolver.operational())
        self.assertEqual(results["INSTRUCTOR_DEFINED_CLASS_5"].status, "MISSING")
        self.assertIn(
            results["PRESENTATION_WORKBENCH"].status,
            {"AVAILABLE_WRITABLE"},
        )
        self.assertEqual(
            results["FOUNDATIONAL_RESOURCE"].status, "AVAILABLE_READ_ONLY"
        )

    def test_required_roots_operational_with_optional_spatial_root_missing(self):
        self.configure_required()
        results = self.resolver.validate_all()
        self.assertTrue(self.resolver.operational())
        self.assertEqual(results["SPATIAL_RESOURCE"].status, "MISSING")

    def test_spatial_root_is_independent_twin_of_foundational_resource(self):
        self.configure_required()
        spatial_root = self.root / "repositories/spatial_resource"
        (spatial_root / "CROSS_BORDER/INDIA_PAKISTAN/LEC_12").mkdir(parents=True)
        source = spatial_root / "CROSS_BORDER/INDIA_PAKISTAN/LEC_12/source.pdf"
        source.write_bytes(b"spatial fixture")
        self.store.update("SPATIAL_RESOURCE", path=str(spatial_root))
        resolved = self.resolver.resolve(
            "SPATIAL_RESOURCE://CROSS_BORDER/INDIA_PAKISTAN/LEC_12/source.pdf"
        )
        self.assertEqual(resolved, source.resolve())
        self.assertEqual(
            self.resolver.to_symbolic("SPATIAL_RESOURCE", resolved),
            "SPATIAL_RESOURCE://CROSS_BORDER/INDIA_PAKISTAN/LEC_12/source.pdf",
        )
        self.assertEqual(
            self.resolver.validate_all()["FOUNDATIONAL_RESOURCE"].status,
            "AVAILABLE_READ_ONLY",
        )
        self.assertEqual(
            self.resolver.validate_all()["SPATIAL_RESOURCE"].status,
            "AVAILABLE_READ_ONLY",
        )

    def test_visualisation_root_accepts_portable_formats_not_live_databases(self):
        self.configure_required()
        visual_root = self.root / "repositories/knowledge_maps"
        visual_root.mkdir(parents=True)
        for filename in (
            "lecture-map.canvas", "concepts.mm", "course.graphml",
            "neo4j-export.cypher", "overview.svg", "live-database.sqlite",
        ):
            (visual_root / filename).write_text("synthetic", encoding="utf-8")
        self.store.update(
            "INSTRUCTOR_DEFINED_CLASS_5",
            path=str(visual_root), access_mode="read_write",
        )
        scan = ScanService(self.database, self.resolver)
        scan.scan("INSTRUCTOR_DEFINED_CLASS_5")
        candidates = scan.repository.latest_candidates(
            "INSTRUCTOR_DEFINED_CLASS_5"
        )
        self.assertEqual(
            {row["file_extension"] for row in candidates},
            {".canvas", ".mm", ".graphml", ".cypher", ".svg"},
        )
        self.assertNotIn(
            "live-database.sqlite",
            {row["relative_path"] for row in candidates},
        )

    def test_visualisation_service_creates_map_and_portable_neo4j_bundle(self):
        self.configure_required()
        visual_root = self.root / "repositories/knowledge_maps"
        visual_root.mkdir(parents=True)
        self.store.update(
            "INSTRUCTOR_DEFINED_CLASS_5",
            path=str(visual_root), access_mode="read_write",
        )
        service = VisualizationService(self.database, self.resolver)
        artifact_pk = service.create_mind_map("South Asia Regions")
        artifact = ArtifactRepository(self.database).get(artifact_pk)
        self.assertEqual(
            artifact["symbolic_locator"],
            "INSTRUCTOR_DEFINED_CLASS_5://South_Asia_Regions.mm",
        )
        self.assertTrue((visual_root / "South_Asia_Regions.mm").is_file())
        nodes, relationships = service.export_neo4j_bundle(artifact_pk)
        self.assertTrue(nodes.is_file())
        self.assertTrue(relationships.is_file())
        self.assertIn("artifact_id:ID", nodes.read_text(encoding="utf-8"))
        self.assertIn(":START_ID", relationships.read_text(encoding="utf-8"))

    def test_missing_removable_and_conflicting_roots(self):
        self.store.update("FOUNDATIONAL_RESOURCE", path="relative/repository")
        self.assertEqual(
            self.resolver.validate_all()["FOUNDATIONAL_RESOURCE"].status,
            "INACCESSIBLE",
        )
        missing = self.root / "not-present"
        self.store.update("FOUNDATIONAL_RESOURCE", path=str(missing))
        self.assertEqual(
            self.resolver.validate_all()["FOUNDATIONAL_RESOURCE"].status, "MISSING"
        )
        self.store.update(
            "FOUNDATIONAL_RESOURCE",
            path=str(Path("/", "media", "instructor-volume-that-is-offline", "resources")),
        )
        self.assertEqual(
            self.resolver.validate_all()["FOUNDATIONAL_RESOURCE"].status,
            "REMOVABLE_VOLUME_OFFLINE",
        )
        shared = self.root / "repositories/shared"
        shared.mkdir(parents=True)
        self.store.update("FOUNDATIONAL_RESOURCE", path=str(shared))
        self.store.update("PUBLISHED_PRESENTATION_PDF", path=str(shared))
        results = self.resolver.validate_all()
        self.assertEqual(results["FOUNDATIONAL_RESOURCE"].status, "CONFLICTING_ROOT")
        self.assertEqual(results["PUBLISHED_PRESENTATION_PDF"].status, "CONFLICTING_ROOT")

    def test_source_tree_root_requires_explicit_acceptance(self):
        nested = self.project / "local-repository"
        nested.mkdir()
        self.store.update("FOUNDATIONAL_RESOURCE", path=str(nested))
        result = self.resolver.validate_all()["FOUNDATIONAL_RESOURCE"]
        self.assertEqual(result.status, "CONFLICTING_ROOT")
        self.store.update("FOUNDATIONAL_RESOURCE", allow_inside_project=True)
        self.assertEqual(
            self.resolver.validate_all()["FOUNDATIONAL_RESOURCE"].status,
            "AVAILABLE_READ_ONLY",
        )

    def test_protected_source_cannot_be_configured_as_writable(self):
        protected = self.root / "historical-source"
        protected.mkdir()
        payload = self.store.load()
        payload["protected_read_only_paths"] = [str(protected)]
        self.store.save(payload)
        self.store.update(
            "PRESENTATION_WORKBENCH",
            path=str(protected),
            access_mode="read_write",
        )
        result = self.resolver.validate_all()["PRESENTATION_WORKBENCH"]
        self.assertEqual(result.status, "CONFLICTING_ROOT")
        self.assertIn("protected read-only source", result.detail)

    def test_symbolic_resolution_and_traversal_rejection(self):
        paths = self.configure_required()
        source = paths["FOUNDATIONAL_RESOURCE"] / "books/chapter_03.pdf"
        source.parent.mkdir()
        source.write_bytes(b"synthetic chapter")
        resolved = self.resolver.resolve(
            "FOUNDATIONAL_RESOURCE://books/chapter_03.pdf"
        )
        self.assertEqual(resolved, source.resolve())
        self.assertEqual(
            self.resolver.to_symbolic("FOUNDATIONAL_RESOURCE", source),
            "FOUNDATIONAL_RESOURCE://books/chapter_03.pdf",
        )
        for locator in (
            "FOUNDATIONAL_RESOURCE://../secret.pdf",
            "FOUNDATIONAL_RESOURCE://../../secret.pdf",
            "FOUNDATIONAL_RESOURCE:///etc/passwd",
        ):
            with self.subTest(locator=locator):
                with self.assertRaises(ValueError):
                    self.resolver.resolve(locator)

    def test_symbolic_link_escape_is_rejected(self):
        paths = self.configure_required()
        outside = self.root / "private-outside.txt"
        outside.write_text("outside", encoding="utf-8")
        link = paths["FOUNDATIONAL_RESOURCE"] / "escape.txt"
        link.symlink_to(outside)
        with self.assertRaisesRegex(ValueError, "outside"):
            self.resolver.resolve("FOUNDATIONAL_RESOURCE://escape.txt")

    def test_root_change_reresolution_uses_locator_availability(self):
        paths = self.configure_required()
        source = paths["FOUNDATIONAL_RESOURCE"] / "source.txt"
        source.write_text("original", encoding="utf-8")
        service = ScanService(self.database, self.resolver)
        service.scan("FOUNDATIONAL_RESOURCE")
        candidate = service.repository.candidates("FOUNDATIONAL_RESOURCE")[0]
        service.register_candidate(candidate["id"])
        artifacts = ArtifactRepository(self.database).list()
        self.assertEqual(
            self.resolver.reresolution_report(artifacts)[0]["outcome"], "resolved"
        )
        source.write_text("changed", encoding="utf-8")
        self.assertEqual(
            self.resolver.reresolution_report(artifacts)[0]["outcome"],
            "resolved",
        )
        replacement = self.root / "repositories/replacement"
        replacement.mkdir()
        self.store.update("FOUNDATIONAL_RESOURCE", path=str(replacement))
        self.assertEqual(
            self.resolver.reresolution_report(artifacts)[0]["outcome"], "missing"
        )

    def test_explicit_scan_creates_candidates_only_and_preserves_sources(self):
        paths = self.configure_required()
        root = paths["FOUNDATIONAL_RESOURCE"]
        first = root / "book.pdf"
        second = root / "notes.xyz"
        first.write_bytes(b"pdf fixture")
        second.write_bytes(b"opaque fixture")
        before = {
            path: (path.read_bytes(), path.stat().st_mtime_ns)
            for path in (first, second)
        }
        service = ScanService(self.database, self.resolver)
        self.assertEqual(service.repository.candidates(), [])
        self.assertEqual(ArtifactRepository(self.database).list(), [])
        service.scan("FOUNDATIONAL_RESOURCE")
        candidates = service.repository.candidates("FOUNDATIONAL_RESOURCE")
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["relative_path"], "book.pdf")
        self.assertEqual(candidates[0]["checksum_sha256"], "")
        self.assertEqual(ArtifactRepository(self.database).list(), [])
        registered = service.register_candidate(candidates[0]["id"])
        self.assertGreater(registered, 0)
        self.assertEqual(len(ArtifactRepository(self.database).list()), 1)
        for path in (first, second):
            self.assertEqual(before[path], (path.read_bytes(), path.stat().st_mtime_ns))

    def test_unchanged_scan_reuses_latest_census(self):
        paths = self.configure_required()
        source = paths["FOUNDATIONAL_RESOURCE"] / "source.pdf"
        source.write_bytes(b"stable source")
        service = ScanService(self.database, self.resolver)
        first_session = service.scan("FOUNDATIONAL_RESOURCE")
        second_session = service.scan("FOUNDATIONAL_RESOURCE")
        self.assertEqual(second_session, first_session)
        self.assertEqual(
            len(service.repository.candidates("FOUNDATIONAL_RESOURCE")),
            1,
        )

    def test_abandoned_scan_is_recovered_as_interrupted(self):
        self.configure_required()
        service = ScanService(self.database, self.resolver)
        session_pk = service.repository.create_session({
            "scan_id": "SCAN-INTERRUPTED-FIXTURE",
            "symbolic_root": "FOUNDATIONAL_RESOURCE",
            "physical_root": str(self.root / "repositories/foundational_resource"),
            "status": "RUNNING",
            "started_at": "2026-07-27T00:00:00+00:00",
        })
        ScanService(self.database, self.resolver)
        with self.database.connection() as connection:
            recovered = connection.execute(
                "SELECT status,completed_at FROM scan_sessions WHERE id=?",
                (session_pk,),
            ).fetchone()
        self.assertEqual(recovered["status"], "INTERRUPTED")
        self.assertTrue(recovered["completed_at"])

    def test_workbench_scan_uses_declared_formats_and_latest_census(self):
        paths = self.configure_required()
        root = paths["PRESENTATION_WORKBENCH"]
        (root / "lecture01.odp").write_bytes(b"odp one")
        (root / "lecture02.pptx").write_bytes(b"pptx two")
        (root / "source.pdf").write_bytes(b"unrelated pdf")
        (root / "wget-log").write_bytes(b"unrelated log")
        service = ScanService(self.database, self.resolver)

        service.scan("PRESENTATION_WORKBENCH")
        first_census = service.repository.latest_candidates(
            "PRESENTATION_WORKBENCH"
        )
        self.assertEqual(
            [item["relative_path"] for item in first_census],
            ["lecture01.odp", "lecture02.pptx"],
        )

        (root / "lecture03.odp").write_bytes(b"odp three")
        service.scan("PRESENTATION_WORKBENCH")
        latest_census = service.repository.latest_candidates(
            "PRESENTATION_WORKBENCH"
        )
        self.assertEqual(
            [item["relative_path"] for item in latest_census],
            ["lecture01.odp", "lecture02.pptx", "lecture03.odp"],
        )
        self.assertEqual(
            len(service.repository.candidates("PRESENTATION_WORKBENCH")), 5
        )

    def test_lecture_raw_material_is_aggregated_at_topic_folder_level(self):
        paths = self.configure_required()
        root = paths["FOUNDATIONAL_RESOURCE"]
        (root / "LEC_RES_1/region_concept").mkdir(parents=True)
        (root / "LEC_RES_1/region_concept/concept.pdf").write_bytes(b"concept")
        (root / "LEC_RES_1/region_concept/map.png").write_bytes(b"map")
        (root / "LEC_RES_1/latex/nested").mkdir(parents=True)
        (root / "LEC_RES_1/latex/nested/lecture.tex").write_bytes(b"ignored")
        (root / "LEC_RES_1/latex/nested/lecture.pdf").write_bytes(b"latex pdf")
        (root / "LEC_RES_2/agriculture").mkdir(parents=True)
        (root / "LEC_RES_2/agriculture/policy.docx").write_bytes(b"policy")
        (root / "LEC_RES_2/loose.pdf").write_bytes(b"loose")
        (root / "LEC_RES_1/.claude").mkdir()
        (root / "LEC_RES_1/.claude/notes.md").write_bytes(b"system")
        (root / "NOTES").mkdir()
        (root / "NOTES/course-note.pdf").write_bytes(b"course note")
        service = ScanService(self.database, self.resolver)
        service.scan("FOUNDATIONAL_RESOURCE")

        topics, stats = service.raw_material_topics(
            service.repository.latest_candidates("FOUNDATIONAL_RESOURCE")
        )
        self.assertEqual(
            [topic["topic_path"] for topic in topics],
            [
                "LEC_RES_1/latex",
                "LEC_RES_1/region_concept",
                "LEC_RES_2/agriculture",
                "NOTES",
            ],
        )
        by_path = {topic["topic_path"]: topic for topic in topics}
        self.assertEqual(by_path["LEC_RES_1/region_concept"]["file_count"], 2)
        self.assertEqual(by_path["LEC_RES_1/latex"]["file_count"], 1)
        self.assertEqual(by_path["NOTES"]["lecture_group"], "Course-wide")
        self.assertEqual(stats["topic_files"], 5)
        self.assertEqual(stats["loose_files"], 1)
        self.assertEqual(stats["system_files"], 1)

    def test_ai_notes_form_persistent_fifteen_lecture_revision_queue(self):
        paths = self.configure_required()
        ai_root = paths["AI_GENERATED_ARTIFACT"]
        workbench = paths["PRESENTATION_WORKBENCH"]
        published = paths["PUBLISHED_PRESENTATION_PDF"]
        for number in range(1, 16):
            (ai_root / f"LEC_{number}").mkdir()
        (ai_root / "LEC_1/note.tex").write_text(
            "\\section{AI-assisted note}", encoding="utf-8"
        )
        (ai_root / "LEC_1/note.pdf").write_bytes(b"PDF reading copy")
        for ignored_name in (
            "note.aux", "note.log", "note.out", "note.toc",
            "note.synctex.gz", "draft.md",
        ):
            (ai_root / "LEC_1" / ignored_name).write_text(
                "LaTeX build auxiliary", encoding="utf-8"
            )
        (ai_root / "LEC_RES_2_vault").mkdir()
        (ai_root / "LEC_RES_2_vault/legacy.tex").write_text(
            "\\section{Legacy AI-assisted note}", encoding="utf-8"
        )
        (ai_root / "unassigned").mkdir()
        (ai_root / "unassigned/readme.pdf").write_bytes(
            b"unassigned PDF reading copy"
        )
        (workbench / "LECTURE1").mkdir()
        (workbench / "LECTURE1/lecture1a.odp").write_bytes(b"odp 1a")
        (workbench / "LECTURE1/lecture1b.odp").write_bytes(b"odp 1b")
        (workbench / "LECTURE2").mkdir()
        (workbench / "LECTURE2/lecture2a.odp").write_bytes(b"odp 2a")
        (published / "lecture1a.pdf").write_bytes(b"pdf 1a")
        service = ScanService(self.database, self.resolver)
        service.scan("PRESENTATION_WORKBENCH")
        service.scan("PUBLISHED_PRESENTATION_PDF")
        service.scan("AI_GENERATED_ARTIFACT")

        rows, stats = service.ai_revision_queue(
            service.repository.latest_candidates("AI_GENERATED_ARTIFACT")
        )
        self.assertEqual(len(rows), 15)
        self.assertEqual(rows[0]["lecture_label"], "Lecture 1")
        self.assertEqual(rows[0]["ai_note_count"], 2)
        self.assertEqual(rows[0]["tex_display"], "note.tex")
        self.assertEqual(rows[0]["pdf_note_display"], "note.pdf")
        self.assertEqual(rows[0]["ai_folder"], "LEC_1")
        self.assertEqual(
            rows[0]["workbench_display"], "lecture1a.odp, lecture1b.odp"
        )
        self.assertEqual(rows[0]["published_display"], "lecture1a.pdf")
        self.assertEqual(rows[1]["ai_note_count"], 1)
        self.assertEqual(rows[14]["revision_status"], "No LaTeX notes")
        self.assertEqual(stats["ai_notes"], 3)
        self.assertEqual(stats["tex_sources"], 2)
        self.assertEqual(stats["pdf_notes"], 1)
        self.assertEqual(stats["lectures_with_notes"], 2)
        self.assertEqual(stats["unassigned_notes"], 1)
        candidates = service.repository.latest_candidates(
            "AI_GENERATED_ARTIFACT"
        )
        self.assertEqual(
            {candidate["file_extension"] for candidate in candidates},
            {".tex", ".pdf"},
        )
        self.assertEqual(len(candidates), 4)

        service.set_ai_revision_workbench(
            1, "LECTURE1/lecture1a.odp"
        )
        service.set_ai_revision_state(1, "INTEGRATED")
        restarted = ScanService(self.database, self.resolver)
        persisted, _stats = restarted.ai_revision_queue(
            restarted.repository.latest_candidates("AI_GENERATED_ARTIFACT")
        )
        self.assertEqual(
            persisted[0]["selected_workbench"],
            "LECTURE1/lecture1a.odp",
        )
        self.assertEqual(
            persisted[0]["revision_status"],
            "Integrated into presentation",
        )
        with self.database.connection() as connection:
            setting = connection.execute(
                """SELECT local_only FROM application_settings
                WHERE setting_key='ai_revision_queue'"""
            ).fetchone()
        self.assertEqual(setting["local_only"], 1)

    def test_workbench_candidates_propose_exact_published_pdf_matches(self):
        paths = self.configure_required()
        workbench = paths["PRESENTATION_WORKBENCH"]
        published = paths["PUBLISHED_PRESENTATION_PDF"]
        (workbench / "current").mkdir()
        (workbench / "current/lecture1a.odp").write_bytes(b"odp exact")
        (workbench / "current/lecture2a.odp").write_bytes(b"odp ambiguous")
        (workbench / "current/lecture15.odp").write_bytes(b"odp unpublished")
        (published / "current").mkdir()
        (published / "archive").mkdir()
        (published / "current/LECTURE1A.pdf").write_bytes(b"pdf exact")
        (published / "current/lecture2a.pdf").write_bytes(b"pdf current")
        (published / "archive/LECTURE2A.pdf").write_bytes(b"pdf archive")
        service = ScanService(self.database, self.resolver)
        service.scan("PUBLISHED_PRESENTATION_PDF")
        service.scan("PRESENTATION_WORKBENCH")

        rows = service.with_published_pdf_matches(
            service.repository.latest_candidates("PRESENTATION_WORKBENCH")
        )
        by_name = {Path(row["relative_path"]).name: row for row in rows}
        self.assertEqual(
            by_name["lecture1a.odp"]["published_pdf_match_status"],
            "MATCHED_CANDIDATE",
        )
        self.assertEqual(
            by_name["lecture1a.odp"]["published_pdf_match"], "LECTURE1A.pdf"
        )
        self.assertEqual(
            by_name["lecture2a.odp"]["published_pdf_match_status"], "AMBIGUOUS"
        )
        self.assertEqual(
            len(by_name["lecture2a.odp"]["published_pdf_matches"]), 2
        )
        self.assertEqual(
            by_name["lecture15.odp"]["published_pdf_match_status"], "NO_MATCH"
        )

    def test_latest_census_uses_natural_lecture_filename_sequence(self):
        paths = self.configure_required()
        root = paths["PRESENTATION_WORKBENCH"]
        expected = [
            "lecture1a.odp", "lecture1b.odp",
            "lecture2a.odp", "lecture2b.odp", "lecture2a_res.odp",
            "lecture7a.odp", "lecture7b.odp", "lecture7_old.odp",
            "LECTURE10a.odp",
        ]
        for filename in reversed(expected):
            (root / filename).write_bytes(filename.encode())
        service = ScanService(self.database, self.resolver)
        service.scan("PRESENTATION_WORKBENCH")
        self.assertEqual(
            [
                Path(row["relative_path"]).name
                for row in service.repository.latest_candidates(
                    "PRESENTATION_WORKBENCH"
                )
            ],
            expected,
        )

    def test_candidate_review_actions_and_manual_duplicate_decision(self):
        paths = self.configure_required()
        source = paths["FOUNDATIONAL_RESOURCE"] / "source.md"
        source.write_text("fixture", encoding="utf-8")
        service = ScanService(self.database, self.resolver)
        service.scan("FOUNDATIONAL_RESOURCE")
        candidate = service.repository.candidates("FOUNDATIONAL_RESOURCE")[0]
        service.register_candidate(candidate["id"])
        service.scan("FOUNDATIONAL_RESOURCE", force=True)
        duplicate = service.repository.candidates("FOUNDATIONAL_RESOURCE")[0]
        self.assertEqual(duplicate["candidate_status"], "AWAITING_REVIEW")
        service.decide(duplicate["id"], "MARKED_DUPLICATE")
        self.assertEqual(
            service.repository.get_candidate(duplicate["id"])["candidate_status"],
            "MARKED_DUPLICATE",
        )
        registered = ArtifactRepository(self.database).list()[0]
        service.scan("FOUNDATIONAL_RESOURCE", force=True)
        relation_candidate = service.repository.candidates("FOUNDATIONAL_RESOURCE")[0]
        service.decide(
            relation_candidate["id"], "RELATE_TO_EXISTING",
            related_artifact_id=registered["id"],
        )
        updated = service.repository.get_candidate(relation_candidate["id"])
        self.assertEqual(updated["candidate_status"], "RELATE_TO_EXISTING")
        self.assertEqual(updated["related_artifact_id"], registered["id"])

    def test_committed_example_contains_no_absolute_paths(self):
        example = Path("config/local_paths.example.json")
        payload = json.loads(example.read_text(encoding="utf-8"))
        self.assertTrue(all(
            item["path"] == "" for item in payload["artifact_roots"].values()
        ))
        text = example.read_text(encoding="utf-8")
        self.assertNotIn("/" + "home/", text)
        self.assertNotIn("/" + "media/", text)


if __name__ == "__main__":
    unittest.main()
