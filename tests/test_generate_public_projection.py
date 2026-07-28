from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path, PurePosixPath


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from generate_public_projection import ProjectionError, generate_projection


class PublicProjectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        (self.root / "course_ledger").mkdir(parents=True)
        (self.root / "config").mkdir()
        self.preamble = self.root / "SEMESTER2026_Course_Governance_Preamble.md"
        self.ledger = self.root / "course_ledger" / "ledger.jsonl"
        self.retrospective = (
            self.root / "course_ledger" / "retrospective_events_2026-07-20.json"
        )
        self.config = self.root / "config" / "paths.json"
        self.active_source = str(PurePosixPath("/") / "media" / "example" / "project")
        self.history_source = str(PurePosixPath("/") / "mnt" / "example" / "history")
        self.config.write_text(
            json.dumps(
                {
                    "redactions": [
                        {
                            "category": "ACTIVE_PROJECT_ROOT",
                            "source": self.active_source,
                            "replacement": "<ACTIVE_PROJECT_ROOT>",
                        },
                        {
                            "category": "HISTORICAL_RESOURCE_REPOSITORY",
                            "source": self.history_source,
                            "replacement": "<HISTORICAL_RESOURCE_REPOSITORY>",
                        },
                    ]
                }
            ),
            encoding="utf-8",
        )
        self.write_sources()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_sources(self, *, summary: str = "Safe academic chronology.") -> None:
        self.preamble.write_text(
            f"# Governance\n\nProject: {self.active_source}\n"
            f"History: {self.history_source}\n",
            encoding="utf-8",
        )
        block = {
            "block_number": 1,
            "previous_block_hash": "0" * 64,
            "content_hash": "1" * 64,
            "block_type": "COURSE_CHARTER",
            "title": "Test charter",
            "date": "2026-07-21",
            "approval_status": "APPROVED",
            "approved_by": "Instructor",
            "fidelity_status": "F4 — Instructor-approved",
            "summary": summary,
            "source_material": [f"{self.history_source}/source.pdf"],
        }
        self.ledger.write_text(json.dumps(block) + "\n", encoding="utf-8")
        event = dict(block)
        event.pop("block_number")
        event.pop("previous_block_hash")
        event.pop("content_hash")
        self.retrospective.write_text(
            json.dumps([event]) + "\n", encoding="utf-8"
        )

    def generate(self, *, dry_run: bool = False):
        return generate_projection(
            self.root,
            self.config,
            dry_run=dry_run,
            generated_at="2026-07-21T00:00:00+00:00",
        )

    def test_absolute_paths_are_redacted_and_labels_are_noncanonical(self) -> None:
        result = self.generate()
        preamble = (
            self.root
            / "public/governance/SEMESTER2026_Course_Governance_Preamble_PUBLIC.md"
        ).read_text(encoding="utf-8")
        block = json.loads(
            (self.root / "public/ledger/ledger_public.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()[0]
        )
        self.assertNotIn(self.active_source, preamble)
        self.assertNotIn(self.history_source, preamble)
        self.assertIn("<ACTIVE_PROJECT_ROOT>", preamble)
        self.assertEqual(block["projection_type"], "PUBLIC_REDACTED_PROJECTION")
        self.assertEqual(block["canonical_authority"], "LOCAL_PRIVATE_LEDGER")
        self.assertEqual(block["cryptographic_status"], "NON_CANONICAL")
        self.assertEqual(block["canonical_content_hash"], "1" * 64)
        self.assertGreater(result["outputs"][1]["redaction_count"], 0)

    def test_local_git_commit_identifier_is_redacted(self) -> None:
        self.write_sources(summary="Local commit " + "a" * 40)
        self.generate()
        projection = (self.root / "public/ledger/ledger_public.jsonl").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("a" * 40, projection)
        self.assertIn("<LOCAL_GIT_COMMIT>", projection)

    def test_unresolved_absolute_path_is_rejected(self) -> None:
        unknown = str(PurePosixPath("/") / "home" / "unmapped" / "private.txt")
        self.preamble.write_text(f"Unknown: {unknown}\n", encoding="utf-8")
        with self.assertRaisesRegex(ProjectionError, "unresolved absolute path"):
            self.generate()

    def test_dry_run_does_not_write_outputs(self) -> None:
        result = self.generate(dry_run=True)
        self.assertTrue(result["dry_run"])
        self.assertFalse((self.root / "public").exists())

    def test_canonical_files_are_preserved(self) -> None:
        paths = (self.preamble, self.ledger, self.retrospective)
        before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
        self.generate()
        after = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
        self.assertEqual(after, before)

    def test_public_projection_manifest_is_complete_and_symbolic(self) -> None:
        self.generate()
        manifest = json.loads(
            (self.root / "public/reports/public_projection_manifest.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(manifest["validation_status"], "PASSED")
        self.assertEqual(len(manifest["records"]), 3)
        for record in manifest["records"]:
            self.assertTrue(record["canonical_source"].startswith("<ACTIVE_PROJECT_ROOT>/"))
            self.assertEqual(record["checksum_label"], "PUBLIC_PROJECTION_FILE_SHA256")
            self.assertNotIn(str(self.root), json.dumps(record))

    def test_secret_pattern_is_rejected(self) -> None:
        self.write_sources(summary="api_key: ABCDEFGHIJKL")
        with self.assertRaisesRegex(ProjectionError, "credential or secret"):
            self.generate()

    def test_student_identifier_is_rejected(self) -> None:
        self.write_sources(summary="student_id: 12345")
        with self.assertRaisesRegex(ProjectionError, "student identifier"):
            self.generate()

    def test_email_address_is_rejected_and_safe_outputs_have_none(self) -> None:
        self.generate()
        for path in (self.root / "public").rglob("*"):
            if path.is_file():
                self.assertNotIn("@", path.read_text(encoding="utf-8"))
        self.write_sources(summary="Contact learner@example.edu")
        with self.assertRaisesRegex(ProjectionError, "email address"):
            self.generate()


if __name__ == "__main__":
    unittest.main()
