from __future__ import annotations

import hashlib
import json
import sqlite3
import subprocess
import tempfile
import unittest
from pathlib import Path, PurePosixPath

from fastapi.testclient import TestClient

from gui.app import create_app
from gui.database import initialise
from gui.pptx_service import generate_pptx, next_deck_filename, validate_deck_plan
from gui.services import (
    add_historical_slide, add_note, add_slide_plan, assign_resource,
    classify_public_path, git_readiness, prepare_draft_event, update_historical_slide_status,
    record_historical_derivative, set_part_approval, update_slide_decision, validate_relative_path,
)


class CockpitTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        (self.root / "reports").mkdir()
        (self.root / "reports/public_include_manifest.txt").write_text(
            "course/lectures/lecture_01/public.md\n", encoding="utf-8"
        )
        (self.root / "reports/public_exclude_manifest.txt").write_text(
            "private.txt\n", encoding="utf-8"
        )
        self.database_path = self.root / "state/cockpit.sqlite3"
        self.connection = initialise(self.database_path, self.root / "missing-census.json")
        subprocess.run(["git", "init", "-b", "main"], cwd=self.root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.email", "test.invalid@example.invalid"], cwd=self.root, check=True)
        (self.root / "seed.txt").write_text("seed\n", encoding="utf-8")
        subprocess.run(["git", "add", "seed.txt"], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-m", "seed"], cwd=self.root, check=True, capture_output=True)

    def tearDown(self) -> None:
        self.connection.close()
        self.temporary.cleanup()

    @property
    def pair_id(self) -> int:
        return self.connection.execute(
            "SELECT id FROM lecture_pairs WHERE lecture_number=1"
        ).fetchone()[0]

    def seed_resource_and_deck(self) -> tuple[int, int]:
        self.connection.execute(
            """INSERT INTO resources(resource_id,title,source_locator,provenance,source_layer,
            file_type,historical_status) VALUES ('R1','Deck','<HISTORICAL_RESOURCE_REPOSITORY>/LECTURE1/deck.pdf',
            'census','PAST_COURSE_RUN','.pdf','HISTORICAL_READ_ONLY')"""
        )
        resource_pk = self.connection.execute("SELECT id FROM resources WHERE resource_id='R1'").fetchone()[0]
        self.connection.execute(
            "INSERT INTO resource_assignments(resource_id,lecture_pair_id,part) VALUES (?,?,'UNCLASSIFIED')",
            (resource_pk, self.pair_id),
        )
        self.connection.execute(
            """INSERT INTO historical_decks(deck_id,lecture_pair_id,title,source_locator,file_type,
            source_layer,content_sha256) VALUES ('D1',?,'Deck','<HISTORICAL_RESOURCE_REPOSITORY>/LECTURE1/deck.pdf',
            '.pdf','PAST_COURSE_RUN',?)""", (self.pair_id, "a" * 64),
        )
        deck_pk = self.connection.execute("SELECT id FROM historical_decks WHERE deck_id='D1'").fetchone()[0]
        self.connection.commit()
        return resource_pk, deck_pk

    def seed_note_and_slide(self) -> None:
        if self.connection.execute("SELECT 1 FROM resources WHERE resource_id='R1'").fetchone() is None:
            self.seed_resource_and_deck()
        add_note(self.connection, 1, {
            "part": "A", "topic": "Instructor-supplied topic", "claim": "Instructor-supplied claim",
            "explanation": "Explanation", "evidence": "Evidence", "source_ids": "R1",
            "date_relevance": "2026", "confidence": "HIGH", "teaching_function": "CONCEPT",
            "suggested_slide": "1", "created_by": "Instructor", "note_origin": "INSTRUCTOR_AUTHORED",
            "instructor_status": "NOT_REVIEWED",
        })
        add_slide_plan(self.connection, 1, {
            "part": "A", "sequence": "1", "title": "Instructor-supplied slide",
            "purpose": "Explain an instructor-supplied concept", "action": "ADD",
            "historical_slide_sources": "", "note_ids": "IS529N-L01-N001",
            "resource_ids": "R1", "visual_type": "CONCEPT", "visual_asset_path": "",
            "speaker_note": "Instructor speaking cue", "citation_footer": "Instructor source",
            "verification_status": "VERIFIED", "approval_status": "NOT_REVIEWED",
        })

    def test_lecture_pair_creation_and_migration_integrity(self) -> None:
        self.assertEqual(self.connection.execute("SELECT COUNT(*) FROM lecture_pairs").fetchone()[0], 15)
        self.assertEqual(self.connection.execute("SELECT COUNT(*) FROM lecture_parts").fetchone()[0], 30)
        self.assertEqual(self.connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0], 13)
        initialise(self.database_path, self.root / "missing.json").close()
        self.assertEqual(self.connection.execute("SELECT COUNT(*) FROM lecture_pairs").fetchone()[0], 15)

    def test_resource_to_part_assignment(self) -> None:
        resource_pk, _ = self.seed_resource_and_deck()
        assign_resource(self.connection, 1, resource_pk, "BOTH", "MAP", "CENTRAL")
        row = self.connection.execute(
            "SELECT ra.part,r.classification,r.centrality FROM resource_assignments ra JOIN resources r ON r.id=ra.resource_id"
        ).fetchone()
        self.assertEqual(tuple(row), ("BOTH", "MAP", "CENTRAL"))

    def test_historical_slide_status_changes(self) -> None:
        _, deck_pk = self.seed_resource_and_deck()
        slide_id = add_historical_slide(self.connection, deck_pk, {
            "historical_slide_number": "1", "title": "Observed title", "current_status": "VERIFY",
        })
        slide_pk = self.connection.execute(
            "SELECT id FROM historical_slides WHERE historical_slide_id=?", (slide_id,)
        ).fetchone()[0]
        update_historical_slide_status(self.connection, slide_pk, "REVISE")
        self.assertEqual(self.connection.execute("SELECT current_status FROM historical_slides").fetchone()[0], "REVISE")
        record_historical_derivative(
            self.connection, deck_pk, "PREVIEW",
            "reports/gui_acceptance/historical/D1-S001.png", slide_pk,
        )
        derivative = self.connection.execute(
            "SELECT source_locator,source_sha256 FROM historical_derivatives"
        ).fetchone()
        self.assertEqual(derivative["source_sha256"], "a" * 64)
        self.assertTrue(derivative["source_locator"].startswith("<HISTORICAL_RESOURCE_REPOSITORY>"))

    def test_revised_note_provenance(self) -> None:
        self.seed_note_and_slide()
        row = self.connection.execute("SELECT source_ids,note_origin,created_by FROM revised_notes").fetchone()
        self.assertEqual(json.loads(row["source_ids"]), ["R1"])
        self.assertEqual(row["note_origin"], "INSTRUCTOR_AUTHORED")
        self.assertEqual(row["created_by"], "Instructor")
        self.assertEqual(self.connection.execute("SELECT COUNT(*) FROM note_source_links").fetchone()[0], 1)
        self.assertEqual(self.connection.execute("SELECT COUNT(*) FROM slide_source_links").fetchone()[0], 1)

    def test_slide_plan_creation_and_validation(self) -> None:
        self.seed_note_and_slide()
        row = self.connection.execute("SELECT * FROM slide_plan_entries").fetchone()
        self.assertEqual(row["slide_id"], "IS529N-L01-A-S001")
        report = validate_deck_plan(self.connection, self.pair_id, "A")
        self.assertEqual(report["status"], "PASS")

    def test_deck_version_naming(self) -> None:
        directory = self.root / "decks"; directory.mkdir()
        name, version = next_deck_filename(directory, 1, "A", "DRAFT")
        self.assertEqual((name, version), ("IS529N_L01A_v0.1_DRAFT.pptx", "v0.1"))
        (directory / name).touch()
        self.assertEqual(next_deck_filename(directory, 1, "A", "REVISED")[1], "v0.2")

    def test_approved_deck_is_never_overwritten(self) -> None:
        self.seed_note_and_slide()
        slide_pk = self.connection.execute("SELECT id FROM slide_plan_entries").fetchone()[0]
        update_slide_decision(self.connection, slide_pk, "ACCEPT")
        set_part_approval(self.connection, 1, "A")
        self.assertEqual(self.connection.execute("SELECT COUNT(*) FROM approval_decisions").fetchone()[0], 2)
        output = self.root / "decks"
        first = generate_pptx(self.connection, self.root, 1, "A", "APPROVED", output)
        first_hash = hashlib.sha256(first["path"].read_bytes()).hexdigest()
        second = generate_pptx(self.connection, self.root, 1, "A", "APPROVED", output)
        self.assertNotEqual(first["path"], second["path"])
        self.assertEqual(hashlib.sha256(first["path"].read_bytes()).hexdigest(), first_hash)

    def test_draft_ledger_event_is_isolated(self) -> None:
        ledger = self.root / "course_ledger/ledger.jsonl"
        ledger.parent.mkdir(); ledger.write_text("canonical\n", encoding="utf-8")
        before = ledger.read_bytes()
        path = prepare_draft_event(self.connection, self.root, 1, "LECTURE_RETROSPECTIVE")
        self.assertIn("course_ledger/drafts/gui", path.as_posix())
        self.assertEqual(ledger.read_bytes(), before)
        self.assertEqual(json.loads(path.read_text())["approval_status"], "DRAFT")

    def test_repository_relative_path_storage(self) -> None:
        self.assertEqual(validate_relative_path("course/lectures/lecture_01/file.pptx"), "course/lectures/lecture_01/file.pptx")
        absolute_private = str(PurePosixPath("/") / "media" / "private" / "file")
        windows_private = "C:" + chr(92) + "private" + chr(92) + "file"
        for value in (absolute_private, "../private", windows_private):
            with self.assertRaises(ValueError):
                validate_relative_path(value)

    def test_git_readiness_and_public_private_classification(self) -> None:
        lecture_file = self.root / "course/lectures/lecture_01/public.md"
        lecture_file.parent.mkdir(parents=True); lecture_file.write_text("draft\n", encoding="utf-8")
        report = git_readiness(self.root, 1)
        self.assertEqual(report["branch"], "main")
        self.assertFalse(report["automatic_commit_enabled"])
        self.assertEqual(report["selected_lecture_files"][0]["classification"], "PUBLIC_CANDIDATE")
        self.assertEqual(classify_public_path("state.sqlite3", set(), set()), "PRIVATE_LOCAL")
        self.assertEqual(classify_public_path("course/lectures/lecture_01/deck_source/x_DRAFT.pptx", set(), {"course/lectures/**/deck_source/*_DRAFT.pptx"}), "PRIVATE_LOCAL")
        self.assertEqual(classify_public_path("unknown.md", set(), set()), "REVIEW_REQUIRED")

    def test_browser_vertical_slice_routes(self) -> None:
        self.connection.close()
        app = create_app(self.root, self.database_path)
        client = TestClient(app)
        for route in ("/", "/titles", "/lectures/1", "/lectures/1/resources", "/lectures/1/decks",
                      "/lectures/1/notes", "/lectures/1/slide-plan", "/lectures/1/deliverables",
                      "/lectures/1/class-record", "/governance?lecture=1", "/health"):
            response = client.get(route)
            self.assertEqual(response.status_code, 200, route)
        response = client.post("/lectures/1/notes", data={
            "part":"A", "topic":"Pasted text", "claim":"Externally supplied claim",
            "teaching_function":"CONCEPT", "created_by":"External", "note_origin":"EXTERNALLY_PASTED_AI_DRAFT",
        }, follow_redirects=False)
        self.assertEqual(response.status_code, 303)
        self.connection = initialise(self.database_path, self.root / "missing.json")


if __name__ == "__main__":
    unittest.main()
