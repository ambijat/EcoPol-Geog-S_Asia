from __future__ import annotations

import json
from urllib.parse import urlparse

from gui.services import utc_now, validate_relative_path
from qt_gui.database.connection import DatabaseManager


EVIDENCE_LAYERS = {
    "HISTORICAL_PPT_LAYER", "RAW_RESOURCE_LAYER", "WEBSITE_LEARNING_LAYER",
}
ALIGNMENT_LEVELS = {
    "HIGH_ALIGNMENT", "MODERATE_ALIGNMENT", "LOW_ALIGNMENT", "OUT_OF_DOMAIN", "UNRESOLVED",
}
EVIDENTIARY_VALUES = {"HIGH", "MEDIUM", "LOW", "UNKNOWN"}
CURRENCY_LEVELS = {"CURRENT", "NEEDS_UPDATE", "HISTORICAL_ONLY", "DATE_UNCERTAIN", "NOT_APPLICABLE"}
WEBSITE_NOTE_STATUSES = {
    "HISTORICAL_AI_NOTE", "AI_NOTE_UNDER_REVIEW", "SOURCE_VERIFIED_AI_NOTE",
    "INSTRUCTOR_REVISED_NOTE", "CURRENT_STUDENT_REFERENCE", "SUPERSEDED_NOTE",
    "ARCHIVE_ONLY", "UNKNOWN_ORIGIN",
}
RECOMMENDED_ACTIONS = {
    "RETAIN", "UPDATE", "EXPAND_USE", "MOVE_TO_PART_A", "MOVE_TO_PART_B",
    "USE_AS_SHARED_RESOURCE", "CREATE_STUDENT_NOTE", "REVISE_WEBSITE_NOTE",
    "ADD_NEW_SLIDE", "REVISE_EXISTING_SLIDE", "REPLACE_SOURCE", "ADD_NEW_SOURCE",
    "EXCLUDE_FROM_ACTIVE_CLUSTER", "ARCHIVE_ONLY", "REQUIRES_FURTHER_REVIEW",
    "IDENTIFY_RAW_SOURCES", "IDENTIFY_WEBSITE_NOTE", "VERIFY_CLAIMS", "REVISE_SLIDE",
}


def _json(values) -> str:
    return json.dumps(list(values), ensure_ascii=False)


def validate_symbolic_location(value: str) -> str:
    if not value:
        return ""
    if value.startswith("<") and ">" in value:
        return value
    parsed = urlparse(value)
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return value
    return validate_relative_path(value)


