from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

import yaml

from gui.services import validate_relative_path


CLUSTER_RANGES = {
    "KC01": (3, 18), "KC02": (19, 27), "KC03": (28, 39),
    "KC04": (40, 46), "KC05": (47, 56), "KC06": (57, 60),
}
KNOWLEDGE_UNIT_TYPES = {
    "CLAIM", "DEFINITION", "CONCEPT", "HISTORICAL_EPISODE", "MAP", "FIGURE",
    "DATASET", "CAUSAL_RELATIONSHIP", "RELATIONAL_PATTERN", "COUNTERARGUMENT",
    "QUOTATION", "EXAMPLE", "LIMITATION",
}
ROTATIONS = {"THEMATIC", "TEMPORAL", "SPATIAL", "RELATIONAL", "EVIDENTIARY", "PEDAGOGICAL"}
HISTORICAL_ACTIONS = {
    "KEEP", "UPDATE", "EXPAND", "MERGE", "SPLIT", "REORDER", "REPLACE",
    "REMOVE", "MOVE_TO_NOTES", "CREATE_NEW",
}
AI_PACKET_ACTIONS = {
    "UPDATE", "EXPAND", "MERGE", "SPLIT", "REPLACE", "CREATE_NEW", "MOVE_TO_NOTES",
}
AI_SUPPORT_OVERRIDE_ACTIONS = {"KEEP", "REMOVE", "REORDER"}
AI_RETURN_TARGETS = {
    "SOURCE_CORPUS", "AI_PROPOSAL", "INSTRUCTOR_EDIT", "VISUAL", "CITATION", "SLIDE_SEQUENCE",
}
AI_UPDATE_REQUIRED_FIELDS = (
    "slide_id", "revision_rationale", "central_proposition", "updated_slide_title",
    "student_visible_content", "speaker_notes", "visual_recommendation",
    "source_citations", "claims_verified", "claims_requiring_verification",
    "material_moved_to_notes", "relationship_to_previous_slide",
    "relationship_to_next_slide", "estimated_teaching_time", "confidence",
)
AI_UPDATE_LIST_FIELDS = {
    "source_citations", "claims_verified", "claims_requiring_verification",
    "material_moved_to_notes",
}
RESOURCE_IDENTIFIER_RE = re.compile(
    r"\bIS529N-(?:CENSUS-\d+|[A-Z][A-Z0-9]*(?:-[A-Z0-9]+){2,})\b"
)
RESOURCE_ACTIONS = {
    "OPEN", "MARK_AS_USED", "MARK_AS_UNDERUSED", "MARK_AS_UNUSED_BUT_RELEVANT",
    "MARK_AS_OUT_OF_DOMAIN", "REQUEST_DEEPER_ANALYSIS", "DEFER",
}
UNIT_ACTIONS = {
    "ADD_TO_CLUSTER", "ADD_TO_SLIDE", "ADD_TO_NOTES", "ADD_TO_READING",
    "MARK_FOR_VERIFICATION", "IGNORE",
}
PATTERN_ACTIONS = {"SELECT", "COMBINE", "REVISE", "REJECT", "SAVE_FOR_LATER"}
SLIDE_ACTIONS = {
    "ACCEPT", "REVISE", "MERGE", "SPLIT", "MOVE", "DELETE",
    "MOVE_DETAIL_TO_NOTES", "REQUEST_NEW_VISUAL", "RETURN_TO_PATTERN",
}
REHEARSAL_EVENTS = {
    "START", "PREVIOUS", "NEXT", "PAUSE", "RESUME", "SHOW_NOTES", "HIDE_NOTES",
    "SHOW_EVIDENCE", "MARK_KEEP", "MARK_REVISE", "MARK_REMOVE",
    "ADD_TEACHING_COMMENT", "END_REHEARSAL",
}
ACCEPTANCE_ACTIONS = {
    "ACCEPT_CLUSTER", "RETURN_TO_SLIDES", "RETURN_TO_SOURCES",
    "RETURN_TO_PATTERNS", "DEFER",
}

