from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from gui.app import create_app
from gui.database import initialise, seed_title_evidence
from gui.title_registry import (
    PENDING_TITLE, TitleRegistryError, apply_title_sync, edit_title,
    export_confirmed_titles, parse_title_text, propose_title_sync,
    title_precedence, valid_part_ids, valid_weekly_ids,
)
from scripts.extract_historical_lecture_titles import source_classification


def registry_text(identifiers: set[str], prefix: str = "Candidate") -> str:
    return "# test registry\n" + "\n".join(
        f"{identifier}|{prefix} {identifier}" for identifier in sorted(identifiers)
    ) + "\n"


class TitleRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        (self.root / "course").mkdir()
        (self.root / "reports").mkdir()
        (self.root / "course/lecture_titles.txt").write_text(
            registry_text(valid_weekly_ids()), encoding="utf-8"
        )
        (self.root / "course/lecture_part_titles.txt").write_text(
            registry_text(valid_part_ids()), encoding="utf-8"
        )
        self.database = self.root / "state/cockpit.sqlite3"
        self.connection = initialise(self.database, self.root / "reports/missing-census.json")

    def tearDown(self) -> None:
        self.connection.close()
        self.temporary.cleanup()

    def test_parses_complete_valid_title_files(self) -> None:
        records = parse_title_text(registry_text(valid_weekly_ids()), valid_weekly_ids(), "weekly")
        self.assertEqual(len(records), 15)

    def test_rejects_duplicate_identifier(self) -> None:
        text = registry_text(valid_weekly_ids()) + "L01|Duplicate\n"
        with self.assertRaisesRegex(TitleRegistryError, "duplicate identifier L01"):
            parse_title_text(text, valid_weekly_ids(), "weekly")

    def test_rejects_malformed_and_blank_records(self) -> None:
        malformed = registry_text(valid_weekly_ids()).replace("L01|Candidate L01", "L01 Candidate")
        with self.assertRaisesRegex(TitleRegistryError, "vertical-bar"):
            parse_title_text(malformed, valid_weekly_ids(), "weekly")
        blank = registry_text(valid_weekly_ids()).replace("L01|Candidate L01", "L01|")
        with self.assertRaisesRegex(TitleRegistryError, "blank title"):
            parse_title_text(blank, valid_weekly_ids(), "weekly")

    def test_title_precedence(self) -> None:
        levels = [
            title_precedence("PENDING", "PENDING"),
            title_precedence("HISTORICAL", "FILENAME_INFERRED"),
            title_precedence("HISTORICAL", "HISTORICALLY_EXTRACTED"),
            title_precedence("TITLE_REGISTRY", "HISTORICALLY_EXTRACTED"),
            title_precedence("MANUAL_GUI", "WORKING_DRAFT"),
            title_precedence("MANUAL_GUI", "INSTRUCTOR_CONFIRMED"),
        ]
        self.assertEqual(levels, sorted(levels))

    def test_instructor_confirmed_title_is_protected_from_reload(self) -> None:
        edit_title(self.connection, "LECTURE_PAIR", "L01", "Confirmed title", True)
        batch = propose_title_sync(self.connection, self.root)
        changed = apply_title_sync(self.connection, batch)
        row = self.connection.execute(
            "SELECT weekly_title,title_status FROM lecture_pairs WHERE lecture_number=1"
        ).fetchone()
        self.assertEqual(tuple(row), ("Confirmed title", "INSTRUCTOR_CONFIRMED"))
        self.assertGreater(self.connection.execute(
            "SELECT COUNT(*) FROM title_registry_conflicts WHERE batch_id=?", (batch,)
        ).fetchone()[0], 0)
        self.assertEqual(changed, 44)

    def test_atomic_export_creates_backups(self) -> None:
        edit_title(self.connection, "LECTURE_PAIR", "L01", "Instructor title", True)
        previous = (self.root / "course/lecture_titles.txt").read_bytes()
        backups = export_confirmed_titles(self.connection, self.root)
        self.assertEqual(backups[0].read_bytes(), previous)
        self.assertIn("L01|Instructor title", (self.root / "course/lecture_titles.txt").read_text())

    def test_part_c_is_supplementary(self) -> None:
        self.assertEqual(
            source_classification("Lecture 8 PART C Service sector", "LECTURE8/lecture8c.odp"),
            "SUPPLEMENTARY_PART_C",
        )

    def test_historical_title_provenance_uses_symbolic_locator(self) -> None:
        report = self.root / "reports/evidence.json"
        report.write_text(json.dumps({"records": [{
            "associated_lecture_id": "IS529N-L01", "target_identifier": "L01A",
            "historical_classification": "PART_A", "source_filename": "lecture1a.odp",
            "source_locator": "<HISTORICAL_RESOURCE_REPOSITORY>/LECTURE1/lecture1a.odp",
            "source_sha256": "a" * 64, "extracted_title": "South Asia as a Region",
            "extraction_method": "TITLE_EXTRACTED_FROM_SLIDE", "extraction_confidence": "HIGH",
            "instructor_confirmation_required": True,
        }]}), encoding="utf-8")
        self.assertEqual(seed_title_evidence(self.connection, report), 1)
        locator = self.connection.execute("SELECT source_locator FROM title_evidence").fetchone()[0]
        self.assertTrue(locator.startswith("<HISTORICAL_RESOURCE_REPOSITORY>/"))

    def test_gui_reload_preview_and_confirmation(self) -> None:
        self.connection.close()
        app = create_app(self.root, self.database)
        client = TestClient(app)
        response = client.post("/titles/reload", follow_redirects=False)
        self.assertEqual(response.status_code, 303)
        self.assertIn("batch=", response.headers["location"])
        batch = int(response.headers["location"].split("batch=")[1])
        preview = client.get(response.headers["location"])
        self.assertIn("Confirm non-conflicting changes", preview.text)
        applied = client.post(f"/titles/reload/{batch}/confirm", follow_redirects=False)
        self.assertEqual(applied.status_code, 303)
        confirmed = client.post(
            "/titles/LECTURE_PAIR/L01",
            data={"title": "GUI confirmed title", "confirmed": "1"}, follow_redirects=False,
        )
        self.assertEqual(confirmed.status_code, 303)
        self.connection = initialise(self.database, self.root / "reports/missing-census.json")
        row = self.connection.execute(
            "SELECT weekly_title,title_status FROM lecture_pairs WHERE lecture_number=1"
        ).fetchone()
        self.assertEqual(tuple(row), ("GUI confirmed title", "INSTRUCTOR_CONFIRMED"))

    def test_invalid_reload_does_not_change_database(self) -> None:
        before = self.connection.execute(
            "SELECT weekly_title FROM lecture_pairs WHERE lecture_number=1"
        ).fetchone()[0]
        (self.root / "course/lecture_titles.txt").write_text("L01 malformed\n", encoding="utf-8")
        with self.assertRaises(TitleRegistryError):
            propose_title_sync(self.connection, self.root)
        after = self.connection.execute(
            "SELECT weekly_title FROM lecture_pairs WHERE lecture_number=1"
        ).fetchone()[0]
        self.assertEqual(after, before)
        self.assertEqual(self.connection.execute("SELECT COUNT(*) FROM title_sync_batches").fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()