class TriangulationService:
    def __init__(self, database: DatabaseManager):
        self.database = database

    def create_topic(self, values: dict) -> int:
        if values.get("part") not in {"A", "B"}:
            raise ValueError("triangulation topic part must be A or B")
        now = utc_now()
        with self.database.connection() as connection:
            pair = connection.execute(
                "SELECT id,lecture_id FROM lecture_pairs WHERE lecture_id=?", (values["lecture_id"],)
            ).fetchone()
            if pair is None:
                raise KeyError(values["lecture_id"])
            cursor = connection.execute(
                """INSERT INTO triangulation_topics(triangulation_topic_id,lecture_pair_id,lecture_id,
                part,topic,central_question,historical_slide_ids,working_note_ids,slide_plan_ids,status,
                created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (values["triangulation_topic_id"], pair["id"], pair["lecture_id"], values["part"],
                 values["topic"], values.get("central_question", ""), _json(values.get("historical_slide_ids", [])),
                 _json(values.get("working_note_ids", [])), _json(values.get("slide_plan_ids", [])),
                 values.get("status", "INCOMPLETE"), now, now),
            )
            connection.commit()
            return cursor.lastrowid

    def add_evidence(self, topic_pk: int, values: dict) -> int:
        layer = values.get("evidence_layer")
        alignment = values.get("alignment_level", "UNRESOLVED")
        evidentiary = values.get("evidentiary_value", "UNKNOWN")
        currency = values.get("currency_status", "DATE_UNCERTAIN")
        treatment = int(values.get("treatment_level", 0))
        if layer not in EVIDENCE_LAYERS:
            raise ValueError("invalid evidence layer")
        if not 0 <= treatment <= 4:
            raise ValueError("treatment level must be between 0 and 4")
        if alignment not in ALIGNMENT_LEVELS:
            raise ValueError("invalid alignment level")
        if evidentiary not in EVIDENTIARY_VALUES or currency not in CURRENCY_LEVELS:
            raise ValueError("invalid evidence value or currency status")
        location = validate_symbolic_location(values.get("symbolic_location", ""))
        now = utc_now()
        with self.database.connection() as connection:
            if connection.execute("SELECT id FROM triangulation_topics WHERE id=?", (topic_pk,)).fetchone() is None:
                raise KeyError(topic_pk)
            cursor = connection.execute(
                """INSERT INTO triangulation_evidence(evidence_id,triangulation_topic_id,evidence_layer,
                source_identifier,source_title,source_type,symbolic_location,source_sha256,treatment_level,
                alignment_level,evidentiary_value,verification_status,currency_status,instructor_status,notes,
                created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (values["evidence_id"], topic_pk, layer, values["source_identifier"],
                 values.get("source_title", ""), values.get("source_type", ""), location,
                 values.get("source_sha256", ""), treatment, alignment, evidentiary,
                 values.get("verification_status", "NOT_YET_VERIFIED"), currency,
                 values.get("instructor_status", "ADVISORY"), values.get("notes", ""), now, now),
            )
            connection.commit()
            return cursor.lastrowid

    def add_claim(self, topic_pk: int, values: dict) -> int:
        if values.get("origin_layer") not in EVIDENCE_LAYERS:
            raise ValueError("invalid claim origin layer")
        if values.get("support_level", "UNKNOWN") not in EVIDENTIARY_VALUES:
            raise ValueError("invalid support level")
        if values.get("currency_status", "DATE_UNCERTAIN") not in CURRENCY_LEVELS:
            raise ValueError("invalid currency status")
        now = utc_now()
        with self.database.connection() as connection:
            cursor = connection.execute(
                """INSERT INTO triangulation_claims(claim_id,triangulation_topic_id,claim_text,origin_layer,
                historical_slide_ids,raw_resource_ids,website_note_ids,verification_status,support_level,
                contradiction_status,currency_status,instructor_comment,created_at,updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (values["claim_id"], topic_pk, values["claim_text"], values["origin_layer"],
                 _json(values.get("historical_slide_ids", [])), _json(values.get("raw_resource_ids", [])),
                 _json(values.get("website_note_ids", [])), values.get("verification_status", "NOT_YET_VERIFIED"),
                 values.get("support_level", "UNKNOWN"), values.get("contradiction_status", "UNRESOLVED"),
                 values.get("currency_status", "DATE_UNCERTAIN"), values.get("instructor_comment", ""), now, now),
            )
            connection.commit()
            return cursor.lastrowid

    def add_website_note(self, values: dict) -> int:
        status = values.get("ai_generation_status", "UNKNOWN_ORIGIN")
        if status not in WEBSITE_NOTE_STATUSES:
            raise ValueError("invalid website-note status")
        page_url = values.get("page_url", "")
        if page_url:
            validate_symbolic_location(page_url)
        now = utc_now()
        generated = values.get("generated_by_ai")
        generated_db = None if generated is None else int(bool(generated))
        with self.database.connection() as connection:
            cursor = connection.execute(
                """INSERT INTO website_notes(website_note_id,page_title,page_url,lecture_id,part,topic,
                displayed_revision,displayed_last_edit,generated_by_ai,ai_generation_status,
                instructor_review_status,source_links_present,linked_raw_resource_ids,claims_extracted,
                claims_verified,relationship_to_ppt,student_facing_status,recommended_action,created_at,updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (values["website_note_id"], values["page_title"], page_url, values["lecture_id"],
                 values.get("part", "UNRESOLVED"), values.get("topic", ""),
                 values.get("displayed_revision", ""), values.get("displayed_last_edit", ""), generated_db,
                 status, values.get("instructor_review_status", "NOT_YET_REVIEWED"),
                 int(bool(values.get("source_links_present"))), _json(values.get("linked_raw_resource_ids", [])),
                 int(values.get("claims_extracted", 0)), int(values.get("claims_verified", 0)),
                 values.get("relationship_to_ppt", "UNRESOLVED"),
                 values.get("student_facing_status", "NOT_YET_VERIFIED"),
                 values.get("recommended_action", "REQUIRES_FURTHER_REVIEW"), now, now),
            )
            connection.commit()
            return cursor.lastrowid

    @staticmethod
    def classify_findings(*, historical: bool, raw: bool, website: bool,
                          raw_aligned: bool = False, raw_used: bool = True,
                          website_verified: bool = True, out_of_domain: bool = False,
                          current_source_required: bool = False) -> list[str]:
        findings: list[str] = []
        if out_of_domain:
            return ["OUT_OF_DOMAIN", "ARCHIVE_ONLY"]
        if historical and raw and website and website_verified:
            findings.append("TRIANGULATED_CORE")
        if historical and raw and not website:
            findings.append("CREATE_OR_EXPAND_STUDENT_NOTE")
        if raw and website and not historical:
            findings.append("CANDIDATE_FOR_NEW_SLIDE")
        if (historical or website) and not raw:
            findings.append("SOURCE_VERIFICATION_REQUIRED")
        if raw and raw_aligned and not raw_used:
            findings.append("UNUSED_RELEVANT_RESOURCE")
        if website and not website_verified:
            findings.append("UNVERIFIED_WEBSITE_NOTE")
        if current_source_required and not raw:
            findings.append("NEW_SOURCE_REQUIRED")
        return findings or ["INCOMPLETE"]

    def recalculate_findings(self, topic_pk: int) -> list[str]:
        with self.database.connection() as connection:
            evidence = [dict(row) for row in connection.execute(
                "SELECT * FROM triangulation_evidence WHERE triangulation_topic_id=?", (topic_pk,)
            )]
            layers = {row["evidence_layer"] for row in evidence}
            raw_rows = [row for row in evidence if row["evidence_layer"] == "RAW_RESOURCE_LAYER"]
            website_rows = [row for row in evidence if row["evidence_layer"] == "WEBSITE_LEARNING_LAYER"]
            finding_types = self.classify_findings(
                historical="HISTORICAL_PPT_LAYER" in layers,
                raw=bool(raw_rows), website=bool(website_rows),
                raw_aligned=any(row["alignment_level"] == "HIGH_ALIGNMENT" for row in raw_rows),
                raw_used=any(row["treatment_level"] > 0 for row in raw_rows),
                website_verified=bool(website_rows) and all(row["verification_status"] == "VERIFIED" for row in website_rows),
                out_of_domain=bool(evidence) and all(row["alignment_level"] == "OUT_OF_DOMAIN" for row in evidence),
            )
            if raw_rows and not any(row["verification_status"] == "VERIFIED" for row in raw_rows):
                finding_types.append("SOURCE_VERIFICATION_REQUIRED")
            finding_types = list(dict.fromkeys(finding_types))
            connection.execute("DELETE FROM triangulation_findings WHERE triangulation_topic_id=?", (topic_pk,))
            now = utc_now()
            action_by_finding = {
                "TRIANGULATED_CORE": "RETAIN", "CREATE_OR_EXPAND_STUDENT_NOTE": "CREATE_STUDENT_NOTE",
                "CANDIDATE_FOR_NEW_SLIDE": "ADD_NEW_SLIDE", "SOURCE_VERIFICATION_REQUIRED": "VERIFY_CLAIMS",
                "UNUSED_RELEVANT_RESOURCE": "EXPAND_USE", "UNVERIFIED_WEBSITE_NOTE": "REVISE_WEBSITE_NOTE",
                "OUT_OF_DOMAIN": "EXCLUDE_FROM_ACTIVE_CLUSTER", "ARCHIVE_ONLY": "ARCHIVE_ONLY",
                "NEW_SOURCE_REQUIRED": "ADD_NEW_SOURCE", "INCOMPLETE": "REQUIRES_FURTHER_REVIEW",
            }
            for index, finding in enumerate(finding_types, 1):
                connection.execute(
                    """INSERT INTO triangulation_findings(finding_id,triangulation_topic_id,finding_type,
                    summary,evidence_gap,recommended_action,instructor_status,created_at,updated_at)
                    VALUES (?,?,?,?,?,?,'ADVISORY',?,?)""",
                    (f"TRI-F-{topic_pk:03d}-{index:02d}", topic_pk, finding,
                     finding.replace("_", " ").title(), self._gap_for(finding), action_by_finding[finding], now, now),
                )
            connection.commit()
            return finding_types

    @staticmethod
    def _gap_for(finding: str) -> str:
        return {
            "CREATE_OR_EXPAND_STUDENT_NOTE": "Website learning layer absent or insufficient",
            "CANDIDATE_FOR_NEW_SLIDE": "Historical PPT omits or underuses aligned material",
            "SOURCE_VERIFICATION_REQUIRED": "Reliable raw scholarly support is not linked",
            "UNUSED_RELEVANT_RESOURCE": "Aligned raw source is not used in PPT or website note",
            "UNVERIFIED_WEBSITE_NOTE": "Website claims are not linked to verified raw sources",
            "NEW_SOURCE_REQUIRED": "Current or adequate scholarship is missing",
            "INCOMPLETE": "Three-way evidence is incomplete",
        }.get(finding, "No blocking evidence gap recorded")

    def reconstruct_source_coverage(self, values: dict) -> dict:
        overlaps = {key: float(values.get(key, 0)) for key in (
            "lexical_overlap", "concept_overlap", "data_overlap", "visual_overlap"
        )}
        if any(not 0 <= value <= 1 for value in overlaps.values()):
            raise ValueError("overlap values must be between 0 and 1")
        citation = bool(values.get("citation_match"))
        corroborating = sum(overlaps[key] >= 0.6 for key in ("concept_overlap", "data_overlap", "visual_overlap"))
        lineage = "PROBABLE" if citation or corroborating >= 2 else "UNCONFIRMED"
        confidence = "HIGH" if citation and corroborating else "MEDIUM" if lineage == "PROBABLE" else "LOW"
        use_level = int(values.get("use_level", 0))
        if not 0 <= use_level <= 4:
            raise ValueError("use level must be between 0 and 4")
        result = {**overlaps, "citation_match": citation, "probable_lineage": lineage,
                  "use_level": use_level, "confidence": confidence, "instructor_confirmation": False,
                  "analytical_label": "RETROSPECTIVE_SOURCE_RECONSTRUCTION",
                  "concept": values.get("concept", ""),
                  "present_in_article": bool(values.get("present_in_article", True)),
                  "present_in_historical_slide": bool(values.get("present_in_historical_slide")),
                  "present_in_working_note": bool(values.get("present_in_working_note")),
                  "present_in_slide_plan": bool(values.get("present_in_slide_plan")),
                  "alignment": values.get("alignment", "UNRESOLVED"),
                  "recommended_action": values.get("recommended_action", "REQUIRES_FURTHER_REVIEW"),
                  "page_references": values.get("page_references", ""),
                  "analysis_notes": values.get("analysis_notes", ""),
                  }
        with self.database.connection() as connection:
            connection.execute(
                """INSERT INTO source_coverage_reconstructions(reconstruction_id,historical_slide_id,
                candidate_source_id,lexical_overlap,concept_overlap,data_overlap,visual_overlap,citation_match,
                probable_lineage,use_level,confidence,instructor_confirmation,created_at,concept,
                present_in_article,present_in_historical_slide,present_in_working_note,present_in_slide_plan,
                alignment,recommended_action,page_references,analysis_notes)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (values["reconstruction_id"], values["historical_slide_id"], values["candidate_source_id"],
                 overlaps["lexical_overlap"], overlaps["concept_overlap"], overlaps["data_overlap"],
                 overlaps["visual_overlap"], int(citation), lineage, use_level, confidence, 0, utc_now(),
                 result["concept"], int(result["present_in_article"]), int(result["present_in_historical_slide"]),
                 int(result["present_in_working_note"]), int(result["present_in_slide_plan"]),
                 result["alignment"], result["recommended_action"], result["page_references"],
                 result["analysis_notes"]),
            )
            connection.commit()
        return result

    def prepare_registry_candidate(self, topic_pk: int, values: dict) -> int:
        if values.get("evidence_layer") not in EVIDENCE_LAYERS:
            raise ValueError("invalid candidate evidence layer")
        location = validate_symbolic_location(values.get("symbolic_location", ""))
        with self.database.connection() as connection:
            cursor = connection.execute(
                """INSERT INTO candidate_registry_records(candidate_id,triangulation_topic_id,evidence_layer,
                source_identifier,title,symbolic_location,source_sha256,admission_status,instructor_decision,
                canonical_registration_performed,notes,created_at) VALUES (?,?,?,?,?,?,?,?,?,0,?,?)""",
                (values["candidate_id"], topic_pk, values["evidence_layer"], values["source_identifier"],
                 values.get("title", ""), location, values.get("source_sha256", ""),
                 values.get("admission_status", "PENDING_INSTRUCTOR_ADMISSION"), "NOT_YET_DECIDED",
                 values.get("notes", ""), utc_now()),
            )
            connection.commit()
            return cursor.lastrowid

    def create_learning_package(self, values: dict) -> int:
        if values.get("part") not in {"A", "B"}:
            raise ValueError("learning package part must be A or B")
        if values.get("public_approval_status", "NOT_APPROVED") == "APPROVED":
            raise ValueError("Phase 4 does not approve student learning packages")
        now = utc_now()
        with self.database.connection() as connection:
            pair = connection.execute("SELECT id FROM lecture_pairs WHERE lecture_id=?", (values["lecture_id"],)).fetchone()
            if pair is None:
                raise KeyError(values["lecture_id"])
            cursor = connection.execute(
                """INSERT INTO student_learning_packages(learning_package_id,lecture_pair_id,lecture_id,part,
                classroom_deck_id,website_note_ids,raw_resource_ids,public_link_ids,verification_status,
                public_approval_status,instructor_status,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (values["learning_package_id"], pair[0], values["lecture_id"], values["part"],
                 values.get("classroom_deck_id"), _json(values.get("website_note_ids", [])),
                 _json(values.get("raw_resource_ids", [])), _json(values.get("public_link_ids", [])),
                 values.get("verification_status", "NOT_YET_VERIFIED"), "NOT_APPROVED",
                 values.get("instructor_status", "WORKING_DRAFT"), now, now),
            )
            connection.commit()
            return cursor.lastrowid

    def topic_detail(self, topic_pk: int) -> dict:
        with self.database.connection() as connection:
            topic = connection.execute("SELECT * FROM triangulation_topics WHERE id=?", (topic_pk,)).fetchone()
            if topic is None:
                raise KeyError(topic_pk)
            return {
                "topic": dict(topic),
                "evidence": [dict(row) for row in connection.execute(
                    "SELECT * FROM triangulation_evidence WHERE triangulation_topic_id=? ORDER BY evidence_layer,evidence_id", (topic_pk,))],
                "claims": [dict(row) for row in connection.execute(
                    "SELECT * FROM triangulation_claims WHERE triangulation_topic_id=? ORDER BY claim_id", (topic_pk,))],
                "findings": [dict(row) for row in connection.execute(
                    "SELECT * FROM triangulation_findings WHERE triangulation_topic_id=? ORDER BY id", (topic_pk,))],
                "candidates": [dict(row) for row in connection.execute(
                    "SELECT * FROM candidate_registry_records WHERE triangulation_topic_id=? ORDER BY id", (topic_pk,))],
            }

    def record_decision(self, topic_pk: int, finding_pk: int | None, values: dict) -> int:
        recommendation = values.get("recommended_action", "REQUIRES_FURTHER_REVIEW")
        decision = values.get("instructor_decision", "NOT_YET_DECIDED")
        if recommendation not in RECOMMENDED_ACTIONS:
            raise ValueError("invalid recommended action")
        if decision != "NOT_YET_DECIDED" and decision not in RECOMMENDED_ACTIONS:
            raise ValueError("invalid instructor decision")
        confirmed = bool(values.get("confirmed"))
        if confirmed and decision == "NOT_YET_DECIDED":
            raise ValueError("confirmation requires an instructor decision")
        now = utc_now()
        with self.database.connection() as connection:
            next_number = connection.execute(
                "SELECT COUNT(*)+1 FROM triangulation_decisions WHERE triangulation_topic_id=?", (topic_pk,)
            ).fetchone()[0]
            cursor = connection.execute(
                """INSERT INTO triangulation_decisions(decision_id,triangulation_topic_id,finding_id,
                recommended_action,instructor_decision,instructor_comment,confirmed,decided_at,created_at)
                VALUES (?,?,?,?,?,?,?,?,?)""",
                (f"TRI-D-{topic_pk:03d}-{next_number:02d}", topic_pk, finding_pk, recommendation,
                 decision, values.get("instructor_comment", ""), int(confirmed), now if confirmed else "", now),
            )
            connection.commit()
            return cursor.lastrowid

    def list_topics(self, lecture_number: int) -> list[dict]:
        with self.database.connection() as connection:
            return [dict(row) for row in connection.execute(
                """SELECT tt.*,(SELECT COUNT(*) FROM triangulation_evidence te WHERE te.triangulation_topic_id=tt.id) evidence_count,
                (SELECT COUNT(*) FROM triangulation_findings tf WHERE tf.triangulation_topic_id=tt.id) finding_count
                FROM triangulation_topics tt JOIN lecture_pairs lp ON lp.id=tt.lecture_pair_id
                WHERE lp.lecture_number=? ORDER BY tt.part,tt.topic""", (lecture_number,))]

    def decision_queue(self, lecture_number: int = 1) -> list[dict]:
        with self.database.connection() as connection:
            rows = [dict(row) for row in connection.execute(
                """SELECT tt.topic,tt.lecture_id,tt.part,tf.finding_type,tf.evidence_gap,
                tf.recommended_action,tf.instructor_status
                FROM triangulation_findings tf JOIN triangulation_topics tt ON tt.id=tf.triangulation_topic_id
                JOIN lecture_pairs lp ON lp.id=tt.lecture_pair_id WHERE lp.lecture_number=?
                AND tf.finding_type!='TRIANGULATED_CORE' ORDER BY tf.id""", (lecture_number,))]
        priority = {
            "SOURCE_VERIFICATION_REQUIRED": 1, "UNUSED_RELEVANT_RESOURCE": 2,
            "UNVERIFIED_WEBSITE_NOTE": 3, "CREATE_OR_EXPAND_STUDENT_NOTE": 4,
            "CANDIDATE_FOR_NEW_SLIDE": 5, "NEW_SOURCE_REQUIRED": 6, "INCOMPLETE": 7,
        }
        for row in rows:
            row["why_it_matters"] = row["evidence_gap"]
            row["navigation"] = "Lecture Triangulation"
            row["priority"] = priority.get(row["finding_type"], 8)
        return sorted(rows, key=lambda row: row["priority"])

    @staticmethod
    def title_decision_required(record: dict) -> bool:
        return bool(not record.get("extracted_title") or record.get("sequence_mismatch_warning")
                    or record.get("confidence") not in {"HIGH"}
                    or record.get("title_conflict"))