DEFAULT_WORKFLOW = {
    "historical": "READY", "cluster": "LOCKED", "resources": "LOCKED",
    "units": "LOCKED", "patterns": "LOCKED", "choice": "LOCKED",
    "slides": "LOCKED", "rehearsal": "LOCKED", "acceptance": "LOCKED",
    "build": "LOCKED",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def json_value(value: str | None, default: Any) -> Any:
    try:
        return json.loads(value or "")
    except (TypeError, json.JSONDecodeError):
        return default


def encoded(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


class ReinforcementError(ValueError):
    pass


class ReinforcementService:
    """Interface-neutral Lecture 1A reinforcement workflow.

    The service stores decisions and generated proposals in the shared database. It never
    opens protected source bytes, registers resources, approves academic content, builds a
    lecture version, or writes to the canonical ledger.
    """

    def __init__(self, connection: sqlite3.Connection, project_root: Path):
        self.connection = connection
        self.project_root = project_root.resolve()

    @contextmanager
    def atomic(self) -> Iterator[None]:
        self.connection.execute("SAVEPOINT reinforcement_action")
        try:
            yield
        except Exception:
            self.connection.execute("ROLLBACK TO reinforcement_action")
            self.connection.execute("RELEASE reinforcement_action")
            raise
        else:
            self.connection.execute("RELEASE reinforcement_action")

    def cluster(self, cluster_id: str = "KC01") -> sqlite3.Row:
        row = self.connection.execute(
            """SELECT c.*,lp.lecture_id,lp.weekly_title FROM lecture_knowledge_clusters c
            JOIN lecture_pairs lp ON lp.id=c.lecture_pair_id
            WHERE c.cluster_id=? AND lp.lecture_id='IS529N-L01' AND c.part='A'""",
            (cluster_id,),
        ).fetchone()
        if row is None:
            raise ReinforcementError(f"unknown Lecture 1A cluster: {cluster_id}")
        expected = CLUSTER_RANGES.get(cluster_id)
        if expected != (row["slide_start"], row["slide_end"]):
            raise ReinforcementError(f"governed slide range mismatch for {cluster_id}")
        return row

    def workflow(self, row: sqlite3.Row | None = None) -> dict[str, str]:
        row = row or self.cluster()
        result = DEFAULT_WORKFLOW.copy()
        result.update(json_value(row["workflow_state"], {}))
        return result

    def _set_workflow(self, **updates: str) -> None:
        row = self.cluster()
        state = self.workflow(row)
        state.update(updates)
        self.connection.execute(
            "UPDATE lecture_knowledge_clusters SET workflow_state=?,updated_at=? WHERE id=?",
            (encoded(state), utc_now(), row["id"]),
        )

    def open_historical(self) -> None:
        with self.atomic():
            row = self.cluster()
            count = self.connection.execute(
                """SELECT COUNT(*) FROM historical_slides hs JOIN historical_decks hd ON hd.id=hs.deck_id
                WHERE hd.deck_id=? AND hs.historical_slide_number BETWEEN ? AND ?""",
                (row["historical_deck_id"], row["slide_start"], row["slide_end"]),
            ).fetchone()[0]
            if count != 16:
                raise ReinforcementError("KC01 requires all historical slides 3–18")
            self._set_workflow(historical="COMPLETE", cluster="READY")
            self.connection.execute(
                "UPDATE lecture_knowledge_clusters SET status='IN_PROGRESS',updated_at=? WHERE id=?",
                (utc_now(), row["id"]),
            )

    def select_cluster(self, cluster_id: str) -> None:
        with self.atomic():
            row = self.cluster(cluster_id)
            if cluster_id != "KC01" or not row["active"]:
                raise ReinforcementError("only KC01 is active in the current pilot")
            if self.workflow(row)["historical"] != "COMPLETE":
                raise ReinforcementError("open the historical lecture first")
            self._set_workflow(cluster="COMPLETE", resources="READY")

    @staticmethod
    def _use_level(historical_use: str, alignment: str) -> str:
        if alignment == "OUT_OF_DOMAIN":
            return "OUT_OF_DOMAIN"
        return {
            "EXTENSIVELY_USED": "EXTENSIVELY_USED",
            "PARTLY_USED_LINEAGE_UNCONFIRMED": "PARTIALLY_USED",
            "UNUSED_BUT_ALIGNED": "UNUSED_BUT_RELEVANT",
            "UNUSED": "UNRESOLVED",
        }.get(historical_use, "UNRESOLVED")

    def find_aligned_resources(self) -> int:
        with self.atomic():
            cluster = self.cluster()
            if self.workflow(cluster)["resources"] not in {"READY", "IN_PROGRESS", "RETURNED"}:
                raise ReinforcementError("resource alignment is locked")
            items = self.connection.execute(
                """SELECT hci.*,r.id resource_pk,r.title resource_title,r.source_locator,
                r.source_quality,r.factual_currency_status,r.verification_status resource_verification,
                r.source_type,r.file_type
                FROM historical_resource_cluster_items hci
                LEFT JOIN resources r ON r.resource_id=hci.source_identifier
                WHERE hci.cluster_id=(SELECT id FROM historical_resource_clusters
                WHERE cluster_id='SA-REGION-CLUSTER-001') ORDER BY hci.source_identifier"""
            ).fetchall()
            if not items:
                raise ReinforcementError("LEC_RES_1 has no indexed resource profiles")
            created = 0
            for item in items:
                if not str(item["source_identifier"]).startswith("IS529N-CENSUS-04"):
                    raise ReinforcementError("resource-group scope violation")
                matching = [3, 4, 17, 18] if item["source_identifier"] in {
                    "IS529N-CENSUS-0449", "IS529N-CENSUS-0450"
                } else []
                use_level = self._use_level(item["historical_use"], item["alignment"])
                cursor = self.connection.execute(
                    """INSERT OR IGNORE INTO cluster_resource_alignments(
                    alignment_id,cluster_id,resource_id,source_identifier,resource_group_id,title,
                    resource_type,symbolic_location,main_subjects,cluster_alignment,
                    matching_historical_slides,current_use_level,source_quality,currency_status,
                    maps_or_figures,relevant_pages_or_sections,recommended_use,verification_status,
                    generated_recommendation,created_at,updated_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        f"KC01-RES-{item['source_identifier'].rsplit('-', 1)[-1]}", cluster["id"],
                        item["resource_pk"], item["source_identifier"], "LEC_RES_1",
                        item["resource_title"] or item["filename"],
                        item["source_type"] or item["file_type"],
                        item["source_locator"] or "<HISTORICAL_RESOURCE_REPOSITORY>",
                        item["relevant_dimensions"], item["alignment"], encoded(matching),
                        use_level, item["source_quality"] or "UNASSESSED",
                        item["factual_currency_status"] or "UNVERIFIED", "REVIEW_REQUIRED",
                        "Inspect cited pages or sections before classroom use.", item["notes"],
                        item["resource_verification"] or item["verification_status"],
                        f"System profile only; instructor must decide whether this source serves {cluster['cluster_id']}.",
                        utc_now(), utc_now(),
                    ),
                )
                created += cursor.rowcount
            self._set_workflow(resources="COMPLETE", units="READY")
            return created

    def historical_decision(self, slide_id: str, action: str, comment: str = "") -> None:
        if action not in HISTORICAL_ACTIONS:
            raise ReinforcementError("invalid historical-slide action")
        with self.atomic():
            cluster = self.cluster()
            slide = self.connection.execute(
                """SELECT hs.historical_slide_id,hs.historical_slide_number FROM historical_slides hs
                JOIN historical_decks hd ON hd.id=hs.deck_id WHERE hs.historical_slide_id=?
                AND hd.deck_id=?""", (slide_id, cluster["historical_deck_id"]),
            ).fetchone()
            if slide is None or not (cluster["slide_start"] <= slide["historical_slide_number"] <= cluster["slide_end"]):
                raise ReinforcementError("historical slide is outside KC01")
            decisions = json_value(cluster["historical_slide_decisions"], {})
            decisions[slide_id] = {
                "decision": action, "comment": comment, "decided_at": utc_now(),
                "recorded_by": "Instructor", "state": "DECISION_RECORDED",
            }
            self.connection.execute(
                "UPDATE lecture_knowledge_clusters SET historical_slide_decisions=?,updated_at=? WHERE id=?",
                (encoded(decisions), utc_now(), cluster["id"]),
            )

    def _pilot_slide(self, slide_id: str = "L01-DECK-005-S003") -> sqlite3.Row:
        if slide_id != "L01-DECK-005-S003":
            raise ReinforcementError("the AI Update Packet pilot is limited to Historical Slide 3")
        cluster = self.cluster()
        slide = self.connection.execute(
            """SELECT hs.*,hd.deck_id FROM historical_slides hs
            JOIN historical_decks hd ON hd.id=hs.deck_id
            WHERE hs.historical_slide_id=? AND hd.deck_id=?""",
            (slide_id, cluster["historical_deck_id"]),
        ).fetchone()
        if slide is None or slide["historical_slide_number"] != 3:
            raise ReinforcementError("Historical Slide 3 is unavailable")
        return slide

    @staticmethod
    def _safe_symbolic_location(value: str | None) -> str:
        location = str(value or "").strip()
        if not location:
            return "<SOURCE_LOCATION_NOT_RECORDED>"
        if location.startswith("<"):
            return location
        if Path(location).is_absolute():
            return "<LOCAL_PROTECTED_SOURCE>"
        return location

    def _slide_update_corpora(self, slide: sqlite3.Row) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        cluster = self.cluster()
        alignments = self.resource_alignments(cluster["id"])
        if not alignments:
            alignments = []
            for row in self.connection.execute(
                """SELECT h.*,r.title resource_title,r.source_locator,r.source_quality,
                r.factual_currency_status,r.verification_status resource_verification
                FROM historical_resource_cluster_items h
                LEFT JOIN resources r ON r.resource_id=h.source_identifier
                WHERE h.cluster_id=(SELECT id FROM historical_resource_clusters
                WHERE cluster_id='SA-REGION-CLUSTER-001') ORDER BY h.source_identifier"""
            ):
                directly_matched = row["source_identifier"] in {
                    "IS529N-CENSUS-0449", "IS529N-CENSUS-0450"
                }
                alignments.append({
                    "source_identifier": row["source_identifier"],
                    "title": row["resource_title"] or row["filename"],
                    "author": "", "publication_year": "", "resource_type": row["source_type"],
                    "symbolic_location": self._safe_symbolic_location(row["source_locator"]),
                    "main_subjects": json_value(row["relevant_dimensions"], []),
                    "cluster_alignment": row["alignment"],
                    "matching_historical_slides": [3] if directly_matched else [],
                    "current_use_level": self._use_level(row["historical_use"], row["alignment"]),
                    "source_quality": row["source_quality"] or "UNASSESSED",
                    "currency_status": row["factual_currency_status"] or "UNVERIFIED",
                    "maps_or_figures": "NOT_YET_INDEXED",
                    "relevant_pages_or_sections": "NOT_YET_RECORDED",
                    "recommended_use": row["notes"],
                    "verification_status": row["resource_verification"] or row["verification_status"],
                })

        units_by_source: dict[str, list[dict[str, str]]] = {}
        for row in self.connection.execute(
            "SELECT * FROM knowledge_units WHERE cluster_id=? ORDER BY knowledge_unit_id",
            (cluster["id"],),
        ):
            if slide["historical_slide_id"] not in json_value(row["historical_slide_ids"], []):
                continue
            units_by_source.setdefault(row["source_identifier"], []).append({
                "knowledge_unit_id": row["knowledge_unit_id"],
                "unit_type": row["unit_type"],
                "pages": row["source_pages"],
                "text": row["unit_text"],
                "verification_status": row["verification_status"],
            })

        slide_corpus: list[dict[str, Any]] = []
        cluster_corpus: list[dict[str, Any]] = []
        for resource in alignments:
            identifier = resource["source_identifier"]
            related_units = units_by_source.get(identifier, [])
            passages = [unit for unit in related_units if unit["unit_type"] == "QUOTATION"]
            directly_matched = slide["historical_slide_number"] in resource.get("matching_historical_slides", [])
            item = {
                "resource_id": identifier,
                "title": resource["title"],
                "author": resource.get("author") or "NOT_RECORDED",
                "year": resource.get("publication_year") or "NOT_RECORDED",
                "resource_type": resource.get("resource_type") or "NOT_RECORDED",
                "symbolic_location": self._safe_symbolic_location(resource.get("symbolic_location")),
                "relevant_pages": resource.get("relevant_pages_or_sections") or "NOT_YET_RECORDED",
                "relevant_passages": passages,
                "related_knowledge_units": related_units,
                "maps_or_figures": resource.get("maps_or_figures") or "NOT_YET_INDEXED",
                "citation": resource["title"],
                "verification_status": resource.get("verification_status") or "NOT_STARTED",
                "source_quality": resource.get("source_quality") or "UNASSESSED",
                "relation_to_original_slide": (
                    "DIRECT_PROFILE_MATCH_REQUIRES_PAGE_VERIFICATION" if directly_matched
                    else "KC01_CONTEXT_ONLY"
                ),
                "cluster_alignment": resource.get("cluster_alignment") or "UNRESOLVED",
            }
            if directly_matched or related_units:
                slide_corpus.append(item)
            else:
                cluster_corpus.append({
                    "resource_id": identifier, "title": resource["title"],
                    "cluster_alignment": item["cluster_alignment"],
                    "relationship": "KC01_CONTEXT_ONLY",
                })
        return slide_corpus, cluster_corpus

    def prepare_ai_update_packet(self, slide_id: str, *, support_override: bool = False) -> dict[str, Any]:
        slide = self._pilot_slide(slide_id)
        cluster = self.cluster()
        decision = json_value(cluster["historical_slide_decisions"], {}).get(slide_id, {})
        action = decision.get("decision", "")
        if action not in AI_PACKET_ACTIONS and not (
            support_override and action in AI_SUPPORT_OVERRIDE_ACTIONS
        ):
            raise ReinforcementError(
                "record an AI-supported action or explicitly choose Prepare AI Support Anyway"
            )
        if not str(decision.get("comment", "")).strip():
            raise ReinforcementError("add a specific instructor intervention note before preparing the corpus")
        slide_corpus, cluster_corpus = self._slide_update_corpora(slide)
        neighbours = {}
        for row in self.connection.execute(
            """SELECT hs.historical_slide_number,hs.title,hs.text_extract
            FROM historical_slides hs JOIN historical_decks hd ON hd.id=hs.deck_id
            WHERE hd.deck_id=? AND hs.historical_slide_number IN (2,4)""",
            (cluster["historical_deck_id"],),
        ):
            neighbours[row["historical_slide_number"]] = {
                "title": row["title"], "text": row["text_extract"] or "",
            }
        selected = self.connection.execute(
            "SELECT * FROM knowledge_patterns WHERE pattern_id=? AND cluster_id=?",
            (cluster["selected_pattern_id"], cluster["id"]),
        ).fetchone() if cluster["selected_pattern_id"] else None
        cluster_proposition = selected["central_proposition"] if selected else cluster["thematic_function"]
        selected_pattern = selected["title"] if selected else "NOT_YET_SELECTED"
        warning_parts = [
            part for part in (slide["reason"], slide["page_status"], slide["confidence"])
            if part and part not in {"TEXT_EXTRACTED", "UNASSESSED"}
        ]
        warnings = "; ".join(warning_parts) or "No extraction warning recorded; source claims still require scholarly verification."

        source_sections = []
        for index, source in enumerate(slide_corpus, start=1):
            passages = source["relevant_passages"]
            passage_text = "\n".join(
                f"- {p['pages']}: {p['text']} [{p['verification_status']}]" for p in passages
            ) or "- No verified page-level passage is indexed. Do not infer claims from the source title."
            unit_text = "\n".join(
                f"- {unit['knowledge_unit_id']} ({unit['unit_type']}; {unit['pages']}): "
                f"{unit['text']} [{unit['verification_status']}]"
                for unit in source["related_knowledge_units"] if unit["unit_type"] != "QUOTATION"
            ) or "- No additional traceable knowledge unit is indexed for this slide and source."
            source_sections.append(
                f"### Source {index}\n"
                f"Resource ID: {source['resource_id']}\n"
                f"Title: {source['title']}\n"
                f"Author: {source['author']}\n"
                f"Year: {source['year']}\n"
                f"Relevant pages: {source['relevant_pages']}\n"
                f"Relevant passages:\n{passage_text}\n"
                f"Traceable knowledge units (not verbatim passages):\n{unit_text}\n"
                f"Maps or figures: {source['maps_or_figures']}\n"
                f"Citation: {source['citation']}\n"
                f"Verification status: {source['verification_status']}\n"
                f"Source quality: {source['source_quality']}\n"
                f"Relation to original slide: {source['relation_to_original_slide']}"
            )
        if not source_sections:
            source_sections.append(
                "No directly aligned page-level source is currently indexed for this slide. "
                "Treat every substantive claim as requiring verification and do not invent citations."
            )
        cluster_sources = "\n".join(
            f"- {item['resource_id']}: {item['title']} ({item['cluster_alignment']}; context only)"
            for item in cluster_corpus
        ) or "- No additional KC01 context profiles are currently indexed."
        schema = "\n".join(f"{field}:" for field in AI_UPDATE_REQUIRED_FIELDS)
        packet = f"""# IS529N Slide Reinforcement Packet

## Task

Update Historical Slide 3 for Lecture 1A while preserving the inherited academic argument and source lineage. This packet is evidence for an external scholarly drafting conversation; it grants no authority to accept or apply a revision.

## Slide identity

Course: IS529N
Lecture: L01A
Cluster: KC01
Historical slide: 3
Slide ID: {slide_id}
Title: {slide['title']}
Instructor decision: {action}

## Instructor direction

{decision.get('comment') or 'No additional direction recorded. Preserve the inherited argument, reduce density, verify claims, and coordinate with adjacent slides.'}

## Original slide content

Extracted title: {slide['title']}

Complete extracted text:

{slide['text_extract'] or '[No extracted text available]'}

Visible references:
{chr(10).join('- ' + line.strip() for line in (slide['text_extract'] or '').splitlines() if re.search(r'\b(source|references?|citation|et al\.|\d{{4}})\b', line, re.I)) or '- No visible reference extracted.'}

OCR or extraction warnings: {warnings}
Visual description: {('Contains extracted image content.' if slide['image_count'] else 'Text-led inherited slide; inspect thumbnail for layout and visual details.')}
Thumbnail reference: /lectures/IS529N-L01-A/reinforcement/historical/{slide_id}/thumbnail

## Slide corpus

Corpus type: SLIDE_SPECIFIC_CORPUS

{chr(10).join(source_sections)}

## Cluster corpus context

The following sources belong to the wider KC01 corpus and must not be treated as direct evidence for Slide 3 without page-level verification:

{cluster_sources}

## Lecture context

Previous slide: {neighbours.get(2, {}).get('title', 'Not available')} — {neighbours.get(2, {}).get('text', 'Not available')}

Following slide: {neighbours.get(4, {}).get('title', 'Not available')} — {neighbours.get(4, {}).get('text', 'Not available')}

Cluster proposition: {cluster_proposition}
Selected knowledge pattern: {selected_pattern}
Target teaching time: 90 seconds
Role in lecture: Opening conceptual frame; distinguish ontology from epistemology and lead into Slide 4 without repetition.

## Required operation

1. Distinguish ontology from epistemology.
2. Preserve source fidelity and historical lineage.
3. Remove unsupported assertions.
4. Reduce student-facing text.
5. Move detailed explanation into speaker notes.
6. Recommend an appropriate visual.
7. Provide exact source citations; do not fabricate missing page evidence.
8. Identify every unresolved claim.
9. Explain exact differences from the inherited slide in `revision_rationale`.

## Required output

Return valid YAML only, with every field in this schema:

```yaml
{schema}
```

`slide_id` must be `{slide_id}`. Use YAML lists for `source_citations`, `claims_verified`, `claims_requiring_verification`, and `material_moved_to_notes`. This output will be labelled `AI_ASSISTED_DRAFT` and `REQUIRES_INSTRUCTOR_REVIEW`; it will not be applied automatically.
"""
        with self.atomic():
            sequence = self.connection.execute(
                "SELECT COUNT(*) FROM slide_ai_update_packets WHERE cluster_id=? AND historical_slide_id=?",
                (cluster["id"], slide["id"]),
            ).fetchone()[0] + 1
            packet_id = f"KC01-S003-AIUP-{sequence:03d}"
            now = utc_now()
            self.connection.execute(
                """INSERT INTO slide_ai_update_packets(packet_id,cluster_id,historical_slide_id,
                historical_action,instructor_direction,corpus_type,packet_markdown,slide_corpus_json,
                cluster_context_json,status,lifecycle_state,prepared_at,updated_at)
                VALUES (?,?,?,?,?,'SLIDE_SPECIFIC_CORPUS',?,?,?,'PREPARED','CORPUS_READY',?,?)""",
                (packet_id, cluster["id"], slide["id"], action, decision.get("comment", ""),
                 packet, encoded(slide_corpus), encoded({"cluster_corpus": cluster_corpus,
                 "cluster_proposition": cluster_proposition, "selected_pattern": selected_pattern}),
                 now, now),
            )
        return self.ai_update_packet(packet_id)

    def ai_update_packet(self, packet_id: str) -> dict[str, Any]:
        cluster = self.cluster()
        row = self.connection.execute(
            """SELECT p.*,hs.historical_slide_id historical_slide_identifier,
            hs.historical_slide_number,hs.title historical_title,
            hs.text_extract historical_text FROM slide_ai_update_packets p
            JOIN historical_slides hs ON hs.id=p.historical_slide_id
            WHERE p.packet_id=? AND p.cluster_id=?""", (packet_id, cluster["id"]),
        ).fetchone()
        if row is None or row["historical_slide_identifier"] != "L01-DECK-005-S003":
            raise ReinforcementError("unknown Slide 3 AI Update Packet")
        result = dict(row)
        for field, default in (("slide_corpus_json", []), ("cluster_context_json", {}),
                               ("validated_result_json", {}), ("validation_errors_json", [])):
            result[field] = json_value(result[field], default)
        revision = None
        if result.get("active_revision_id"):
            revision_row = self.connection.execute(
                "SELECT * FROM slide_ai_update_revisions WHERE id=? AND packet_id=?",
                (result["active_revision_id"], result["id"]),
            ).fetchone()
            if revision_row:
                revision = dict(revision_row)
                for field, default in (("validated_result_json", {}),
                                       ("validation_errors_json", []),
                                       ("instructor_edit_json", {})):
                    revision[field] = json_value(revision[field], default)
        result["active_revision"] = revision
        result["comparison"] = self._slide_update_comparison(
            result["historical_text"],
            (revision or {}).get("instructor_edit_json")
            or (revision or {}).get("validated_result_json") or {},
        )
        return result

    def mark_ai_packet_copied(self, packet_id: str) -> None:
        packet = self.ai_update_packet(packet_id)
        if packet["lifecycle_state"] not in {"CORPUS_READY", "PACKET_COPIED"}:
            raise ReinforcementError("prepare the update corpus before copying the packet")
        now = utc_now()
        with self.atomic():
            self.connection.execute(
                """UPDATE slide_ai_update_packets SET lifecycle_state='PACKET_COPIED',
                packet_copied_at=?,updated_at=? WHERE id=?""", (now, now, packet["id"]),
            )

    def mark_ai_packet_sent(self, packet_id: str) -> None:
        packet = self.ai_update_packet(packet_id)
        if packet["lifecycle_state"] not in {"PACKET_COPIED", "SENT_TO_EXTERNAL_AI"}:
            raise ReinforcementError("copy the packet before marking it as sent")
        now = utc_now()
        with self.atomic():
            self.connection.execute(
                """UPDATE slide_ai_update_packets SET status='SENT_TO_AI',
                lifecycle_state='SENT_TO_EXTERNAL_AI',external_ai_status='SENT_MANUALLY',
                sent_at=?,updated_at=? WHERE id=?""",
                (now, now, packet["id"]),
            )

    def paste_ai_update_result(
        self, packet_id: str, result_text: str, *, free_form_override: bool = False
    ) -> str:
        packet = self.ai_update_packet(packet_id)
        if packet["lifecycle_state"] not in {
            "SENT_TO_EXTERNAL_AI", "AI_RESULT_INVALID", "RETURNED_FOR_REVISION",
        }:
            raise ReinforcementError("mark the copied packet as sent before pasting a revision")
        if not result_text.strip():
            raise ReinforcementError("paste a structured YAML result first")
        try:
            preview = self._yaml_payload(result_text)
        except yaml.YAMLError:
            preview = {}
        if not isinstance(preview, dict) and not free_form_override:
            raise ReinforcementError("free-form prose requires an explicit instructor override")
        now = utc_now()
        with self.atomic():
            sequence = self.connection.execute(
                "SELECT COUNT(*) FROM slide_ai_update_revisions WHERE packet_id=?",
                (packet["id"],),
            ).fetchone()[0] + 1
            revision_id = f"{packet_id}-REV-{sequence:03d}"
            cursor = self.connection.execute(
                """INSERT INTO slide_ai_update_revisions(revision_id,packet_id,sequence,
                raw_result_text,status,pasted_at,created_at,updated_at)
                VALUES (?,?,?,?,'AI_RESULT_PASTED',?,?,?)""",
                (revision_id, packet["id"], sequence, result_text, now, now, now),
            )
            self.connection.execute(
                """UPDATE slide_ai_update_packets SET ai_result_text=?,status='RESULT_PASTED',
                lifecycle_state='AI_RESULT_PASTED',active_revision_id=?,
                validated_result_json='{}',validation_errors_json='[]',result_pasted_at=?,
                validated_at='',instructor_ruling='NOT_YET_DECIDED',instructor_ruling_comment='',
                instructor_edit_status='NOT_STARTED',application_note='',applied_by='',applied_at='',
                slide_file_or_version_reference='',reinforced_slide_reference='',
                reinforced_slide_checksum='',attachment_storage_path='',attached_at='',
                unresolved_claims_disposition='NOT_RECORDED',final_slide_status='NOT_ACCEPTED',
                return_reason='',return_target='',decided_at='',updated_at=? WHERE id=?""",
                (result_text, cursor.lastrowid, now, now, packet["id"]),
            )
        return revision_id

    @staticmethod
    def _yaml_payload(text: str) -> Any:
        stripped = text.strip()
        if stripped.startswith("```"):
            lines = stripped.splitlines()
            if lines and lines[0].strip().lower() in {"```yaml", "```yml", "```"}:
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            stripped = "\n".join(lines)
        return yaml.safe_load(stripped)

    def validate_ai_update_result(self, packet_id: str) -> dict[str, Any]:
        packet = self.ai_update_packet(packet_id)
        revision = packet["active_revision"]
        if packet["lifecycle_state"] != "AI_RESULT_PASTED" or not revision:
            raise ReinforcementError("paste the AI result before validation")
        errors: list[str] = []
        try:
            payload = self._yaml_payload(revision["raw_result_text"])
        except yaml.YAMLError as exc:
            payload = None
            errors.append(f"invalid YAML: {exc}")
        if not isinstance(payload, dict):
            errors.append("result must be a YAML mapping")
            payload = {}
        missing = [field for field in AI_UPDATE_REQUIRED_FIELDS if field not in payload]
        if missing:
            errors.append("missing required fields: " + ", ".join(missing))
        if payload.get("slide_id") != packet["historical_slide_identifier"]:
            errors.append(f"slide_id must be {packet['historical_slide_identifier']}")
        for field in AI_UPDATE_LIST_FIELDS:
            if field in payload and not isinstance(payload[field], list):
                errors.append(f"{field} must be a YAML list")
        if isinstance(payload.get("source_citations"), list) and not payload["source_citations"]:
            errors.append("source_citations must contain at least one exact citation or an explicit unresolved citation entry")
        for field in AI_UPDATE_REQUIRED_FIELDS:
            if field in AI_UPDATE_LIST_FIELDS or field == "slide_id":
                continue
            if field in payload and (payload[field] is None or str(payload[field]).strip() == ""):
                errors.append(f"{field} must not be empty")
        allowed_sources = {
            str(source["resource_id"]): str(source["title"])
            for source in packet["slide_corpus_json"]
        }
        mentioned_ids = set(RESOURCE_IDENTIFIER_RE.findall(encoded(payload)))
        unknown_ids = sorted(mentioned_ids - set(allowed_sources))
        if unknown_ids:
            errors.append("unknown source IDs: " + ", ".join(unknown_ids))
        if isinstance(payload.get("source_citations"), list):
            for citation in payload["source_citations"]:
                citation_text = str(citation).casefold()
                if not any(
                    source_id.casefold() in citation_text or title.casefold() in citation_text
                    for source_id, title in allowed_sources.items()
                ):
                    errors.append(f"citation does not correspond to the packet source corpus: {citation}")
        claims_text = encoded(payload).casefold()
        forbidden_claims = {
            "approval claim": r"\b(approved|approval)\b",
            "classroom-ready claim": r"\bclassroom[- ]ready\b",
            "automatic overwrite request": r"\b(overwrite|apply automatically|automatically apply)\b",
        }
        for label, pattern in forbidden_claims.items():
            if re.search(pattern, claims_text):
                errors.append(f"result contains a forbidden {label}")
        now = utc_now()
        lifecycle = "AI_RESULT_VALIDATED" if not errors else "AI_RESULT_INVALID"
        revision_status = lifecycle
        with self.atomic():
            self.connection.execute(
                """UPDATE slide_ai_update_revisions SET validated_result_json=?,
                validation_errors_json=?,status=?,validated_at=?,updated_at=? WHERE id=?""",
                (encoded(payload) if not errors else "{}", encoded(errors),
                 revision_status, now, now, revision["id"]),
            )
            self.connection.execute(
                """UPDATE slide_ai_update_packets SET validated_result_json=?,
                validation_errors_json=?,status=?,lifecycle_state=?,validated_at=?,updated_at=?
                WHERE id=?""",
                (encoded(payload) if not errors else "{}", encoded(errors),
                 "VALIDATED" if not errors else "RESULT_PASTED", lifecycle,
                 now, now, packet["id"]),
            )
        return {"valid": not errors, "errors": errors, "result": payload if not errors else {}}

    @staticmethod
    def _slide_update_comparison(historical_text: str, proposal: dict[str, Any]) -> dict[str, list[str]]:
        visible = proposal.get("student_visible_content", [])
        proposed_text = " ".join(visible) if isinstance(visible, list) else str(visible)
        old_words = re.findall(r"[A-Za-z][A-Za-z'-]{3,}", historical_text or "")
        new_words = re.findall(r"[A-Za-z][A-Za-z'-]{3,}", proposed_text)
        old_fold = {word.casefold() for word in old_words}
        new_fold = {word.casefold() for word in new_words}
        retained = list(dict.fromkeys(word for word in new_words if word.casefold() in old_fold))[:24]
        added = list(dict.fromkeys(word for word in new_words if word.casefold() not in old_fold))[:24]
        removed = list(dict.fromkeys(word for word in old_words if word.casefold() not in new_fold))[:24]
        moved = proposal.get("material_moved_to_notes", [])
        verify = proposal.get("claims_requiring_verification", [])
        return {
            "retained": retained, "added": added, "removed": removed,
            "moved_to_notes": moved if isinstance(moved, list) else [str(moved)],
            "requires_verification": verify if isinstance(verify, list) else [str(verify)],
        }

    def open_instructor_editing(self, packet_id: str) -> None:
        packet = self.ai_update_packet(packet_id)
        revision = packet["active_revision"]
        if packet["lifecycle_state"] != "AI_RESULT_VALIDATED" or not revision:
            raise ReinforcementError("validate the AI-assisted revision before editing")
        now = utc_now()
        with self.atomic():
            self.connection.execute(
                """UPDATE slide_ai_update_revisions SET status='INSTRUCTOR_EDITING',
                instructor_edit_json=validated_result_json,editing_started_at=?,updated_at=? WHERE id=?""",
                (now, now, revision["id"]),
            )
            self.connection.execute(
                """UPDATE slide_ai_update_packets SET lifecycle_state='INSTRUCTOR_EDITING',
                instructor_edit_status='IN_PROGRESS',updated_at=? WHERE id=?""",
                (now, packet["id"]),
            )

    def save_instructor_edit(
        self, packet_id: str, edited: dict[str, Any], *, waive: bool = False
    ) -> None:
        packet = self.ai_update_packet(packet_id)
        revision = packet["active_revision"]
        if packet["lifecycle_state"] != "INSTRUCTOR_EDITING" or not revision:
            raise ReinforcementError("open the instructor editing view first")
        base = dict(revision["validated_result_json"])
        if waive:
            status, edit_status = "EDITING_EXPLICITLY_WAIVED", "EXPLICITLY_WAIVED"
        else:
            for field in (
                "updated_slide_title", "student_visible_content", "speaker_notes",
                "visual_recommendation", "source_citations", "relationship_to_previous_slide",
                "relationship_to_next_slide", "claims_requiring_verification",
            ):
                if field in edited:
                    base[field] = edited[field]
            if not str(base.get("updated_slide_title", "")).strip():
                raise ReinforcementError("the instructor-edited title must not be empty")
            status, edit_status = "INSTRUCTOR_EDITED", "COMPLETED"
        now = utc_now()
        with self.atomic():
            self.connection.execute(
                """UPDATE slide_ai_update_revisions SET status=?,instructor_edit_json=?,
                editing_completed_at=?,updated_at=? WHERE id=?""",
                (status, encoded(base), now, now, revision["id"]),
            )
            self.connection.execute(
                "UPDATE slide_ai_update_packets SET instructor_edit_status=?,updated_at=? WHERE id=?",
                (edit_status, now, packet["id"]),
            )

    def record_manual_application(
        self, packet_id: str, application_note: str, applied_by: str,
        slide_file_or_version_reference: str,
    ) -> None:
        packet = self.ai_update_packet(packet_id)
        if packet["lifecycle_state"] != "INSTRUCTOR_EDITING" or packet["instructor_edit_status"] not in {
            "COMPLETED", "EXPLICITLY_WAIVED",
        }:
            raise ReinforcementError("complete or explicitly waive instructor editing first")
        if not all(value.strip() for value in (
            application_note, applied_by, slide_file_or_version_reference,
        )):
            raise ReinforcementError("manual application note, instructor and slide reference are required")
        if Path(slide_file_or_version_reference).is_absolute():
            raise ReinforcementError("use a version label or symbolic reference, not an absolute path")
        now = utc_now()
        with self.atomic():
            self.connection.execute(
                """UPDATE slide_ai_update_packets SET lifecycle_state='MANUALLY_APPLIED',
                application_note=?,applied_by=?,applied_at=?,slide_file_or_version_reference=?,
                updated_at=? WHERE id=?""",
                (application_note, applied_by, now, slide_file_or_version_reference,
                 now, packet["id"]),
            )

    def attach_reinforced_slide(
        self, packet_id: str, *, reference: str = "", checksum: str = "",
        filename: str = "", content: bytes | None = None,
    ) -> dict[str, str]:
        packet = self.ai_update_packet(packet_id)
        if packet["lifecycle_state"] != "MANUALLY_APPLIED":
            raise ReinforcementError("record manual application before attaching the revised slide")
        storage_path = ""
        if content is not None and filename:
            if len(content) > 25 * 1024 * 1024:
                raise ReinforcementError("attachment exceeds the 25 MB local limit")
            suffix = Path(filename).suffix.lower()
            if suffix not in {".png", ".jpg", ".jpeg", ".pdf", ".pptx"}:
                raise ReinforcementError("attachment must be PNG, JPEG, PDF or PPTX")
            safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", Path(filename).name)
            digest = hashlib.sha256(content).hexdigest()
            relative = Path("gui/local_state/reinforcement_attachments") / packet_id / f"{digest[:12]}_{safe_name}"
            destination = (self.project_root / relative).resolve()
            allowed = (self.project_root / "gui/local_state/reinforcement_attachments").resolve()
            if allowed not in destination.parents:
                raise ReinforcementError("unsafe attachment destination")
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content)
            reference = f"<LOCAL_REINFORCEMENT_ATTACHMENTS>/{packet_id}/{destination.name}"
            checksum = digest
            storage_path = relative.as_posix()
        else:
            if not reference.startswith("<") or Path(reference).is_absolute():
                raise ReinforcementError("use a symbolic reinforced-slide reference")
            if not re.fullmatch(r"[a-fA-F0-9]{64}", checksum):
                raise ReinforcementError("a 64-character SHA-256 checksum is required for a reference")
            checksum = checksum.lower()
        now = utc_now()
        with self.atomic():
            self.connection.execute(
                """UPDATE slide_ai_update_packets SET lifecycle_state='REINFORCED_SLIDE_ATTACHED',
                reinforced_slide_reference=?,reinforced_slide_checksum=?,attachment_storage_path=?,
                attached_at=?,updated_at=? WHERE id=?""",
                (reference, checksum, storage_path, now, now, packet["id"]),
            )
        return {"reference": reference, "checksum": checksum}

    def reinforced_attachment_path(self, packet_id: str) -> Path | None:
        packet = self.ai_update_packet(packet_id)
        if not packet["attachment_storage_path"]:
            return None
        relative = validate_relative_path(packet["attachment_storage_path"])
        if not relative.startswith("gui/local_state/reinforcement_attachments/"):
            return None
        path = (self.project_root / relative).resolve()
        allowed = (self.project_root / "gui/local_state/reinforcement_attachments").resolve()
        if allowed not in path.parents or not path.is_file():
            return None
        return path

    def accept_reinforced_slide(self, packet_id: str, unresolved_disposition: str) -> None:
        packet = self.ai_update_packet(packet_id)
        revision = packet["active_revision"]
        if packet["lifecycle_state"] != "REINFORCED_SLIDE_ATTACHED":
            raise ReinforcementError("attach the manually revised slide before acceptance")
        if packet["instructor_edit_status"] not in {"COMPLETED", "EXPLICITLY_WAIVED"}:
            raise ReinforcementError("instructor editing is incomplete")
        if not packet["application_note"] or not packet["reinforced_slide_checksum"]:
            raise ReinforcementError("manual application or attachment evidence is incomplete")
        if not revision or revision["status"] not in {
            "INSTRUCTOR_EDITED", "EDITING_EXPLICITLY_WAIVED",
        }:
            raise ReinforcementError("the active revision is not instructor-controlled")
        if unresolved_disposition not in {"RESOLVED", "EXPLICITLY_DEFERRED"}:
            raise ReinforcementError("resolve or explicitly defer unresolved claims")
        now = utc_now()
        with self.atomic():
            self.connection.execute(
                "UPDATE slide_ai_update_revisions SET status='INSTRUCTOR_ACCEPTED',updated_at=? WHERE id=?",
                (now, revision["id"]),
            )
            self.connection.execute(
                """UPDATE slide_ai_update_packets SET lifecycle_state='INSTRUCTOR_ACCEPTED',
                unresolved_claims_disposition=?,final_slide_status=
                'INSTRUCTOR_ACCEPTED_REINFORCED_SLIDE',instructor_ruling='ACCEPT_REINFORCED_SLIDE',
                decided_at=?,updated_at=? WHERE id=?""",
                (unresolved_disposition, now, now, packet["id"]),
            )

    def return_ai_update_for_revision(
        self, packet_id: str, reason: str, target: str
    ) -> None:
        if target not in AI_RETURN_TARGETS:
            raise ReinforcementError("invalid return target")
        if not reason.strip():
            raise ReinforcementError("a return reason is required")
        packet = self.ai_update_packet(packet_id)
        revision = packet["active_revision"]
        if packet["lifecycle_state"] not in {
            "AI_RESULT_VALIDATED", "INSTRUCTOR_EDITING", "MANUALLY_APPLIED",
            "REINFORCED_SLIDE_ATTACHED",
        } or not revision:
            raise ReinforcementError("there is no reviewable proposal to return")
        now = utc_now()
        with self.atomic():
            self.connection.execute(
                """UPDATE slide_ai_update_revisions SET status='RETURNED_FOR_REVISION',
                return_reason=?,return_target=?,returned_at=?,updated_at=? WHERE id=?""",
                (reason, target, now, now, revision["id"]),
            )
            self.connection.execute(
                """UPDATE slide_ai_update_packets SET lifecycle_state='RETURNED_FOR_REVISION',
                status='RETURNED_FOR_REVISION',return_reason=?,return_target=?,
                instructor_ruling='RETURN_FOR_REVISION',instructor_ruling_comment=?,
                decided_at=?,updated_at=? WHERE id=?""",
                (reason, target, reason, now, now, packet["id"]),
            )

    def resource_action(self, alignment_id: str, action: str, comment: str = "") -> None:
        if action not in RESOURCE_ACTIONS:
            raise ReinforcementError("invalid resource action")
        use_level = {
            "MARK_AS_USED": "EXTENSIVELY_USED",
            "MARK_AS_UNDERUSED": "UNDERUSED",
            "MARK_AS_UNUSED_BUT_RELEVANT": "UNUSED_BUT_RELEVANT",
            "MARK_AS_OUT_OF_DOMAIN": "OUT_OF_DOMAIN",
        }.get(action)
        with self.atomic():
            cluster = self.cluster()
            row = self.connection.execute(
                "SELECT id FROM cluster_resource_alignments WHERE alignment_id=? AND cluster_id=?",
                (alignment_id, cluster["id"]),
            ).fetchone()
            if row is None:
                raise ReinforcementError("resource is outside LEC_RES_1/KC01")
            assignments = "instructor_action=?,instructor_comment=?,updated_at=?"
            values: list[Any] = [action, comment, utc_now()]
            if use_level:
                assignments += ",current_use_level=?"
                values.append(use_level)
            values.append(row["id"])
            self.connection.execute(
                f"UPDATE cluster_resource_alignments SET {assignments} WHERE id=?", values
            )

    @staticmethod
    def _unit_type(slide: sqlite3.Row) -> str:
        title = (slide["title"] or "").lower()
        if "map" in title or "geography" in title:
            return "MAP"
        if "source" in title or "account" in title or "india" in title:
            return "HISTORICAL_EPISODE"
        if slide["image_count"]:
            return "FIGURE"
        return "CONCEPT"

    def extract_knowledge_units(self) -> int:
        with self.atomic():
            cluster = self.cluster()
            if self.workflow(cluster)["units"] not in {"READY", "RETURNED"}:
                raise ReinforcementError("knowledge-unit extraction is locked")
            source = self.connection.execute(
                "SELECT id,resource_id,source_locator FROM resources WHERE resource_id='L01-CENSUS-005'"
            ).fetchone()
            if source is None:
                raise ReinforcementError("historical source lineage is unavailable")
            slides = self.connection.execute(
                """SELECT hs.* FROM historical_slides hs JOIN historical_decks hd ON hd.id=hs.deck_id
                WHERE hd.deck_id=? AND hs.historical_slide_number BETWEEN ? AND ?
                ORDER BY hs.historical_slide_number""",
                (cluster["historical_deck_id"], cluster["slide_start"], cluster["slide_end"]),
            ).fetchall()
            if len(slides) != 16:
                raise ReinforcementError("fixed KC01 range must contain 16 historical slides")
            created = 0
            for slide in slides:
                text = (slide["text_extract"] or slide["title"] or f"Historical slide {slide['historical_slide_number']}").strip()
                if not text:
                    text = f"Historical slide {slide['historical_slide_number']} requires inspection."
                cursor = self.connection.execute(
                    """INSERT OR IGNORE INTO knowledge_units(
                    knowledge_unit_id,cluster_id,resource_id,source_identifier,historical_slide_ids,
                    unit_type,unit_text,source_pages,source_location,verification_status,
                    alignment_score,temporal_scope,spatial_scope,pedagogical_value,
                    candidate_slide_role,instructor_status,origin,created_at,updated_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        f"KU-KC01-{slide['historical_slide_number']:03d}", cluster["id"], source["id"],
                        source["resource_id"], encoded([slide["historical_slide_id"]]),
                        self._unit_type(slide), text, f"Historical slide {slide['historical_slide_number']}",
                        source["source_locator"], "REQUIRES_INSTRUCTOR_REVIEW", 0.75, "HISTORICAL",
                        "South Asia", "Preserves inherited pedagogical memory for recomposition.",
                        "RETAIN_OR_RECOMPOSE", "NOT_YET_DECIDED", "SYSTEM_EXTRACTED",
                        utc_now(), utc_now(),
                    ),
                )
                created += cursor.rowcount
            self._set_workflow(units="REVIEW_REQUIRED", patterns="READY")
            return created

    def unit_action(self, unit_id: str, action: str) -> None:
        if action not in UNIT_ACTIONS:
            raise ReinforcementError("invalid knowledge-unit action")
        with self.atomic():
            cluster = self.cluster()
            cursor = self.connection.execute(
                """UPDATE knowledge_units SET instructor_status=?,updated_at=?
                WHERE knowledge_unit_id=? AND cluster_id=?""",
                (action, utc_now(), unit_id, cluster["id"]),
            )
            if cursor.rowcount != 1:
                raise ReinforcementError("unknown KC01 knowledge unit")

    def select_rotation(self, rotation: str) -> None:
        if rotation not in ROTATIONS:
            raise ReinforcementError("invalid analytical rotation")
        with self.atomic():
            cluster = self.cluster()
            if self.workflow(cluster)["patterns"] not in {"READY", "REVIEW_REQUIRED", "RETURNED"}:
                raise ReinforcementError("pattern generation is locked")
            self.connection.execute(
                "UPDATE lecture_knowledge_clusters SET selected_rotation=?,updated_at=? WHERE id=?",
                (rotation, utc_now(), cluster["id"]),
            )

    @staticmethod
    def _pattern_specs() -> list[dict[str, Any]]:
        return [
            {
                "id": "KC01-PATTERN-A", "title": "Successive geographical imaginations",
                "proposition": "South Asia has been repeatedly constituted through changing geographical imaginations rather than discovered as a fixed region.",
                "lenses": ["TEMPORAL", "SPATIAL", "EVIDENTIARY"],
                "sequence": ["Puranic geography", "Greek representations", "Arab and medieval accounts", "British cartography", "Modern territorial South Asia"],
                "retained": [3, 4, 7, 10, 12, 13, 14, 15, 16, 17, 18],
                "condensed": [5, 6, 8, 9, 11], "removed": [], "minutes": 20,
                "risks": ["Chronology may imply a falsely linear succession", "Claims require source-by-source verification"],
            },
            {
                "id": "KC01-PATTERN-B", "title": "Ways of knowing South Asia",
                "proposition": "Different knowledge practices produced different South Asian regions, each with its own authority, scale and exclusions.",
                "lenses": ["THEMATIC", "EVIDENTIARY", "PEDAGOGICAL"],
                "sequence": ["Sacred geography", "Travel and observation", "Scientific description", "Imperial survey", "Modern political mapping"],
                "retained": [3, 4, 7, 10, 13, 14, 15, 16, 17, 18],
                "condensed": [5, 6, 8, 9, 11, 12], "removed": [], "minutes": 20,
                "risks": ["Categories overlap historically", "Modern mapping requires a clear transition to territorial politics"],
            },
            {
                "id": "KC01-PATTERN-C", "title": "Region before borders",
                "proposition": "Routes, rivers, pilgrimage, trade and imperial formations connected South Asia before modern borders reorganised those relations.",
                "lenses": ["RELATIONAL", "SPATIAL", "TEMPORAL"],
                "sequence": ["Rivers", "Routes", "Pilgrimage", "Trade", "Empires", "Colonial boundaries"],
                "retained": [3, 4, 10, 12, 13, 14, 15, 16, 18],
                "condensed": [5, 6, 7, 8, 9, 11, 17], "removed": [], "minutes": 22,
                "risks": ["The inherited deck provides uneven direct evidence for flows", "Border formation needs explicit counter-evidence"],
            },
        ]

    def generate_patterns(self) -> int:
        with self.atomic():
            cluster = self.cluster()
            if self.workflow(cluster)["patterns"] not in {"READY", "REVIEW_REQUIRED", "RETURNED"}:
                raise ReinforcementError("pattern generation is locked")
            units = self.connection.execute(
                "SELECT id,knowledge_unit_id FROM knowledge_units WHERE cluster_id=? ORDER BY knowledge_unit_id",
                (cluster["id"],),
            ).fetchall()
            if not units:
                raise ReinforcementError("extract knowledge units first")
            source_basis = [r[0] for r in self.connection.execute(
                """SELECT source_identifier FROM cluster_resource_alignments WHERE cluster_id=?
                AND current_use_level!='OUT_OF_DOMAIN' ORDER BY source_identifier""", (cluster["id"],)
            )]
            created = 0
            for spec in self._pattern_specs():
                cursor = self.connection.execute(
                    """INSERT OR IGNORE INTO knowledge_patterns(
                    pattern_id,cluster_id,title,central_proposition,analytical_lenses,
                    historical_slides_retained,historical_slides_condensed,historical_slides_removed,
                    new_relationships,source_basis,counter_evidence,evidence_strength,teaching_value,
                    estimated_time,risks_or_limitations,sequence_json,status,origin,created_at,updated_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        spec["id"], cluster["id"], spec["title"], spec["proposition"],
                        encoded(spec["lenses"]), encoded(spec["retained"]), encoded(spec["condensed"]),
                        encoded(spec["removed"]), encoded(spec["sequence"]), encoded(source_basis),
                        encoded(["Historical representation is not equivalent to verified evidence"]),
                        "PROVISIONAL", "Offers a distinct route through inherited material without discarding its lineage.",
                        spec["minutes"], encoded(spec["risks"]), encoded(spec["sequence"]),
                        "REVIEW_REQUIRED", "SYSTEM_GENERATED_DRAFT", utc_now(), utc_now(),
                    ),
                )
                created += cursor.rowcount
                pattern = self.connection.execute(
                    "SELECT id FROM knowledge_patterns WHERE pattern_id=?", (spec["id"],)
                ).fetchone()
                for index, unit in enumerate(units, start=1):
                    self.connection.execute(
                        """INSERT OR IGNORE INTO knowledge_pattern_units(
                        pattern_id,knowledge_unit_id,sequence,relationship_note) VALUES (?,?,?,?)""",
                        (pattern["id"], unit["id"], index, "Candidate relationship; instructor review required."),
                    )
            self._set_workflow(patterns="REVIEW_REQUIRED", choice="READY")
            return created

    def pattern_action(
        self, pattern_id: str, action: str, *, other_pattern_id: str = "",
        value: str = "", comment: str = "",
    ) -> str:
        if action not in PATTERN_ACTIONS | {"CONFIRM_PATTERN", "EDIT_PROPOSITION", "CHANGE_SEQUENCE", "DEFER"}:
            raise ReinforcementError("invalid pattern action")
        with self.atomic():
            cluster = self.cluster()
            pattern = self.connection.execute(
                "SELECT * FROM knowledge_patterns WHERE pattern_id=? AND cluster_id=?",
                (pattern_id, cluster["id"]),
            ).fetchone()
            if pattern is None:
                raise ReinforcementError("unknown KC01 pattern")
            if action == "SELECT":
                self.connection.execute(
                    "UPDATE knowledge_patterns SET status='REVIEW_REQUIRED' WHERE cluster_id=? AND status='SELECTED'",
                    (cluster["id"],),
                )
                self.connection.execute(
                    "UPDATE knowledge_patterns SET status='SELECTED',instructor_comment=?,updated_at=?,updated_by='Instructor' WHERE id=?",
                    (comment, utc_now(), pattern["id"]),
                )
                self.connection.execute(
                    "UPDATE lecture_knowledge_clusters SET selected_pattern_id=?,updated_at=? WHERE id=?",
                    (pattern_id, utc_now(), cluster["id"]),
                )
                self._set_workflow(choice="REVIEW_REQUIRED")
            elif action == "CONFIRM_PATTERN":
                if cluster["selected_pattern_id"] != pattern_id or pattern["status"] != "SELECTED":
                    raise ReinforcementError("select this pattern before confirming it")
                self.connection.execute(
                    "UPDATE knowledge_patterns SET status='CONFIRMED',instructor_comment=?,updated_at=?,updated_by='Instructor' WHERE id=?",
                    (comment, utc_now(), pattern["id"]),
                )
                self._set_workflow(choice="COMPLETE", slides="READY")
            elif action == "REJECT":
                self.connection.execute(
                    "UPDATE knowledge_patterns SET status='REJECTED',instructor_comment=?,updated_at=?,updated_by='Instructor' WHERE id=?",
                    (comment, utc_now(), pattern["id"]),
                )
            elif action == "SAVE_FOR_LATER" or action == "DEFER":
                self.connection.execute(
                    "UPDATE knowledge_patterns SET status='SAVED_FOR_LATER',instructor_comment=?,updated_at=?,updated_by='Instructor' WHERE id=?",
                    (comment, utc_now(), pattern["id"]),
                )
            elif action == "REVISE":
                self.connection.execute(
                    "UPDATE knowledge_patterns SET status='RETURNED',instructor_comment=?,updated_at=?,updated_by='Instructor' WHERE id=?",
                    (comment, utc_now(), pattern["id"]),
                )
            elif action == "EDIT_PROPOSITION":
                if not value.strip():
                    raise ReinforcementError("replacement proposition is required")
                self.connection.execute(
                    "UPDATE knowledge_patterns SET central_proposition=?,status='RETURNED',updated_at=?,updated_by='Instructor' WHERE id=?",
                    (value.strip(), utc_now(), pattern["id"]),
                )
            elif action == "CHANGE_SEQUENCE":
                sequence = json.loads(value)
                if not isinstance(sequence, list) or not sequence or not all(isinstance(x, str) and x.strip() for x in sequence):
                    raise ReinforcementError("sequence must be a non-empty JSON list of labels")
                self.connection.execute(
                    "UPDATE knowledge_patterns SET sequence_json=?,status='RETURNED',updated_at=?,updated_by='Instructor' WHERE id=?",
                    (encoded(sequence), utc_now(), pattern["id"]),
                )
            elif action == "COMBINE":
                other = self.connection.execute(
                    "SELECT * FROM knowledge_patterns WHERE pattern_id=? AND cluster_id=?",
                    (other_pattern_id, cluster["id"]),
                ).fetchone()
                if other is None or other["id"] == pattern["id"]:
                    raise ReinforcementError("choose a different KC01 pattern to combine")
                combined_id = "KC01-PATTERN-COMBINED"
                sequence = list(dict.fromkeys(
                    json_value(pattern["sequence_json"], []) + json_value(other["sequence_json"], [])
                ))
                self.connection.execute(
                    """INSERT INTO knowledge_patterns(
                    pattern_id,cluster_id,title,central_proposition,analytical_lenses,
                    historical_slides_retained,historical_slides_condensed,historical_slides_removed,
                    new_relationships,source_basis,counter_evidence,evidence_strength,teaching_value,
                    estimated_time,risks_or_limitations,sequence_json,status,origin,instructor_comment,
                    created_at,updated_at,updated_by)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(pattern_id) DO UPDATE SET title=excluded.title,
                    central_proposition=excluded.central_proposition,sequence_json=excluded.sequence_json,
                    status='REVIEW_REQUIRED',updated_at=excluded.updated_at,updated_by='Instructor'""",
                    (
                        combined_id, cluster["id"], f"Combined: {pattern['title']} + {other['title']}",
                        value.strip() or f"Combined proposition: {pattern['central_proposition']} {other['central_proposition']}",
                        encoded(list(dict.fromkeys(json_value(pattern["analytical_lenses"], []) + json_value(other["analytical_lenses"], [])))),
                        encoded(list(dict.fromkeys(json_value(pattern["historical_slides_retained"], []) + json_value(other["historical_slides_retained"], [])))),
                        encoded(list(dict.fromkeys(json_value(pattern["historical_slides_condensed"], []) + json_value(other["historical_slides_condensed"], [])))),
                        "[]", encoded(sequence), encoded(list(dict.fromkeys(json_value(pattern["source_basis"], []) + json_value(other["source_basis"], [])))),
                        encoded(["Combined pattern requires fresh coherence and timing review"]), "PROVISIONAL",
                        "Instructor-requested combination of two candidate structures.",
                        max(pattern["estimated_time"], other["estimated_time"]),
                        encoded(["May exceed cluster time", "Requires explicit confirmation"]), encoded(sequence),
                        "REVIEW_REQUIRED", "INSTRUCTOR_COMBINED_DRAFT", comment, utc_now(), utc_now(), "Instructor",
                    ),
                )
                return combined_id
            return pattern_id

    def generate_reinforced_slides(self) -> int:
        with self.atomic():
            cluster = self.cluster()
            if self.workflow(cluster)["slides"] != "READY":
                raise ReinforcementError("reinforced-slide generation is locked")
            pattern = self.connection.execute(
                "SELECT * FROM knowledge_patterns WHERE pattern_id=? AND cluster_id=? AND status='CONFIRMED'",
                (cluster["selected_pattern_id"], cluster["id"]),
            ).fetchone()
            if pattern is None:
                raise ReinforcementError("confirm a pattern first")
            sequence = json_value(pattern["sequence_json"], [])
            retained = json_value(pattern["historical_slides_retained"], [])
            unit_ids = [r[0] for r in self.connection.execute(
                "SELECT knowledge_unit_id FROM knowledge_units WHERE cluster_id=? ORDER BY knowledge_unit_id",
                (cluster["id"],),
            )]
            resources = json_value(pattern["source_basis"], [])
            created = 0
            for index, title in enumerate(sequence, start=1):
                lineage = retained[(index - 1)::len(sequence)] or [cluster["slide_start"] + index - 1]
                historical_ids = [f"L01-DECK-005-S{number:03d}" for number in lineage]
                assigned_units = unit_ids[(index - 1)::len(sequence)]
                cursor = self.connection.execute(
                    """INSERT OR IGNORE INTO reinforced_slides(
                    reinforced_slide_id,cluster_id,pattern_id,sequence,title,central_proposition,
                    historical_slide_lineage,knowledge_units,resource_support,visual_recommendation,
                    speaker_cue,citation_footer,verification_status,estimated_time,transition_in,
                    transition_out,status,created_at,updated_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        f"KC01-RS-{index:02d}", cluster["id"], pattern["id"], index, title,
                        f"Use {title.lower()} to test the selected cluster proposition without severing historical lineage.",
                        encoded(historical_ids), encoded(assigned_units), encoded(resources),
                        "Use an inherited visual or a source-backed replacement; do not use a generic decorative image.",
                        f"Connect {title.lower()} to the cluster proposition and identify its evidentiary limit.",
                        f"Historical Lecture 1A slides {', '.join(str(n) for n in lineage)} · evidence review required",
                        "REQUIRES_INSTRUCTOR_REVIEW", max(90, round(pattern["estimated_time"] * 60 / len(sequence))),
                        "Link from the previous way of knowing South Asia.",
                        "Name the next relationship in the selected pattern.", "REVIEW_REQUIRED", utc_now(), utc_now(),
                    ),
                )
                created += cursor.rowcount
            self._set_workflow(slides="REVIEW_REQUIRED", rehearsal="LOCKED")
            return created

    def slide_action(self, slide_id: str, action: str, comment: str = "") -> None:
        if action not in SLIDE_ACTIONS:
            raise ReinforcementError("invalid reinforced-slide action")
        with self.atomic():
            cluster = self.cluster()
            cursor = self.connection.execute(
                """UPDATE reinforced_slides SET status=?,instructor_comment=?,updated_at=?
                WHERE reinforced_slide_id=? AND cluster_id=?""",
                (action, comment, utc_now(), slide_id, cluster["id"]),
            )
            if cursor.rowcount != 1:
                raise ReinforcementError("unknown reinforced slide")
            pending = self.connection.execute(
                "SELECT COUNT(*) FROM reinforced_slides WHERE cluster_id=? AND status='REVIEW_REQUIRED'",
                (cluster["id"],),
            ).fetchone()[0]
            if pending == 0:
                self._set_workflow(slides="COMPLETE", rehearsal="READY")

    def start_rehearsal(self) -> str:
        with self.atomic():
            cluster = self.cluster()
            if self.workflow(cluster)["rehearsal"] != "READY":
                raise ReinforcementError("rehearsal is locked until every proposed slide has a decision")
            number = self.connection.execute(
                "SELECT COUNT(*)+1 FROM cluster_rehearsals WHERE cluster_id=?", (cluster["id"],)
            ).fetchone()[0]
            rehearsal_id = f"KC01-REH-{number:03d}"
            timestamp = utc_now()
            self.connection.execute(
                """INSERT INTO cluster_rehearsals(rehearsal_id,cluster_id,status,started_at,
                target_seconds,created_at,updated_at) VALUES (?,?,'IN_PROGRESS',?,1200,?,?)""",
                (rehearsal_id, cluster["id"], timestamp, timestamp, timestamp),
            )
            self._set_workflow(rehearsal="IN_PROGRESS")
            self.rehearsal_event(rehearsal_id, "START")
            return rehearsal_id

    def rehearsal_event(
        self, rehearsal_id: str, event_type: str, *, slide_id: str = "",
        elapsed_seconds: int = 0, comment: str = "",
    ) -> None:
        if event_type not in REHEARSAL_EVENTS:
            raise ReinforcementError("invalid rehearsal event")
        if elapsed_seconds < 0:
            raise ReinforcementError("elapsed time cannot be negative")
        cluster = self.cluster()
        rehearsal = self.connection.execute(
            "SELECT * FROM cluster_rehearsals WHERE rehearsal_id=? AND cluster_id=?",
            (rehearsal_id, cluster["id"]),
        ).fetchone()
        if rehearsal is None:
            raise ReinforcementError("unknown KC01 rehearsal")
        slide_pk = None
        if slide_id:
            slide = self.connection.execute(
                "SELECT id FROM reinforced_slides WHERE reinforced_slide_id=? AND cluster_id=?",
                (slide_id, cluster["id"]),
            ).fetchone()
            if slide is None:
                raise ReinforcementError("rehearsal slide is outside KC01")
            slide_pk = slide["id"]
        event_number = self.connection.execute(
            "SELECT COUNT(*)+1 FROM cluster_rehearsal_events WHERE rehearsal_id=?", (rehearsal["id"],)
        ).fetchone()[0]
        self.connection.execute(
            """INSERT INTO cluster_rehearsal_events(event_id,rehearsal_id,reinforced_slide_id,
            event_type,elapsed_seconds,comment,occurred_at) VALUES (?,?,?,?,?,?,?)""",
            (f"{rehearsal_id}-E{event_number:03d}", rehearsal["id"], slide_pk,
             event_type, elapsed_seconds, comment, utc_now()),
        )
        total = self.connection.execute(
            "SELECT COALESCE(SUM(elapsed_seconds),0) FROM cluster_rehearsal_events WHERE rehearsal_id=?",
            (rehearsal["id"],),
        ).fetchone()[0]
        if event_type == "END_REHEARSAL":
            status = "COMPLETE"
            self._set_workflow(rehearsal="COMPLETE", acceptance="READY")
        elif event_type == "PAUSE":
            status = "PAUSED"
        elif event_type == "RESUME":
            status = "IN_PROGRESS"
        else:
            status = rehearsal["status"]
        merged_comment = rehearsal["instructor_comments"]
        if comment:
            merged_comment = (merged_comment + "\n" + comment).strip()
        self.connection.execute(
            """UPDATE cluster_rehearsals SET status=?,actual_seconds=?,instructor_comments=?,
            ended_at=?,updated_at=? WHERE id=?""",
            (status, total, merged_comment, utc_now() if status == "COMPLETE" else "",
             utc_now(), rehearsal["id"]),
        )

    def accept_cluster(self, action: str, comment: str = "") -> str:
        if action not in ACCEPTANCE_ACTIONS:
            raise ReinforcementError("invalid cluster-acceptance action")
        with self.atomic():
            cluster = self.cluster()
            pattern = self.connection.execute(
                "SELECT * FROM knowledge_patterns WHERE pattern_id=? AND status='CONFIRMED'",
                (cluster["selected_pattern_id"],),
            ).fetchone()
            rehearsal = self.connection.execute(
                "SELECT * FROM cluster_rehearsals WHERE cluster_id=? AND status='COMPLETE' ORDER BY id DESC LIMIT 1",
                (cluster["id"],),
            ).fetchone()
            if action == "ACCEPT_CLUSTER":
                if self.workflow(cluster)["acceptance"] != "READY" or pattern is None or rehearsal is None:
                    raise ReinforcementError("complete the confirmed-pattern rehearsal before acceptance")
                unresolved_units = self.connection.execute(
                    """SELECT COUNT(*) FROM knowledge_units WHERE cluster_id=?
                    AND instructor_status IN ('NOT_YET_DECIDED','MARK_FOR_VERIFICATION')""",
                    (cluster["id"],),
                ).fetchone()[0]
                unresolved_slides = self.connection.execute(
                    """SELECT COUNT(*) FROM reinforced_slides WHERE cluster_id=?
                    AND status NOT IN ('ACCEPT','MOVE_DETAIL_TO_NOTES')""",
                    (cluster["id"],),
                ).fetchone()[0]
                if unresolved_units or unresolved_slides:
                    raise ReinforcementError(
                        f"acceptance refused: {unresolved_units} unresolved knowledge units and "
                        f"{unresolved_slides} unresolved reinforced slides"
                    )
            if pattern is None or rehearsal is None:
                raise ReinforcementError("a confirmed pattern and completed rehearsal are required")
            summary = self.acceptance_summary(cluster["id"], rehearsal)
            number = self.connection.execute(
                "SELECT COUNT(*)+1 FROM cluster_acceptance_records WHERE cluster_id=?", (cluster["id"],)
            ).fetchone()[0]
            acceptance_id = f"KC01-ACC-{number:03d}"
            self.connection.execute(
                """INSERT INTO cluster_acceptance_records(acceptance_id,cluster_id,selected_pattern_id,
                rehearsal_id,ruling,summary_json,instructor_comment,decided_at)
                VALUES (?,?,?,?,?,?,?,?)""",
                (acceptance_id, cluster["id"], pattern["id"], rehearsal["id"], action,
                 encoded(summary), comment, utc_now()),
            )
            if action == "ACCEPT_CLUSTER":
                self.connection.execute(
                    "UPDATE lecture_knowledge_clusters SET status='ACCEPTED',updated_at=?,updated_by='Instructor' WHERE id=?",
                    (utc_now(), cluster["id"]),
                )
                self._set_workflow(acceptance="COMPLETE", build="LOCKED")
            else:
                stage = {
                    "RETURN_TO_SLIDES": "slides", "RETURN_TO_SOURCES": "resources",
                    "RETURN_TO_PATTERNS": "patterns", "DEFER": "acceptance",
                }[action]
                self.connection.execute(
                    "UPDATE lecture_knowledge_clusters SET status='RETURNED',updated_at=?,updated_by='Instructor' WHERE id=?",
                    (utc_now(), cluster["id"]),
                )
                self._set_workflow(**{stage: "RETURNED", "acceptance": "RETURNED"})
            return acceptance_id

    def acceptance_summary(self, cluster_pk: int, rehearsal: sqlite3.Row | None = None) -> dict[str, Any]:
        counts = {r["status"]: r["count"] for r in self.connection.execute(
            "SELECT status,COUNT(*) count FROM reinforced_slides WHERE cluster_id=? GROUP BY status",
            (cluster_pk,),
        )}
        rehearsal = rehearsal or self.connection.execute(
            "SELECT * FROM cluster_rehearsals WHERE cluster_id=? ORDER BY id DESC LIMIT 1", (cluster_pk,)
        ).fetchone()
        return {
            "slides_retained": counts.get("ACCEPT", 0),
            "slides_requiring_revision": counts.get("REVISE", 0) + counts.get("REQUEST_NEW_VISUAL", 0),
            "slides_removed": counts.get("DELETE", 0),
            "estimated_seconds": self.connection.execute(
                "SELECT COALESCE(SUM(estimated_time),0) FROM reinforced_slides WHERE cluster_id=?",
                (cluster_pk,),
            ).fetchone()[0],
            "actual_rehearsal_seconds": rehearsal["actual_seconds"] if rehearsal else 0,
            "evidence_gaps": self.connection.execute(
                "SELECT COUNT(*) FROM knowledge_units WHERE cluster_id=? AND instructor_status='MARK_FOR_VERIFICATION'",
                (cluster_pk,),
            ).fetchone()[0],
            "visual_problems": counts.get("REQUEST_NEW_VISUAL", 0),
            "sequence_problems": counts.get("MOVE", 0),
            "unresolved_claims": self.connection.execute(
                "SELECT COUNT(*) FROM knowledge_units WHERE cluster_id=? AND instructor_status='NOT_YET_DECIDED'",
                (cluster_pk,),
            ).fetchone()[0],
        }

    def export_analysis_prompt(self) -> str:
        cluster = self.cluster()
        slides = self.historical_slides(cluster)
        resources = self.resource_alignments(cluster["id"])
        payload = {
            "instruction": "Return JSON only. Generate knowledge-unit or pattern drafts; do not make instructor decisions.",
            "labels_required": ["AI_ASSISTED_DRAFT", "REQUIRES_INSTRUCTOR_REVIEW"],
            "cluster": {"cluster_id": cluster["cluster_id"], "title": cluster["title"], "slides": [s["number"] for s in slides]},
            "historical_slide_titles": [{"slide": s["number"], "title": s["title"]} for s in slides],
            "resource_profiles": [{"resource_id": r["source_identifier"], "title": r["title"], "alignment": r["cluster_alignment"]} for r in resources],
            "output_schema": {
                "knowledge_units": [{
                    "knowledge_unit_id": "AI-KU-001", "unit_type": "CLAIM", "unit_text": "...",
                    "source_identifier": "...", "source_pages": "...", "historical_slide_ids": ["..."],
                }],
                "patterns": [{"pattern_id": "AI-PATTERN-001", "title": "...", "central_proposition": "...", "sequence": ["..."]}],
            },
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)

    def import_ai_draft(self, text: str) -> dict[str, int]:
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ReinforcementError(f"invalid structured import: {exc}") from exc
        if not isinstance(payload, dict):
            raise ReinforcementError("structured import must be a JSON object")
        cluster = self.cluster()
        counts = {"knowledge_units": 0, "patterns": 0}
        with self.atomic():
            for unit in payload.get("knowledge_units", []):
                unit_type = unit.get("unit_type")
                if unit_type not in KNOWLEDGE_UNIT_TYPES:
                    raise ReinforcementError("imported knowledge-unit type is invalid")
                source = self.connection.execute(
                    "SELECT id,source_locator FROM resources WHERE resource_id=?", (unit.get("source_identifier"),)
                ).fetchone()
                if source is None or not unit.get("source_pages") or not unit.get("historical_slide_ids"):
                    raise ReinforcementError("imported knowledge unit lacks governed provenance")
                identifier = str(unit.get("knowledge_unit_id", ""))
                if not re.fullmatch(r"AI-KU-[A-Za-z0-9_-]+", identifier):
                    raise ReinforcementError("imported knowledge-unit ID must start AI-KU-")
                cursor = self.connection.execute(
                    """INSERT INTO knowledge_units(knowledge_unit_id,cluster_id,resource_id,
                    source_identifier,historical_slide_ids,unit_type,unit_text,source_pages,
                    source_location,verification_status,alignment_score,pedagogical_value,
                    candidate_slide_role,instructor_status,origin,created_at,updated_at)
                    VALUES (?,?,?,?,?,?,?,?,?,'REQUIRES_INSTRUCTOR_REVIEW',0.5,?,?,'NOT_YET_DECIDED',
                    'AI_ASSISTED_DRAFT',?,?)""",
                    (identifier, cluster["id"], source["id"], unit["source_identifier"],
                     encoded(unit["historical_slide_ids"]), unit_type, str(unit.get("unit_text", "")).strip(),
                     str(unit["source_pages"]), source["source_locator"],
                     "Imported draft; instructor review required.", "REVIEW_CANDIDATE", utc_now(), utc_now()),
                )
                counts["knowledge_units"] += cursor.rowcount
            for pattern in payload.get("patterns", []):
                identifier = str(pattern.get("pattern_id", ""))
                sequence = pattern.get("sequence")
                if not re.fullmatch(r"AI-PATTERN-[A-Za-z0-9_-]+", identifier):
                    raise ReinforcementError("imported pattern ID must start AI-PATTERN-")
                if not isinstance(sequence, list) or not sequence:
                    raise ReinforcementError("imported pattern requires a sequence")
                cursor = self.connection.execute(
                    """INSERT INTO knowledge_patterns(pattern_id,cluster_id,title,central_proposition,
                    analytical_lenses,new_relationships,source_basis,counter_evidence,evidence_strength,
                    teaching_value,estimated_time,risks_or_limitations,sequence_json,status,origin,
                    created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,'REVIEW_REQUIRED',
                    'AI_ASSISTED_DRAFT',?,?)""",
                    (identifier, cluster["id"], str(pattern.get("title", "Imported pattern")),
                     str(pattern.get("central_proposition", "")).strip(), encoded(pattern.get("analytical_lenses", [])),
                     encoded(sequence), encoded(pattern.get("source_basis", [])),
                     encoded(pattern.get("counter_evidence", [])), "PROVISIONAL",
                     "Imported draft; instructor selection required.", int(pattern.get("estimated_time", 0)),
                     encoded(pattern.get("risks_or_limitations", ["AI-assisted draft"])), encoded(sequence),
                     utc_now(), utc_now()),
                )
                counts["patterns"] += cursor.rowcount
        return counts

    def historical_slides(self, cluster: sqlite3.Row | None = None) -> list[dict[str, Any]]:
        cluster = cluster or self.cluster()
        decisions = json_value(cluster["historical_slide_decisions"], {})
        packets: dict[int, dict[str, Any]] = {}
        for packet_row in self.connection.execute(
            """SELECT p.*,hs.historical_slide_number FROM slide_ai_update_packets p
            JOIN historical_slides hs ON hs.id=p.historical_slide_id
            WHERE p.cluster_id=? ORDER BY p.id DESC""", (cluster["id"],),
        ):
            number = packet_row["historical_slide_number"]
            if number in packets:
                continue
            packets[number] = self.ai_update_packet(packet_row["packet_id"])
        result = []
        for row in self.connection.execute(
            """SELECT hs.* FROM historical_slides hs JOIN historical_decks hd ON hd.id=hs.deck_id
            WHERE hd.deck_id=? AND hs.historical_slide_number BETWEEN ? AND ?
            ORDER BY hs.historical_slide_number""",
            (cluster["historical_deck_id"], cluster["slide_start"], cluster["slide_end"]),
        ):
            visual = "DATA_TABLE" if row["table_count"] else "FIGURE" if row["image_count"] else "TEXT"
            references = [line.strip() for line in (row["text_extract"] or "").splitlines()
                          if re.search(r"\b(source|references?|citation|et al\.|\d{4})\b", line, re.I)]
            decision = decisions.get(row["historical_slide_id"], {})
            packet = packets.get(row["historical_slide_number"])
            lifecycle = packet["lifecycle_state"] if packet else (
                "DECISION_RECORDED" if decision else "UNREVIEWED"
            )
            result.append({
                "id": row["historical_slide_id"], "number": row["historical_slide_number"],
                "title": row["title"] or f"Historical slide {row['historical_slide_number']}",
                "text": row["text_extract"] or "No extracted text; inspect the thumbnail.",
                "references": references[:5], "visual_type": visual,
                "status": row["current_status"], "relationship": "CORE_KC01_LINEAGE",
                "decision": decision,
                "ai_packet_eligible": row["historical_slide_number"] == 3
                and decision.get("decision") in AI_PACKET_ACTIONS,
                "ai_support_override_eligible": row["historical_slide_number"] == 3
                and decision.get("decision") in AI_SUPPORT_OVERRIDE_ACTIONS,
                "slide_reinforcement_state": lifecycle,
                "ai_packet": packet,
                "thumbnail_available": self.thumbnail_path(row["historical_slide_id"]) is not None,
            })
        return result

    def thumbnail_path(self, slide_id: str) -> Path | None:
        row = self.connection.execute(
            "SELECT visual_preview FROM historical_slides WHERE historical_slide_id=?", (slide_id,)
        ).fetchone()
        if row is None or not row["visual_preview"]:
            return None
        relative = validate_relative_path(row["visual_preview"])
        if not relative.startswith("qt_gui/local_state/historical_derivatives/"):
            return None
        path = (self.project_root / relative).resolve()
        allowed = (self.project_root / "qt_gui/local_state/historical_derivatives").resolve()
        if allowed not in path.parents or not path.is_file():
            return None
        return path

    def resource_alignments(self, cluster_pk: int) -> list[dict[str, Any]]:
        rows = [dict(r) for r in self.connection.execute(
            "SELECT * FROM cluster_resource_alignments WHERE cluster_id=? AND resource_group_id='LEC_RES_1' ORDER BY source_identifier",
            (cluster_pk,),
        )]
        for row in rows:
            for field in ("main_subjects", "matching_historical_slides"):
                row[field] = json_value(row[field], [])
        return rows

    def workspace(self, stage: str = "overview") -> dict[str, Any]:
        cluster = self.cluster()
        clusters = [dict(r) for r in self.connection.execute(
            "SELECT * FROM lecture_knowledge_clusters WHERE lecture_pair_id=? AND part='A' ORDER BY slide_start",
            (cluster["lecture_pair_id"],),
        )]
        resources = self.resource_alignments(cluster["id"])
        units = [dict(r) for r in self.connection.execute(
            "SELECT * FROM knowledge_units WHERE cluster_id=? ORDER BY knowledge_unit_id", (cluster["id"],)
        )]
        for unit in units:
            unit["historical_slide_ids"] = json_value(unit["historical_slide_ids"], [])
        patterns = [dict(r) for r in self.connection.execute(
            "SELECT * FROM knowledge_patterns WHERE cluster_id=? ORDER BY pattern_id", (cluster["id"],)
        )]
        for pattern in patterns:
            for field in ("analytical_lenses", "historical_slides_retained", "historical_slides_condensed",
                          "historical_slides_removed", "new_relationships", "source_basis", "counter_evidence",
                          "risks_or_limitations", "sequence_json"):
                pattern[field] = json_value(pattern[field], [])
        slides = [dict(r) for r in self.connection.execute(
            "SELECT * FROM reinforced_slides WHERE cluster_id=? ORDER BY sequence", (cluster["id"],)
        )]
        historical_by_id = {s["id"]: s for s in self.historical_slides(cluster)}
        for slide in slides:
            for field in ("historical_slide_lineage", "knowledge_units", "resource_support"):
                slide[field] = json_value(slide[field], [])
            slide["historical"] = [historical_by_id[x] for x in slide["historical_slide_lineage"] if x in historical_by_id]
        rehearsal = self.connection.execute(
            "SELECT * FROM cluster_rehearsals WHERE cluster_id=? ORDER BY id DESC LIMIT 1", (cluster["id"],)
        ).fetchone()
        accepted = self.connection.execute(
            "SELECT COUNT(*) FROM lecture_knowledge_clusters WHERE lecture_pair_id=? AND part='A' AND status='ACCEPTED'",
            (cluster["lecture_pair_id"],),
        ).fetchone()[0]
        workflow = self.workflow(cluster)
        return {
            "stage": stage, "cluster": dict(cluster), "clusters": clusters,
            "workflow": workflow, "historical_slides": list(historical_by_id.values()),
            "resources": resources, "units": units, "patterns": patterns, "reinforced_slides": slides,
            "rehearsal": dict(rehearsal) if rehearsal else None,
            "acceptance_summary": self.acceptance_summary(cluster["id"], rehearsal),
            "decision_queue": self.decision_queue(cluster["id"]),
            "counts": {
                "knowledge_units": len(units), "patterns": len(patterns),
                "reinforced_slides": len(slides), "accepted_clusters": accepted,
            },
            "build_locked": accepted < 6,
        }

    def decision_queue(self, cluster_pk: int) -> list[str]:
        queue: list[str] = []
        packet_row = self.connection.execute(
            "SELECT packet_id FROM slide_ai_update_packets WHERE cluster_id=? ORDER BY id DESC LIMIT 1",
            (cluster_pk,),
        ).fetchone()
        if packet_row:
            packet = self.ai_update_packet(packet_row["packet_id"])
            state = packet["lifecycle_state"]
            revision = packet["active_revision"] or {}
            edited = revision.get("instructor_edit_json") or revision.get("validated_result_json") or {}
            unresolved = edited.get("claims_requiring_verification", [])
            if state == "SENT_TO_EXTERNAL_AI":
                queue.append("Slide 3: Paste the externally prepared AI-assisted revision")
            elif state == "AI_RESULT_INVALID":
                queue.append("Slide 3: Correct the invalid structured revision")
            elif state == "AI_RESULT_VALIDATED":
                queue.append("Slide 3: Review the AI-assisted revision")
            elif state == "INSTRUCTOR_EDITING":
                if packet["instructor_edit_status"] == "IN_PROGRESS":
                    queue.append("Slide 3: Complete or explicitly waive instructor editing")
                else:
                    queue.append("Slide 3: Record manual application")
            elif state == "MANUALLY_APPLIED":
                queue.append("Slide 3: Attach the revised slide")
            elif state == "REINFORCED_SLIDE_ATTACHED":
                if unresolved:
                    queue.append(f"Slide 3: Resolve or defer {len(unresolved)} unverified claim(s)")
                queue.append("Slide 3: Accept or return the reinforced slide")
            elif state == "RETURNED_FOR_REVISION":
                queue.append(f"Slide 3: Revise the returned {packet['return_target'].lower().replace('_', ' ')}")
        patterns = self.connection.execute(
            "SELECT COUNT(*) FROM knowledge_patterns WHERE cluster_id=?", (cluster_pk,)
        ).fetchone()[0]
        selected = self.connection.execute(
            "SELECT selected_pattern_id FROM lecture_knowledge_clusters WHERE id=?", (cluster_pk,)
        ).fetchone()[0]
        if patterns and not selected:
            queue.append("KC01: Select one knowledge pattern")
        for row in self.connection.execute(
            """SELECT source_identifier FROM cluster_resource_alignments WHERE cluster_id=?
            AND instructor_action IN ('NOT_YET_DECIDED','REQUEST_DEEPER_ANALYSIS') LIMIT 4""", (cluster_pk,)
        ):
            queue.append(f"Resource {row['source_identifier']}: decide its KC01 use")
        unresolved = self.connection.execute(
            "SELECT COUNT(*) FROM knowledge_units WHERE cluster_id=? AND instructor_status='MARK_FOR_VERIFICATION'",
            (cluster_pk,),
        ).fetchone()[0]
        if unresolved:
            queue.append(f"KC01: {unresolved} knowledge unit(s) require verification")
        revision = self.connection.execute(
            "SELECT COUNT(*) FROM reinforced_slides WHERE cluster_id=? AND status='REVISE'", (cluster_pk,)
        ).fetchone()[0]
        if revision:
            queue.append(f"KC01: {revision} reinforced slide(s) require revision")
        rehearsal = self.connection.execute(
            "SELECT actual_seconds,target_seconds FROM cluster_rehearsals WHERE cluster_id=? ORDER BY id DESC LIMIT 1",
            (cluster_pk,),
        ).fetchone()
        if rehearsal and rehearsal["actual_seconds"] > rehearsal["target_seconds"]:
            queue.append(
                f"Cluster timing: {round(rehearsal['actual_seconds']/60)} minutes; target {round(rehearsal['target_seconds']/60)} minutes"
            )
        return queue
