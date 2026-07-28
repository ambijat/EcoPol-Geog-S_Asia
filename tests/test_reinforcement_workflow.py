from __future__ import annotations

import hashlib
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from gui.app import create_app
from gui.database import initialise
from gui.lean_revision_service import LeanRevisionService
from gui.reinforcement_service import (
    RESOURCE_IDENTIFIER_RE, ReinforcementError, ReinforcementService,
)


class ReinforcementFixture:
    def __init__(self, root: Path, connection: sqlite3.Connection):
        self.root = root
        self.connection = connection
        self.pair_id = connection.execute(
            "SELECT id FROM lecture_pairs WHERE lecture_id='IS529N-L01'"
        ).fetchone()[0]

    def seed(self) -> None:
        self.connection.execute(
            """INSERT INTO resources(resource_id,title,source_locator,provenance,source_layer,
            file_type,historical_status,source_type,source_quality,factual_currency_status,
            verification_status) VALUES ('L01-CENSUS-005','lecture1a.odp',
            '<HISTORICAL_RESOURCE_REPOSITORY>/LECTURE1/lecture1a.odp','synthetic','PAST_COURSE_RUN',
            '.odp','HISTORICAL_READ_ONLY','HISTORICAL_FILE','UNASSESSED','HISTORICAL_ONLY','NOT_STARTED')"""
        )
        self.connection.execute(
            """INSERT INTO historical_decks(deck_id,lecture_pair_id,title,source_locator,file_type,
            source_layer,content_sha256) VALUES ('L01-DECK-005',?,'lecture1a.odp',
            '<HISTORICAL_RESOURCE_REPOSITORY>/LECTURE1/lecture1a.odp','.odp','PAST_COURSE_RUN',?)""",
            (self.pair_id, "a" * 64),
        )
        deck_pk = self.connection.execute(
            "SELECT id FROM historical_decks WHERE deck_id='L01-DECK-005'"
        ).fetchone()[0]
        for number in range(3, 19):
            self.connection.execute(
                """INSERT INTO historical_slides(historical_slide_id,deck_id,historical_slide_number,
                title,text_extract,current_status,image_count,table_count)
                VALUES (?,?,?,?,?,'VERIFY',?,0)""",
                (f"L01-DECK-005-S{number:03d}", deck_pk, number,
                 f"Synthetic historical slide {number}",
                 f"Synthetic extracted teaching content for historical slide {number}.",
                 int(number % 2 == 0)),
            )
        self.connection.execute(
            """INSERT INTO historical_resource_clusters(cluster_id,title,symbolic_location,
            resource_count,type_summary,inspection_status,inspected_at) VALUES ('SA-REGION-CLUSTER-001',
            'Synthetic LEC_RES_1','<HISTORICAL_RESOURCE_REPOSITORY>/synthetic',2,'2 PDF','INDEXED',
            '2026-07-22T00:00:00+00:00')"""
        )
        resource_cluster_pk = self.connection.execute(
            "SELECT id FROM historical_resource_clusters WHERE cluster_id='SA-REGION-CLUSTER-001'"
        ).fetchone()[0]
        for suffix, use, alignment in (("0449", "EXTENSIVELY_USED", "HIGH"),
                                       ("0450", "UNUSED_BUT_ALIGNED", "HIGH")):
            resource_id = f"IS529N-CENSUS-{suffix}"
            self.connection.execute(
                """INSERT INTO resources(resource_id,title,source_locator,provenance,source_layer,
                file_type,historical_status,source_type,source_quality,factual_currency_status,
                verification_status) VALUES (?,?,?,'synthetic','RAW_RESOURCE_LAYER','PDF',
                'HISTORICAL_READ_ONLY','SCHOLARLY_ARTICLE','HIGH','NEEDS_UPDATE','SELECTIVELY_INSPECTED')""",
                (resource_id, f"Synthetic source {suffix}",
                 f"<HISTORICAL_RESOURCE_REPOSITORY>/synthetic/{suffix}.pdf"),
            )
            self.connection.execute(
                """INSERT INTO historical_resource_cluster_items(cluster_id,source_identifier,
                filename,source_type,source_sha256,historical_use,alignment,relevant_dimensions,
                verification_status,notes) VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (resource_cluster_pk, resource_id, f"{suffix}.pdf", "PDF", suffix * 16,
                 use, alignment, '["regional imagination"]', "SELECTIVELY_INSPECTED",
                 "Synthetic profile; no copyrighted content."),
            )
        self.connection.commit()


class ReinforcementWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.database_path = self.root / "state.sqlite3"
        self.connection = initialise(self.database_path, self.root / "missing.json")
        ReinforcementFixture(self.root, self.connection).seed()
        self.service = ReinforcementService(self.connection, self.root)

    def tearDown(self) -> None:
        self.connection.close()
        self.temporary.cleanup()

    def advance_to_units(self) -> None:
        self.service.open_historical()
        self.service.select_cluster("KC01")
        self.service.find_aligned_resources()
        self.service.extract_knowledge_units()

    def advance_to_slides(self) -> None:
        self.advance_to_units()
        self.service.select_rotation("TEMPORAL")
        self.service.generate_patterns()
        self.service.pattern_action("KC01-PATTERN-A", "SELECT")
        self.service.pattern_action("KC01-PATTERN-A", "CONFIRM_PATTERN")
        self.service.generate_reinforced_slides()

    def resolve_units_and_slides(self) -> None:
        for row in self.connection.execute("SELECT knowledge_unit_id FROM knowledge_units"):
            self.service.unit_action(row[0], "ADD_TO_CLUSTER")
        for row in self.connection.execute("SELECT reinforced_slide_id FROM reinforced_slides"):
            self.service.slide_action(row[0], "ACCEPT")

    @staticmethod
    def valid_slide_update_yaml() -> str:
        return """slide_id: L01-DECK-005-S003
revision_rationale: Reduced density and separated the inherited concepts.
central_proposition: South Asia is both imagined as a region and known through situated practices.
updated_slide_title: Ontology of the South Asian Region
student_visible_content:
  - Cultural-spiritual geography preceded modern territorial borders.
  - Regional claims require explicit evidence and historical qualification.
speaker_notes: Distinguish the question of what the region is from how it is known.
visual_recommendation: A source-backed conceptual diagram, not an invented map.
source_citations:
  - Synthetic source 0449, page verification still required.
claims_verified: []
claims_requiring_verification:
  - The historical Jambudvipa and Mount Meru claims.
material_moved_to_notes:
  - Detailed examples from the inherited slide.
relationship_to_previous_slide: Develops the opening question posed on Slide 2.
relationship_to_next_slide: Hands the epistemological method to Slide 4.
estimated_teaching_time: 90 seconds
confidence: PROVISIONAL
"""

    def test_resource_identifier_recognises_non_census_packet_sources(self) -> None:
        text = "IS529N-ALI-GOP-PART-04 and IS529N-VALDIYA-GPG-CH01"
        self.assertEqual(
            set(RESOURCE_IDENTIFIER_RE.findall(text)),
            {"IS529N-ALI-GOP-PART-04", "IS529N-VALDIYA-GPG-CH01"},
        )

    def test_cluster_creation_fixed_ranges_activation_and_locking(self) -> None:
        rows = self.connection.execute(
            "SELECT cluster_id,slide_start,slide_end,active,status FROM lecture_knowledge_clusters ORDER BY cluster_id"
        ).fetchall()
        self.assertEqual(len(rows), 6)
        self.assertEqual(tuple(rows[0][:4]), ("KC01", 3, 18, 1))
        self.assertTrue(all(row[3] == 0 and row[4] == "NOT_STARTED" for row in rows[1:]))
        with self.assertRaises(ReinforcementError):
            self.service.select_cluster("KC02")

    def test_historical_open_and_derivative_slide_decision(self) -> None:
        source = self.root / "historical.bin"
        source.write_bytes(b"immutable historical bytes")
        before = hashlib.sha256(source.read_bytes()).hexdigest()
        self.service.open_historical()
        self.service.historical_decision("L01-DECK-005-S007", "MERGE", "Instructor decision")
        decision = json.loads(self.service.cluster()["historical_slide_decisions"])
        self.assertEqual(decision["L01-DECK-005-S007"]["decision"], "MERGE")
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), before)

    def test_resource_group_scope_and_no_registry_admission(self) -> None:
        self.service.open_historical(); self.service.select_cluster("KC01")
        before = self.connection.execute("SELECT COUNT(*) FROM candidate_registry_records").fetchone()[0]
        self.assertEqual(self.service.find_aligned_resources(), 2)
        rows = self.connection.execute(
            "SELECT DISTINCT resource_group_id FROM cluster_resource_alignments"
        ).fetchall()
        self.assertEqual([row[0] for row in rows], ["LEC_RES_1"])
        self.assertEqual(self.connection.execute("SELECT COUNT(*) FROM candidate_registry_records").fetchone()[0], before)

    def test_knowledge_unit_provenance_type_validation_and_actions(self) -> None:
        self.advance_to_units()
        self.assertEqual(self.connection.execute("SELECT COUNT(*) FROM knowledge_units").fetchone()[0], 16)
        row = self.connection.execute("SELECT * FROM knowledge_units ORDER BY id LIMIT 1").fetchone()
        self.assertTrue(row["source_location"].startswith("<HISTORICAL_RESOURCE_REPOSITORY>"))
        self.assertTrue(json.loads(row["historical_slide_ids"]))
        self.service.unit_action(row["knowledge_unit_id"], "ADD_TO_SLIDE")
        self.assertEqual(self.connection.execute(
            "SELECT instructor_status FROM knowledge_units WHERE id=?", (row["id"],)
        ).fetchone()[0], "ADD_TO_SLIDE")
        with self.assertRaises(ReinforcementError):
            self.service.unit_action(row["knowledge_unit_id"], "MAKE_AUTHORITATIVE")

    def test_rotations_candidate_patterns_and_no_automatic_decision(self) -> None:
        self.advance_to_units()
        self.service.select_rotation("RELATIONAL")
        self.assertEqual(self.service.generate_patterns(), 3)
        rows = self.connection.execute(
            "SELECT pattern_id,status FROM knowledge_patterns ORDER BY pattern_id"
        ).fetchall()
        self.assertEqual([r[0] for r in rows], ["KC01-PATTERN-A", "KC01-PATTERN-B", "KC01-PATTERN-C"])
        self.assertTrue(all(r[1] == "REVIEW_REQUIRED" for r in rows))
        self.assertEqual(self.service.cluster()["selected_pattern_id"], "")
        with self.assertRaises(ReinforcementError):
            self.service.select_rotation("GENERIC_AI")

    def test_pattern_confirmation_rejection_and_combination(self) -> None:
        self.advance_to_units(); self.service.generate_patterns()
        self.service.pattern_action("KC01-PATTERN-C", "REJECT", comment="Not for this cluster")
        self.assertEqual(self.connection.execute(
            "SELECT status FROM knowledge_patterns WHERE pattern_id='KC01-PATTERN-C'"
        ).fetchone()[0], "REJECTED")
        combined = self.service.pattern_action(
            "KC01-PATTERN-A", "COMBINE", other_pattern_id="KC01-PATTERN-B",
            value="Instructor combined proposition",
        )
        self.assertEqual(combined, "KC01-PATTERN-COMBINED")
        self.service.pattern_action("KC01-PATTERN-A", "SELECT")
        self.service.pattern_action("KC01-PATTERN-A", "CONFIRM_PATTERN")
        self.assertEqual(self.connection.execute(
            "SELECT status FROM knowledge_patterns WHERE pattern_id='KC01-PATTERN-A'"
        ).fetchone()[0], "CONFIRMED")

    def test_historical_reinforced_mapping_and_slide_decision_persistence(self) -> None:
        self.advance_to_slides()
        workspace = self.service.workspace("slides")
        self.assertGreaterEqual(len(workspace["reinforced_slides"]), 5)
        self.assertTrue(workspace["reinforced_slides"][0]["historical"])
        slide_id = workspace["reinforced_slides"][0]["reinforced_slide_id"]
        self.service.slide_action(slide_id, "REQUEST_NEW_VISUAL", "Use source-backed map")
        row = self.connection.execute(
            "SELECT status,instructor_comment FROM reinforced_slides WHERE reinforced_slide_id=?", (slide_id,)
        ).fetchone()
        self.assertEqual(tuple(row), ("REQUEST_NEW_VISUAL", "Use source-backed map"))

    def test_rehearsal_timing_comments_and_acceptance_refusal(self) -> None:
        self.advance_to_slides(); self.resolve_units_and_slides()
        rehearsal_id = self.service.start_rehearsal()
        first = self.connection.execute("SELECT reinforced_slide_id FROM reinforced_slides ORDER BY sequence").fetchone()[0]
        self.service.rehearsal_event(
            rehearsal_id, "ADD_TEACHING_COMMENT", slide_id=first,
            elapsed_seconds=42, comment="Transition needs tightening",
        )
        self.service.rehearsal_event(rehearsal_id, "END_REHEARSAL", elapsed_seconds=18)
        rehearsal = self.connection.execute(
            "SELECT * FROM cluster_rehearsals WHERE rehearsal_id=?", (rehearsal_id,)
        ).fetchone()
        self.assertEqual(rehearsal["actual_seconds"], 60)
        self.assertIn("Transition needs tightening", rehearsal["instructor_comments"])
        self.service.unit_action(
            self.connection.execute("SELECT knowledge_unit_id FROM knowledge_units LIMIT 1").fetchone()[0],
            "MARK_FOR_VERIFICATION",
        )
        with self.assertRaisesRegex(ReinforcementError, "acceptance refused"):
            self.service.accept_cluster("ACCEPT_CLUSTER")

    def test_cluster_acceptance_and_v05_build_lock(self) -> None:
        self.advance_to_slides(); self.resolve_units_and_slides()
        rehearsal_id = self.service.start_rehearsal()
        self.service.rehearsal_event(rehearsal_id, "END_REHEARSAL", elapsed_seconds=600)
        acceptance_id = self.service.accept_cluster("ACCEPT_CLUSTER", "KC01 accepted locally")
        self.assertTrue(acceptance_id.startswith("KC01-ACC-"))
        workspace = self.service.workspace("build")
        self.assertEqual(workspace["counts"]["accepted_clusters"], 1)
        self.assertTrue(workspace["build_locked"])
        self.assertEqual(workspace["workflow"]["build"], "LOCKED")

    def test_transaction_rollback_and_symbolic_path_enforcement(self) -> None:
        self.advance_to_units(); self.service.generate_patterns()
        before = self.connection.execute("SELECT COUNT(*) FROM knowledge_patterns").fetchone()[0]
        with self.assertRaises(ReinforcementError):
            self.service.pattern_action(
                "KC01-PATTERN-A", "COMBINE", other_pattern_id="MISSING"
            )
        self.assertEqual(self.connection.execute("SELECT COUNT(*) FROM knowledge_patterns").fetchone()[0], before)
        cluster_pk = self.service.cluster()["id"]
        with self.assertRaises(sqlite3.IntegrityError):
            self.connection.execute(
                """INSERT INTO knowledge_units(knowledge_unit_id,cluster_id,source_identifier,
                unit_type,unit_text,source_pages,source_location) VALUES
                ('BAD-PATH',?,'R','CLAIM','x','1','/private/source.pdf')""", (cluster_pk,)
            )

    def test_structured_import_is_review_only_and_requires_provenance(self) -> None:
        self.advance_to_units()
        result = self.service.import_ai_draft(json.dumps({"knowledge_units": [{
            "knowledge_unit_id": "AI-KU-001", "unit_type": "CLAIM",
            "unit_text": "Synthetic imported claim", "source_identifier": "IS529N-CENSUS-0449",
            "source_pages": "p. 1", "historical_slide_ids": ["L01-DECK-005-S003"],
        }]}))
        self.assertEqual(result["knowledge_units"], 1)
        row = self.connection.execute(
            "SELECT origin,verification_status,instructor_status FROM knowledge_units WHERE knowledge_unit_id='AI-KU-001'"
        ).fetchone()
        self.assertEqual(tuple(row), ("AI_ASSISTED_DRAFT", "REQUIRES_INSTRUCTOR_REVIEW", "NOT_YET_DECIDED"))
        with self.assertRaises(ReinforcementError):
            self.service.import_ai_draft(json.dumps({"knowledge_units": [{
                "knowledge_unit_id": "AI-KU-002", "unit_type": "CLAIM", "unit_text": "x",
                "source_identifier": "IS529N-CENSUS-0449", "historical_slide_ids": [],
            }]}))

    def test_slide3_ai_packet_requires_eligible_explicit_decision(self) -> None:
        self.service.open_historical()
        self.service.historical_decision("L01-DECK-005-S003", "KEEP", "Keep it")
        with self.assertRaisesRegex(ReinforcementError, "explicitly choose"):
            self.service.prepare_ai_update_packet("L01-DECK-005-S003")
        override = self.service.prepare_ai_update_packet(
            "L01-DECK-005-S003", support_override=True
        )
        self.assertEqual(override["lifecycle_state"], "CORPUS_READY")
        self.service.historical_decision("L01-DECK-005-S004", "UPDATE", "Revise")
        with self.assertRaisesRegex(ReinforcementError, "limited to Historical Slide 3"):
            self.service.prepare_ai_update_packet("L01-DECK-005-S004")
        self.service.historical_decision("L01-DECK-005-S003", "UPDATE", "")
        with self.assertRaisesRegex(ReinforcementError, "intervention note"):
            self.service.prepare_ai_update_packet("L01-DECK-005-S003")

    def test_ai_packet_is_complete_separates_corpora_and_preserves_history(self) -> None:
        self.service.open_historical()
        direction = "Reduce density, verify claims, and coordinate with Slide 4."
        self.service.historical_decision("L01-DECK-005-S003", "UPDATE", direction)
        packet = self.service.prepare_ai_update_packet("L01-DECK-005-S003")
        body = packet["packet_markdown"]
        self.assertEqual(packet["status"], "PREPARED")
        self.assertEqual(len(packet["slide_corpus_json"]), 2)
        for required in ("# IS529N Slide Reinforcement Packet", "## Original slide content",
                         "## Slide corpus", "## Cluster corpus context", "## Lecture context",
                         "## Required output", direction, "student_visible_content:"):
            self.assertIn(required, body)
        self.assertNotIn(str(self.root), body)
        self.assertTrue(all("relevant_pages" in source for source in packet["slide_corpus_json"]))
        self.assertTrue(all(source["symbolic_location"].startswith("<")
                            for source in packet["slide_corpus_json"]))
        second = self.service.prepare_ai_update_packet("L01-DECK-005-S003")
        self.assertEqual(second["packet_id"], "KC01-S003-AIUP-002")
        self.assertEqual(self.connection.execute(
            "SELECT COUNT(*) FROM slide_ai_update_packets"
        ).fetchone()[0], 2)

    def test_ai_result_validation_comparison_labels_and_explicit_ruling(self) -> None:
        self.service.open_historical()
        self.service.historical_decision("L01-DECK-005-S003", "UPDATE", "Instructor direction")
        packet = self.service.prepare_ai_update_packet("L01-DECK-005-S003")
        original = self.connection.execute(
            "SELECT text_extract FROM historical_slides WHERE historical_slide_id='L01-DECK-005-S003'"
        ).fetchone()[0]
        self.service.mark_ai_packet_copied(packet["packet_id"])
        self.service.mark_ai_packet_sent(packet["packet_id"])
        self.service.paste_ai_update_result(packet["packet_id"], "slide_id: wrong")
        rejected = self.service.validate_ai_update_result(packet["packet_id"])
        self.assertFalse(rejected["valid"])
        self.assertTrue(rejected["errors"])
        self.assertEqual(self.service.ai_update_packet(packet["packet_id"])["lifecycle_state"], "AI_RESULT_INVALID")
        self.service.paste_ai_update_result(packet["packet_id"], self.valid_slide_update_yaml())
        accepted = self.service.validate_ai_update_result(packet["packet_id"])
        self.assertTrue(accepted["valid"])
        stored = self.service.ai_update_packet(packet["packet_id"])
        self.assertEqual(stored["draft_label"], "AI_ASSISTED_DRAFT")
        self.assertEqual(stored["review_label"], "REQUIRES_INSTRUCTOR_REVIEW")
        self.assertEqual(stored["lifecycle_state"], "AI_RESULT_VALIDATED")
        with self.assertRaisesRegex(ReinforcementError, "attach"):
            self.service.accept_reinforced_slide(packet["packet_id"], "RESOLVED")
        self.service.open_instructor_editing(packet["packet_id"])
        self.service.save_instructor_edit(packet["packet_id"], {
            "updated_slide_title": "Instructor-edited title",
            "student_visible_content": ["Instructor-edited bullet"],
        })
        edited = self.service.ai_update_packet(packet["packet_id"])
        self.assertEqual(edited["active_revision"]["validated_result_json"]["updated_slide_title"],
                         "Ontology of the South Asian Region")
        self.assertEqual(edited["active_revision"]["instructor_edit_json"]["updated_slide_title"],
                         "Instructor-edited title")
        self.service.record_manual_application(
            packet["packet_id"], "Rebuilt manually in a working derivative.",
            "Instructor", "<WORKING_LECTURE_DERIVATIVE>/slide-003",
        )
        self.service.attach_reinforced_slide(
            packet["packet_id"], reference="<WORKING_LECTURE_DERIVATIVE>/slide-003.png",
            checksum="b" * 64,
        )
        self.service.accept_reinforced_slide(packet["packet_id"], "EXPLICITLY_DEFERRED")
        final = self.service.ai_update_packet(packet["packet_id"])
        self.assertEqual(final["lifecycle_state"], "INSTRUCTOR_ACCEPTED")
        self.assertEqual(final["final_slide_status"], "INSTRUCTOR_ACCEPTED_REINFORCED_SLIDE")
        self.assertEqual(self.connection.execute(
            "SELECT text_extract FROM historical_slides WHERE historical_slide_id='L01-DECK-005-S003'"
        ).fetchone()[0], original)

    def test_ai_packet_browser_controls_and_download(self) -> None:
        self.service.open_historical()
        self.service.historical_decision("L01-DECK-005-S003", "UPDATE", "Synthetic direction")
        packet = self.service.prepare_ai_update_packet("L01-DECK-005-S003")
        self.connection.close()
        app = create_app(self.root, self.database_path)
        client = TestClient(app)
        page = client.get("/lectures/IS529N-L01-A/reinforcement?stage=historical")
        self.assertEqual(page.status_code, 200)
        for label in ("Copy for ChatGPT", "Download Packet", "CORPUS_READY"):
            self.assertIn(label, page.text)
        download = client.get(
            f"/lectures/IS529N-L01-A/reinforcement/ai-update-packets/{packet['packet_id']}/download"
        )
        self.assertEqual(download.status_code, 200)
        self.assertIn("# IS529N Slide Reinforcement Packet", download.text)
        self.assertIn("IS529N_L01A_KC01_S003_UPDATE_PACKET.md",
                      download.headers["content-disposition"])
        client.post("/lectures/IS529N-L01-A/reinforcement/action", data={
            "command": "MARK_AI_PACKET_COPIED", "target_id": packet["packet_id"],
            "return_stage": "historical",
        })
        copied = client.get("/lectures/IS529N-L01-A/reinforcement?stage=historical")
        self.assertIn("Mark as Sent", copied.text)
        client.post("/lectures/IS529N-L01-A/reinforcement/action", data={
            "command": "MARK_AI_PACKET_SENT", "target_id": packet["packet_id"],
            "return_stage": "historical",
        })
        client.post("/lectures/IS529N-L01-A/reinforcement/action", data={
            "command": "PASTE_AI_UPDATE_RESULT", "target_id": packet["packet_id"],
            "return_stage": "historical", "structured_result": self.valid_slide_update_yaml(),
        })
        validated = client.post("/lectures/IS529N-L01-A/reinforcement/action", data={
            "command": "VALIDATE_AI_UPDATE_RESULT", "target_id": packet["packet_id"],
            "return_stage": "historical",
        })
        self.assertEqual(validated.status_code, 200)
        for label in ("Compare Old and Proposed", "Open Instructor Editing View", "Return for Revision"):
            self.assertIn(label, validated.text)
        editing = client.post("/lectures/IS529N-L01-A/reinforcement/action", data={
            "command": "OPEN_INSTRUCTOR_EDITING", "target_id": packet["packet_id"],
            "return_stage": "historical",
        })
        self.assertIn("Save Instructor Edit", editing.text)
        edited = client.post("/lectures/IS529N-L01-A/reinforcement/action", data={
            "command": "SAVE_INSTRUCTOR_EDIT", "target_id": packet["packet_id"],
            "return_stage": "historical", "updated_slide_title": "Instructor browser edit",
            "student_visible_content": "One concise bullet", "speaker_notes": "Notes",
            "visual_recommendation": "Source-backed diagram",
            "source_citations": "Synthetic source 0449",
            "relationship_to_previous_slide": "Previous", "relationship_to_next_slide": "Next",
            "claims_requiring_verification": "Verify inherited claim",
        })
        self.assertIn("Mark as Manually Applied", edited.text)
        applied = client.post("/lectures/IS529N-L01-A/reinforcement/action", data={
            "command": "MARK_MANUALLY_APPLIED", "target_id": packet["packet_id"],
            "return_stage": "historical", "application_note": "Applied manually",
            "applied_by": "Instructor", "slide_file_or_version_reference": "working-copy-slide-003",
        })
        self.assertIn("Attach Revised Slide", applied.text)
        attached = client.post("/lectures/IS529N-L01-A/reinforcement/action", data={
            "command": "ATTACH_REVISED_SLIDE", "target_id": packet["packet_id"],
            "return_stage": "historical",
            "reinforced_slide_reference": "<WORKING_LECTURE_DERIVATIVE>/slide-003.png",
            "reinforced_slide_checksum": "c" * 64,
        })
        self.assertIn("Accept Reinforced Slide", attached.text)
        self.connection = initialise(self.database_path, self.root / "missing.json")

    def test_unknown_source_rejected_and_return_preserves_prior_revision(self) -> None:
        self.service.open_historical()
        self.service.historical_decision("L01-DECK-005-S003", "UPDATE", "Synthetic direction")
        packet = self.service.prepare_ai_update_packet("L01-DECK-005-S003")
        self.service.mark_ai_packet_copied(packet["packet_id"])
        self.service.mark_ai_packet_sent(packet["packet_id"])
        unknown = self.valid_slide_update_yaml().replace(
            "Synthetic source 0449", "IS529N-CENSUS-0999"
        )
        self.service.paste_ai_update_result(packet["packet_id"], unknown)
        rejected = self.service.validate_ai_update_result(packet["packet_id"])
        self.assertFalse(rejected["valid"])
        self.assertTrue(any("unknown source IDs" in item for item in rejected["errors"]))
        self.service.paste_ai_update_result(packet["packet_id"], self.valid_slide_update_yaml())
        self.assertTrue(self.service.validate_ai_update_result(packet["packet_id"])["valid"])
        self.service.return_ai_update_for_revision(
            packet["packet_id"], "Verify the cited page.", "CITATION"
        )
        self.service.paste_ai_update_result(packet["packet_id"], self.valid_slide_update_yaml())
        revisions = self.connection.execute(
            "SELECT status FROM slide_ai_update_revisions ORDER BY sequence"
        ).fetchall()
        self.assertEqual(len(revisions), 3)
        self.assertEqual(revisions[1][0], "RETURNED_FOR_REVISION")

    def test_forbidden_approval_claim_and_local_attachment_controls(self) -> None:
        self.service.open_historical()
        self.service.historical_decision("L01-DECK-005-S003", "UPDATE", "Synthetic direction")
        packet = self.service.prepare_ai_update_packet("L01-DECK-005-S003")
        self.service.mark_ai_packet_copied(packet["packet_id"])
        self.service.mark_ai_packet_sent(packet["packet_id"])
        forbidden = self.valid_slide_update_yaml().replace(
            "PROVISIONAL", "Approved and classroom-ready"
        )
        self.service.paste_ai_update_result(packet["packet_id"], forbidden)
        validation = self.service.validate_ai_update_result(packet["packet_id"])
        self.assertFalse(validation["valid"])
        self.assertTrue(any("forbidden" in item for item in validation["errors"]))
        self.service.paste_ai_update_result(packet["packet_id"], self.valid_slide_update_yaml())
        self.assertTrue(self.service.validate_ai_update_result(packet["packet_id"])["valid"])
        self.service.open_instructor_editing(packet["packet_id"])
        self.service.save_instructor_edit(packet["packet_id"], {}, waive=True)
        self.service.record_manual_application(
            packet["packet_id"], "Applied in a protected working derivative.",
            "Instructor", "working-copy-slide-003",
        )
        with self.assertRaisesRegex(ReinforcementError, "symbolic"):
            self.service.attach_reinforced_slide(
                packet["packet_id"], reference="/private/revised.png", checksum="d" * 64
            )
        attachment = self.service.attach_reinforced_slide(
            packet["packet_id"], filename="revised-slide.png", content=b"synthetic image bytes"
        )
        self.assertEqual(attachment["checksum"], hashlib.sha256(b"synthetic image bytes").hexdigest())
        path = self.service.reinforced_attachment_path(packet["packet_id"])
        self.assertIsNotNone(path)
        self.assertTrue(path.is_file())

    def test_responsive_browser_route_and_tablet_layout(self) -> None:
        self.connection.close()
        app = create_app(self.root, self.database_path)
        client = TestClient(app)
        response = client.get("/lectures/IS529N-L01-A/reinforcement")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Lean Lecture Revision", response.text)
        self.assertIn("Save Revision Draft", response.text)
        self.assertNotIn("Build Next Lecture Version", response.text)
        legacy = client.get("/lectures/IS529N-L01-A/reinforcement?view=legacy&stage=historical")
        self.assertIn("Lecture Reinforcement Workspace", legacy.text)
        self.assertIn("Build Next Lecture Version", legacy.text)
        css = client.get("/static/styles.css").text
        self.assertIn("@media(max-width:900px)", css)
        self.assertIn("@media(max-width:560px)", css)
        self.assertIn("min-height:48px", css)
        self.connection = initialise(self.database_path, self.root / "missing.json")

    def test_lean_pair_direct_source_validate_edit_accept_then_attach(self) -> None:
        self.service.open_historical()
        self.service.select_cluster("KC01")
        self.service.find_aligned_resources()
        lean = LeanRevisionService(self.connection, self.root)
        direct = self.root / "direct-evidence.txt"
        direct.write_text("A page-addressable excerpt for the instructor.", encoding="utf-8")
        before = {
            row["historical_slide_id"]: row["text_extract"]
            for row in self.connection.execute(
                "SELECT historical_slide_id,text_extract FROM historical_slides WHERE historical_slide_number IN (3,4)"
            )
        }
        legacy_packets = self.connection.execute("SELECT COUNT(*) FROM slide_ai_update_packets").fetchone()[0]
        draft = lean.save_draft(
            unit_type="SLIDE_PAIR",
            slide_ids=["L01-DECK-005-S003", "L01-DECK-005-S004"],
            instructor_query="Separate ontology from epistemology and preserve the transition.",
            source_mode="DIRECT_LOCAL", selected_source_ids=[],
            direct_source_text=f"{direct} | p. 1 | Direct local evidence excerpt",
        )
        packet = lean.prepare_packet(draft["unit_id"])
        self.assertEqual(packet["status"], "AI_PREPARED")
        self.assertIn(str(direct), packet["packet_markdown"])
        self.assertNotIn("Mark as Sent", packet["packet_markdown"])
        payload = {
            "unit_id": draft["unit_id"],
            "slides": [
                {"slide_id": "L01-DECK-005-S003", "title": "Ontology",
                 "student_visible_content": ["What kind of region is represented?"],
                 "speaker_notes": "Keep attributed interpretations qualified.",
                 "visual_recommendation": "Concept diagram", "transition_from_previous": "Question",
                 "transition_to_next": "How was this knowledge produced?"},
                {"slide_id": "L01-DECK-005-S004", "title": "Epistemology",
                 "student_visible_content": ["How was regional knowledge produced?"],
                 "speaker_notes": "Distinguish narration, observation and pilgrimage.",
                 "visual_recommendation": "Process diagram", "transition_from_previous": "From what to how",
                 "transition_to_next": "Continue the lecture sequence"},
            ],
            "sources_used": [draft["direct_sources_json"][0]["source_id"]],
            "claims_qualified": ["Meru-Pamir remains an attributed interpretation."],
        }
        validation = lean.paste_and_validate(draft["unit_id"], json.dumps(payload))
        self.assertTrue(validation["valid"], validation["errors"])
        lean.save_instructor_edit(draft["unit_id"], payload)
        accepted = lean.accept_content(draft["unit_id"], "Instructor")
        self.assertEqual(accepted["status"], "CONTENT_ACCEPTED")
        self.assertEqual(accepted["artefact_status"], "NOT_ATTACHED")
        attached = lean.attach_artefact(draft["unit_id"], reference="working-pair-3-4.pptx")
        self.assertEqual(attached["artefact_status"], "ARTEFACT_ATTACHED")
        after = {
            row["historical_slide_id"]: row["text_extract"]
            for row in self.connection.execute(
                "SELECT historical_slide_id,text_extract FROM historical_slides WHERE historical_slide_number IN (3,4)"
            )
        }
        self.assertEqual(after, before)
        self.assertEqual(
            self.connection.execute("SELECT COUNT(*) FROM slide_ai_update_packets").fetchone()[0],
            legacy_packets,
        )

    def test_lean_repository_source_and_browser_controls(self) -> None:
        self.service.open_historical()
        self.service.select_cluster("KC01")
        self.service.find_aligned_resources()
        lean = LeanRevisionService(self.connection, self.root)
        draft = lean.save_draft(
            unit_type="SINGLE_SLIDE", slide_ids=["L01-DECK-005-S003"],
            instructor_query="Reduce visible text and retain source qualifications.",
            source_mode="REPOSITORY", selected_source_ids=["IS529N-CENSUS-0449"],
            direct_source_text="",
        )
        lean.prepare_packet(draft["unit_id"])
        self.connection.close()
        app = create_app(self.root, self.database_path)
        client = TestClient(app)
        page = client.get(f"/lectures/IS529N-L01-A/reinforcement?unit={draft['unit_id']}")
        for label in ("Copy AI Packet", "Download AI Packet", "Paste and Validate"):
            self.assertIn(label, page.text)
        self.assertNotIn("Mark as Sent", page.text)
        download = client.get(
            f"/lectures/IS529N-L01-A/reinforcement/lean/{draft['unit_id']}/download"
        )
        self.assertEqual(download.status_code, 200)
        self.assertIn("IS529N-CENSUS-0449", download.text)
        self.connection = initialise(self.database_path, self.root / "missing.json")


if __name__ == "__main__":
    unittest.main()
