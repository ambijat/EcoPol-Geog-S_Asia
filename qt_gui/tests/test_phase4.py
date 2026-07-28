from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from qt_gui.config import AppConfig, STYLE_SHEET, WATERMARK
from qt_gui.database.connection import DatabaseManager
from qt_gui.main_window import MainWindow
from qt_gui.services.triangulation_service import TriangulationService


class QtPhaseFourTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        for folder in ("reports", "course_ledger", "resource_registry", "historical"):
            (self.root / folder).mkdir(parents=True, exist_ok=True)
        (self.root / "course_ledger/ledger.jsonl").write_text(
            json.dumps({"block_number": 1, "content_hash": "a" * 64}) + "\n", encoding="utf-8"
        )
        (self.root / "resource_registry/resources.jsonl").write_text("", encoding="utf-8")
        (self.root / "reports/public_include_manifest.txt").write_text("qt_gui/services/triangulation_service.py\n")
        (self.root / "reports/public_exclude_manifest.txt").write_text("qt_gui/local_state/**\n")
        subprocess.run(["git", "init", "-b", "main"], cwd=self.root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Phase 4 Test"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.email", "phase4.invalid@example.invalid"], cwd=self.root, check=True)
        (self.root / "seed.txt").write_text("seed\n", encoding="utf-8")
        subprocess.run(["git", "add", "seed.txt"], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-m", "seed"], cwd=self.root, check=True, capture_output=True)
        self.database = DatabaseManager(self.root / "local_state/cockpit.sqlite3", self.root)
        self.database.initialise()
        self.service = TriangulationService(self.database)
        self.topic = self.service.create_topic({
            "triangulation_topic_id": "SYNTHETIC-TRI-001",
            "lecture_id": "IS529N-L01",
            "part": "A",
            "topic": "Synthetic triangulation topic",
            "central_question": "How do the layers align?",
            "historical_slide_ids": ["SYN-H1"],
            "working_note_ids": ["SYN-N1"],
            "slide_plan_ids": ["SYN-S1"],
        })

    def tearDown(self):
        self.temporary.cleanup()

    def evidence(self, evidence_id: str, layer: str, **overrides) -> int:
        values = {
            "evidence_id": evidence_id,
            "evidence_layer": layer,
            "source_identifier": evidence_id + "-SOURCE",
            "source_title": "Synthetic public-safe evidence",
            "source_type": "SYNTHETIC",
            "symbolic_location": "<SYNTHETIC_FIXTURE>/evidence",
            "treatment_level": 2,
            "alignment_level": "HIGH_ALIGNMENT",
            "evidentiary_value": "MEDIUM",
            "verification_status": "VERIFIED",
            "currency_status": "CURRENT",
        }
        values.update(overrides)
        return self.service.add_evidence(self.topic, values)

    def test_creation_of_triangulation_topics(self):
        detail = self.service.topic_detail(self.topic)
        self.assertEqual(detail["topic"]["topic"], "Synthetic triangulation topic")
        self.assertEqual(json.loads(detail["topic"]["historical_slide_ids"]), ["SYN-H1"])

    def test_evidence_layer_validation(self):
        with self.assertRaises(ValueError):
            self.evidence("BAD-LAYER", "UNCONTROLLED_LAYER")

    def test_treatment_level_validation(self):
        with self.assertRaises(ValueError):
            self.evidence("BAD-TREATMENT", "RAW_RESOURCE_LAYER", treatment_level=5)

    def test_alignment_classification(self):
        with self.assertRaises(ValueError):
            self.evidence("BAD-ALIGNMENT", "RAW_RESOURCE_LAYER", alignment_level="MAYBE")
        self.evidence("GOOD-ALIGNMENT", "RAW_RESOURCE_LAYER", alignment_level="MODERATE_ALIGNMENT")

    def test_website_note_status(self):
        self.service.add_website_note({
            "website_note_id": "SYN-WEB-001", "page_title": "Synthetic note",
            "page_url": "https://example.invalid/synthetic", "lecture_id": "IS529N-L01",
            "part": "A", "topic": "Synthetic", "ai_generation_status": "UNKNOWN_ORIGIN",
        })
        with self.assertRaises(ValueError):
            self.service.add_website_note({
                "website_note_id": "SYN-WEB-BAD", "page_title": "Bad", "lecture_id": "IS529N-L01",
                "part": "A", "ai_generation_status": "PRESUMED_AI",
            })

    def test_three_way_convergence(self):
        findings = self.service.classify_findings(historical=True, raw=True, website=True)
        self.assertIn("TRIANGULATED_CORE", findings)

    def test_ppt_resource_convergence_with_website_gap(self):
        findings = self.service.classify_findings(historical=True, raw=True, website=False)
        self.assertIn("CREATE_OR_EXPAND_STUDENT_NOTE", findings)

    def test_website_resource_convergence_with_ppt_gap(self):
        findings = self.service.classify_findings(historical=False, raw=True, website=True)
        self.assertIn("CANDIDATE_FOR_NEW_SLIDE", findings)

    def test_unsupported_inherited_claim(self):
        findings = self.service.classify_findings(historical=True, raw=False, website=False)
        self.assertIn("SOURCE_VERIFICATION_REQUIRED", findings)

    def test_unused_relevant_source(self):
        findings = self.service.classify_findings(
            historical=False, raw=True, website=False, raw_aligned=True, raw_used=False
        )
        self.assertIn("UNUSED_RELEVANT_RESOURCE", findings)

    def test_unverified_website_note(self):
        findings = self.service.classify_findings(
            historical=False, raw=False, website=True, website_verified=False
        )
        self.assertIn("UNVERIFIED_WEBSITE_NOTE", findings)

    def test_out_of_domain_classification(self):
        findings = self.service.classify_findings(
            historical=True, raw=True, website=True, out_of_domain=True
        )
        self.assertEqual(findings, ["OUT_OF_DOMAIN", "ARCHIVE_ONLY"])

    def test_new_source_required_classification(self):
        findings = self.service.classify_findings(
            historical=True, raw=False, website=False, current_source_required=True
        )
        self.assertIn("NEW_SOURCE_REQUIRED", findings)

    def test_source_coverage_reconstruction(self):
        result = self.service.reconstruct_source_coverage({
            "reconstruction_id": "SYN-RECON-001", "historical_slide_id": "SYN-H1",
            "candidate_source_id": "SYN-R1", "lexical_overlap": 0.7, "concept_overlap": 0.8,
            "data_overlap": 0.7, "visual_overlap": 0.1, "citation_match": False, "use_level": 2,
        })
        self.assertEqual(result["probable_lineage"], "PROBABLE")
        self.assertEqual(result["analytical_label"], "RETROSPECTIVE_SOURCE_RECONSTRUCTION")
        self.assertFalse(result["instructor_confirmation"])

    def test_refusal_to_infer_lineage_from_lexical_overlap_alone(self):
        result = self.service.reconstruct_source_coverage({
            "reconstruction_id": "SYN-RECON-LEXICAL", "historical_slide_id": "SYN-H1",
            "candidate_source_id": "SYN-R2", "lexical_overlap": 0.99,
            "concept_overlap": 0.1, "data_overlap": 0, "visual_overlap": 0,
            "citation_match": False, "use_level": 1,
        })
        self.assertEqual(result["probable_lineage"], "UNCONFIRMED")

    def test_candidate_registry_preparation(self):
        candidate = self.service.prepare_registry_candidate(self.topic, {
            "candidate_id": "SYN-CAND-001", "evidence_layer": "RAW_RESOURCE_LAYER",
            "source_identifier": "SYN-R1", "title": "Synthetic candidate",
            "symbolic_location": "<SYNTHETIC_FIXTURE>/raw.pdf",
        })
        self.assertGreater(candidate, 0)
        self.assertEqual(self.service.topic_detail(self.topic)["candidates"][0]["instructor_decision"], "NOT_YET_DECIDED")

    def test_no_automatic_canonical_registration(self):
        canonical = self.root / "resource_registry/resources.jsonl"
        before = canonical.read_bytes()
        self.service.prepare_registry_candidate(self.topic, {
            "candidate_id": "SYN-CAND-002", "evidence_layer": "HISTORICAL_PPT_LAYER",
            "source_identifier": "SYN-H1", "title": "Synthetic historical candidate",
        })
        self.assertEqual(canonical.read_bytes(), before)
        self.assertFalse(self.service.topic_detail(self.topic)["candidates"][0]["canonical_registration_performed"])

    def test_title_decision_suppression(self):
        self.assertFalse(self.service.title_decision_required({
            "extracted_title": "High-fidelity inherited title", "confidence": "HIGH",
            "sequence_mismatch_warning": "", "title_conflict": False,
        }))
        self.assertTrue(self.service.title_decision_required({
            "extracted_title": "", "confidence": "HIGH", "sequence_mismatch_warning": "",
        }))

    def test_fixed_part_mapping(self):
        with self.database.connection() as connection:
            rows = {row["part"]: dict(row) for row in connection.execute(
                "SELECT part,scheduled_day,scheduled_time FROM lecture_parts WHERE lecture_pair_id=(SELECT id FROM lecture_pairs WHERE lecture_number=1)"
            )}
        self.assertEqual((rows["A"]["scheduled_day"], rows["A"]["scheduled_time"]), ("TUESDAY", "09:00-11:00"))
        self.assertEqual((rows["B"]["scheduled_day"], rows["B"]["scheduled_time"]), ("FRIDAY", "09:00-11:00"))

    def test_decision_queue_prioritisation(self):
        self.evidence("HIST", "HISTORICAL_PPT_LAYER")
        self.service.recalculate_findings(self.topic)
        queue = self.service.decision_queue(1)
        self.assertTrue(queue)
        self.assertEqual(queue[0]["finding_type"], "SOURCE_VERIFICATION_REQUIRED")
        self.assertNotIn("TITLE", {item["finding_type"] for item in queue})

    def test_student_learning_package_creation(self):
        package = self.service.create_learning_package({
            "learning_package_id": "SYN-SLP-001", "lecture_id": "IS529N-L01", "part": "A",
            "raw_resource_ids": ["SYN-R1"], "website_note_ids": ["SYN-W1"],
        })
        with self.database.connection() as connection:
            row = connection.execute("SELECT * FROM student_learning_packages WHERE id=?", (package,)).fetchone()
        self.assertEqual(row["public_approval_status"], "NOT_APPROVED")
        with self.assertRaises(ValueError):
            self.service.create_learning_package({
                "learning_package_id": "SYN-SLP-BAD", "lecture_id": "IS529N-L01", "part": "A",
                "public_approval_status": "APPROVED",
            })

    def test_qt_workspace_navigation(self):
        config = AppConfig(self.root, self.database.database_path, WATERMARK, STYLE_SHEET,
                           self.root / "historical", self.root / "qt_gui/local_state/historical_derivatives")
        window = MainWindow(config)
        window.show()
        self.app.processEvents()
        window.open_workspace("Lecture Triangulation", 1)
        self.assertEqual(window.navigation.currentItem().text(), "Lecture Triangulation")
        self.assertEqual(window.triangulation_view.topic_list.count(), 1)
        window.close()

    def test_symbolic_path_enforcement(self):
        with self.assertRaises(ValueError):
            self.evidence("ABSOLUTE", "RAW_RESOURCE_LAYER", symbolic_location="/private/raw.pdf")

    def test_transaction_rollback(self):
        with self.assertRaises(RuntimeError):
            with self.database.connection() as connection:
                connection.execute("UPDATE triangulation_topics SET topic='ROLLBACK' WHERE id=?", (self.topic,))
                raise RuntimeError("cancel")
        self.assertNotEqual(self.service.topic_detail(self.topic)["topic"]["topic"], "ROLLBACK")

    def test_preservation_of_historical_sources(self):
        source = self.root / "historical/source.odp"
        source.write_bytes(b"synthetic immutable historical bytes")
        before = hashlib.sha256(source.read_bytes()).hexdigest()
        self.evidence("HIST-PRESERVE", "HISTORICAL_PPT_LAYER",
                      symbolic_location="<HISTORICAL_RESOURCE_REPOSITORY>/source.odp")
        after = hashlib.sha256(source.read_bytes()).hexdigest()
        self.assertEqual(after, before)


if __name__ == "__main__":
    unittest.main()
