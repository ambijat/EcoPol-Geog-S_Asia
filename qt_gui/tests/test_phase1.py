from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from gui.services import set_part_approval, update_slide_decision, validate_relative_path
from gui.title_registry import title_precedence, valid_part_ids, valid_weekly_ids
from qt_gui.app import create_application
from qt_gui.config import AppConfig, STYLE_SHEET, WATERMARK
from qt_gui.database.connection import DatabaseManager
from qt_gui.database.repositories.lecture_repository import LectureRepository
from qt_gui.database.repositories.title_repository import TitleRepository
from qt_gui.main_window import MainWindow, NAVIGATION
from qt_gui.services.git_readiness_service import GitReadinessService
from qt_gui.services.historical_deck_service import HistoricalDeckService
from qt_gui.services.ledger_draft_service import LedgerDraftService
from qt_gui.services.lecture_service import LectureService
from qt_gui.services.note_service import NoteService
from qt_gui.services.pptx_service import PptxService
from qt_gui.services.resource_service import ResourceService
from qt_gui.services.slide_plan_service import SlidePlanService
from qt_gui.services.title_registry_service import TitleRegistryService


def registry_text(identifiers: set[str]) -> str:
    return "# synthetic test registry\n" + "\n".join(
        f"{identifier}|Candidate {identifier}" for identifier in sorted(identifiers)
    ) + "\n"


class QtPhaseOneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        (self.root / "course").mkdir()
        (self.root / "reports").mkdir()
        (self.root / "course_ledger").mkdir()
        (self.root / "resource_registry").mkdir()
        (self.root / "course_ledger/ledger.jsonl").write_text(
            json.dumps({"block_number": 1, "content_hash": "a" * 64}) + "\n", encoding="utf-8"
        )
        (self.root / "resource_registry/resources.jsonl").write_text("", encoding="utf-8")
        (self.root / "course/lecture_titles.txt").write_text(
            registry_text(valid_weekly_ids()), encoding="utf-8"
        )
        (self.root / "course/lecture_part_titles.txt").write_text(
            registry_text(valid_part_ids()), encoding="utf-8"
        )
        (self.root / "reports/public_include_manifest.txt").write_text(
            "course/lectures/lecture_01/public.md\n", encoding="utf-8"
        )
        (self.root / "reports/public_exclude_manifest.txt").write_text(
            "course/lectures/**/deck_source/*_DRAFT.pptx\n", encoding="utf-8"
        )
        subprocess.run(["git", "init", "-b", "main"], cwd=self.root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Qt Test"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.email", "qt.invalid@example.invalid"], cwd=self.root, check=True)
        (self.root / "seed.txt").write_text("seed\n", encoding="utf-8")
        subprocess.run(["git", "add", "seed.txt"], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-m", "seed"], cwd=self.root, check=True, capture_output=True)
        self.database_path = self.root / "local_state/cockpit.sqlite3"
        self.database = DatabaseManager(self.database_path, self.root)
        self.database.initialise()
        self.lecture_service = LectureService(LectureRepository(self.database))

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def config(self) -> AppConfig:
        return AppConfig(self.root, self.database_path, WATERMARK, STYLE_SHEET)

    def seed_resource_and_deck(self) -> tuple[int, int]:
        with self.database.connection() as connection:
            pair_id = connection.execute("SELECT id FROM lecture_pairs WHERE lecture_number=1").fetchone()[0]
            connection.execute(
                """INSERT INTO resources(resource_id,title,source_locator,provenance,source_layer,
                file_type,historical_status,content_sha256) VALUES
                ('QT-R1','Synthetic','<SYNTHETIC_FIXTURE>/source','test','SYNTHETIC','.txt','SYNTHETIC',?)""",
                ("a" * 64,),
            )
            resource = connection.execute("SELECT id FROM resources WHERE resource_id='QT-R1'").fetchone()[0]
            connection.execute(
                "INSERT INTO resource_assignments(resource_id,lecture_pair_id,part) VALUES (?,?,'UNCLASSIFIED')",
                (resource, pair_id),
            )
            connection.execute(
                """INSERT INTO historical_decks(deck_id,lecture_pair_id,title,source_locator,file_type,
                source_layer,content_sha256) VALUES ('QT-D1',?,'Synthetic deck',
                '<HISTORICAL_RESOURCE_REPOSITORY>/LECTURE1/deck.pdf','.pdf','PAST_COURSE_RUN',?)""",
                (pair_id, "b" * 64),
            )
            deck = connection.execute("SELECT id FROM historical_decks WHERE deck_id='QT-D1'").fetchone()[0]
            connection.commit()
            return resource, deck

    def seed_note_and_slides(self) -> None:
        self.seed_resource_and_deck()
        notes = NoteService(self.database)
        notes.create(1, {
            "part":"A", "topic":"Synthetic", "claim":"Synthetic structural claim",
            "explanation":"Test", "evidence":"Fixture", "source_ids":"QT-R1",
            "date_relevance":"NOT_APPLICABLE", "confidence":"SYNTHETIC",
            "teaching_function":"CONCEPT", "suggested_slide":"1", "created_by":"QT_TEST",
            "note_origin":"INSTRUCTOR_AUTHORED", "instructor_status":"NOT_REVIEWED",
        })
        slides = SlidePlanService(self.database)
        for sequence in (1, 2):
            slides.create(1, {
                "part":"A", "sequence":str(sequence), "title":f"Synthetic slide {sequence}",
                "purpose":"Structural Qt test", "action":"ADD", "historical_slide_sources":"",
                "note_ids":"IS529N-L01-N001", "resource_ids":"QT-R1", "visual_type":"CONCEPT",
                "visual_asset_path":"", "speaker_note":"Test", "citation_footer":"QT-R1",
                "verification_status":"VERIFIED", "approval_status":"NOT_REVIEWED",
            })

    def test_application_startup_and_window_navigation(self) -> None:
        window = MainWindow(self.config())
        window.show(); self.application.processEvents()
        self.assertIn("Economic and Political Geography", window.windowTitle())
        self.assertEqual(window.navigation.count(), 12)
        window.navigate("Lecture Titles")
        self.assertEqual(window.stack.currentIndex(), 1)
        window.navigate("Governance and Git Readiness")
        self.assertEqual(window.stack.currentIndex(), 10)
        window.close()

    def test_create_application_factory(self) -> None:
        app, window = create_application(self.config(), [])
        self.assertIs(app, self.application)
        self.assertIsInstance(window, MainWindow)
        window.close()

    def test_migration_integrity(self) -> None:
        with self.database.connection() as connection:
            self.assertEqual(connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0], 13)
            self.assertEqual(connection.execute("PRAGMA foreign_keys").fetchone()[0], 1)

    def test_dashboard_has_fifteen_lecture_cards(self) -> None:
        window = MainWindow(self.config())
        self.assertEqual(window.dashboard_view.lecture_card_count, 15)
        window.close()

    def test_lecture_pair_loading(self) -> None:
        pair = self.lecture_service.load_pair(1)
        self.assertEqual(pair["pair"]["lecture_id"], "IS529N-L01")
        self.assertEqual([part["part"] for part in pair["parts"]], ["A", "B"])

    def test_title_registry_and_precedence(self) -> None:
        service = TitleRegistryService(TitleRepository(self.database))
        weekly, parts = service.validate()
        self.assertEqual((len(weekly), len(parts)), (15, 30))
        self.assertGreater(title_precedence("MANUAL_GUI", "INSTRUCTOR_CONFIRMED"), title_precedence("TITLE_REGISTRY", "HISTORICALLY_EXTRACTED"))

    def test_basic_title_widget_interaction(self) -> None:
        window = MainWindow(self.config())
        view = window.title_manager_view
        view.table.selectRow(0)
        view.table.item(0, 1).setText("Qt working title")
        QTest.mouseClick(view.save_button, Qt.MouseButton.LeftButton)
        with self.database.connection() as connection:
            row = connection.execute("SELECT weekly_title,title_status FROM lecture_pairs WHERE lecture_number=1").fetchone()
            self.assertEqual(tuple(row), ("Qt working title", "WORKING_DRAFT"))
        window.close()

    def test_resource_assignment(self) -> None:
        resource, _ = self.seed_resource_and_deck()
        service = ResourceService(self.database)
        service.assign(1, resource, "A", "MAP", "CENTRAL")
        self.assertEqual(service.list_for_lecture(1)[0]["assignment"], "A")

    def test_historical_derivative_provenance(self) -> None:
        _, deck = self.seed_resource_and_deck()
        service = HistoricalDeckService(self.database)
        service.register_derivative(deck, "PREVIEW", "reports/qt_gui_acceptance/deck.png")
        with self.database.connection() as connection:
            row = connection.execute("SELECT source_locator,source_sha256 FROM historical_derivatives").fetchone()
            self.assertTrue(row["source_locator"].startswith("<HISTORICAL_RESOURCE_REPOSITORY>"))
            self.assertEqual(row["source_sha256"], "b" * 64)

    def test_note_creation(self) -> None:
        self.seed_resource_and_deck()
        service = NoteService(self.database)
        note_id = service.create(1, {
            "part":"A", "topic":"Synthetic", "claim":"Claim", "source_ids":"QT-R1",
            "teaching_function":"CONCEPT", "created_by":"QT_TEST", "note_origin":"INSTRUCTOR_AUTHORED",
        })
        self.assertEqual(note_id, "IS529N-L01-N001")
        self.assertEqual(len(service.list_for_lecture(1)), 1)

    def test_slide_plan_ordering(self) -> None:
        self.seed_note_and_slides()
        service = SlidePlanService(self.database)
        rows = service.list_for_part(1, "A")
        service.move(rows[1]["id"], -1)
        reordered = service.list_for_part(1, "A")
        self.assertEqual(reordered[0]["title"], "Synthetic slide 2")

    def test_deliverable_versioning_and_approved_overwrite_protection(self) -> None:
        self.seed_note_and_slides()
        service = PptxService(self.database)
        name, version = service.next_filename(self.root / "decks", 1, "A", "DRAFT")
        self.assertEqual((name, version), ("IS529N_L01A_v0.1_DRAFT.pptx", "v0.1"))
        with self.database.connection() as connection:
            for row in connection.execute("SELECT id FROM slide_plan_entries"):
                update_slide_decision(connection, row[0], "ACCEPT")
            set_part_approval(connection, 1, "A")
        first = service.generate(1, "A", "APPROVED")
        first_hash = hashlib.sha256(first["path"].read_bytes()).hexdigest()
        second = service.generate(1, "A", "APPROVED")
        self.assertNotEqual(first["path"], second["path"])
        self.assertEqual(hashlib.sha256(first["path"].read_bytes()).hexdigest(), first_hash)

    def test_draft_ledger_isolation(self) -> None:
        canonical = self.root / "course_ledger/ledger.jsonl"
        canonical.write_text("canonical\n", encoding="utf-8")
        before = canonical.read_bytes()
        with self.database.connection() as connection:
            pair = connection.execute("SELECT id FROM lecture_pairs WHERE lecture_number=1").fetchone()[0]
            connection.execute(
                """INSERT INTO class_session_records(session_id,lecture_pair_id,part,actual_date,
                instructor_validation_status) VALUES ('IS529N-L01-A-SESSION',?,'A','2026-01-01','INSTRUCTOR_VALIDATED')""",
                (pair,),
            )
            connection.commit()
        path = LedgerDraftService(self.database).prepare(1, "LECTURE_RETROSPECTIVE")
        self.assertIn("course_ledger/drafts/qt", path.as_posix())
        self.assertEqual(canonical.read_bytes(), before)

    def test_repository_relative_path_enforcement(self) -> None:
        self.assertEqual(validate_relative_path("reports/qt_gui_acceptance/item.png"), "reports/qt_gui_acceptance/item.png")
        with self.assertRaises(ValueError):
            validate_relative_path(str(self.root / "private.png"))

    def test_git_readiness_and_public_private_classification(self) -> None:
        lecture_file = self.root / "course/lectures/lecture_01/public.md"
        lecture_file.parent.mkdir(parents=True); lecture_file.write_text("draft\n", encoding="utf-8")
        report = GitReadinessService(self.database).governance_status(1)
        self.assertFalse(report["git_writes_enabled"])
        self.assertFalse(report["canonical_ledger_writes_enabled"])
        self.assertEqual(report["selected_lecture_files"][0]["classification"], "PUBLIC_CANDIDATE")


if __name__ == "__main__":
    unittest.main()
