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

from gui.reinforcement_service import RESOURCE_IDENTIFIER_RE, ReinforcementError


UNIT_TYPES = {"SINGLE_SLIDE", "SLIDE_PAIR", "SMALL_CLUSTER"}
SOURCE_MODES = {"REPOSITORY", "DIRECT_LOCAL", "MIXED", "GOVERNED"}
EDITABLE_STATUSES = {"AI_VALIDATED", "INSTRUCTOR_REVIEWED", "RETURNED"}
TEXT_SUFFIXES = {".txt", ".md", ".csv", ".json", ".jsonl", ".yaml", ".yml"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def encoded(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def decoded(value: str | None, default: Any) -> Any:
    try:
        return json.loads(value or "")
    except (TypeError, json.JSONDecodeError):
        return default


class LeanRevisionService:
    """Small, non-destructive revision path over the historical slide/source tables."""

    def __init__(self, connection: sqlite3.Connection, project_root: Path):
        self.connection = connection
        self.project_root = project_root.resolve()

    @contextmanager
    def atomic(self) -> Iterator[None]:
        self.connection.execute("SAVEPOINT lean_revision_action")
        try:
            yield
        except Exception:
            self.connection.execute("ROLLBACK TO lean_revision_action")
            self.connection.execute("RELEASE lean_revision_action")
            raise
        else:
            self.connection.execute("RELEASE lean_revision_action")

    def _cluster(self) -> sqlite3.Row:
        row = self.connection.execute(
            "SELECT * FROM lecture_knowledge_clusters WHERE cluster_id='KC01' AND part='A'"
        ).fetchone()
        if row is None:
            raise ReinforcementError("KC01 is unavailable")
        return row

    def slides(self) -> list[dict[str, Any]]:
        cluster = self._cluster()
        rows = self.connection.execute(
            """SELECT hs.* FROM historical_slides hs
            JOIN historical_decks hd ON hd.id=hs.deck_id
            WHERE hd.deck_id=? AND hs.historical_slide_number BETWEEN ? AND ?
            ORDER BY hs.historical_slide_number""",
            (cluster["historical_deck_id"], cluster["slide_start"], cluster["slide_end"]),
        )
        return [dict(row) for row in rows]

    def repository_sources(self) -> list[dict[str, Any]]:
        cluster = self._cluster()
        rows = [dict(row) for row in self.connection.execute(
            """SELECT a.source_identifier,a.title,a.author,a.publication_year,
            a.relevant_pages_or_sections,a.verification_status,a.symbolic_location,
            a.matching_historical_slides
            FROM cluster_resource_alignments a
            WHERE a.cluster_id=? ORDER BY
            CASE WHEN a.source_identifier LIKE 'IS529N-ALI-%' THEN 0
                 WHEN a.source_identifier LIKE 'IS529N-VALDIYA-%' THEN 1 ELSE 2 END,
            a.source_identifier""",
            (cluster["id"],),
        )]
        for row in rows:
            row["matching_historical_slides"] = decoded(row["matching_historical_slides"], [])
            row["passages"] = [dict(unit) for unit in self.connection.execute(
                """SELECT knowledge_unit_id,unit_type,unit_text,source_pages,verification_status,
                historical_slide_ids
                FROM knowledge_units WHERE cluster_id=? AND source_identifier=?
                ORDER BY knowledge_unit_id""",
                (cluster["id"], row["source_identifier"]),
            )]
            for passage in row["passages"]:
                passage["historical_slide_ids"] = decoded(passage["historical_slide_ids"], [])
        return rows

    @staticmethod
    def _normalise_slide_ids(unit_type: str, slide_ids: list[str]) -> list[str]:
        if unit_type not in UNIT_TYPES:
            raise ReinforcementError("choose a supported revision unit")
        result = list(dict.fromkeys(value.strip() for value in slide_ids if value.strip()))
        expected = {"SINGLE_SLIDE": (1, 1), "SLIDE_PAIR": (2, 2), "SMALL_CLUSTER": (2, 4)}[unit_type]
        if not expected[0] <= len(result) <= expected[1]:
            raise ReinforcementError(
                f"{unit_type.replace('_', ' ').title()} requires {expected[0]}"
                + (f"–{expected[1]}" if expected[0] != expected[1] else "") + " slides"
            )
        if any(not re.fullmatch(r"L01-DECK-005-S0(?:0[3-9]|1[0-8])", value) for value in result):
            raise ReinforcementError("revision units are limited to KC01 historical slides 3–18")
        numbers = [int(value.rsplit("S", 1)[-1]) for value in result]
        if numbers != sorted(numbers) or any(b != a + 1 for a, b in zip(numbers, numbers[1:])):
            raise ReinforcementError("pair and small-cluster slides must be consecutive and ordered")
        return result

    def _direct_sources(self, text: str) -> list[dict[str, str]]:
        sources: list[dict[str, str]] = []
        for line_number, line in enumerate(text.splitlines(), start=1):
            if not line.strip():
                continue
            parts = [part.strip() for part in line.split("|", 2)]
            path = Path(parts[0]).expanduser().resolve()
            if not path.is_file():
                raise ReinforcementError(f"direct source line {line_number} is not a readable file: {parts[0]}")
            pages = parts[1] if len(parts) > 1 else "Page reference not supplied"
            excerpt = parts[2] if len(parts) > 2 else ""
            if not excerpt and path.suffix.lower() in TEXT_SUFFIXES:
                excerpt = path.read_text(encoding="utf-8", errors="replace")[:4000].strip()
            sources.append({
                "source_id": f"LOCAL-{hashlib.sha256(str(path).encode()).hexdigest()[:12].upper()}",
                "title": path.name,
                "path": str(path),
                "pages": pages,
                "excerpt": excerpt or "No text excerpt supplied; inspect the authoritative local file.",
                "verification_status": "LOCALLY_SUPPLIED_NOT_REGISTERED",
            })
        return sources

    def save_draft(
        self, *, unit_type: str, slide_ids: list[str], instructor_query: str,
        source_mode: str, selected_source_ids: list[str], direct_source_text: str,
    ) -> dict[str, Any]:
        slides = self._normalise_slide_ids(unit_type, slide_ids)
        query = instructor_query.strip()
        if not query:
            raise ReinforcementError("enter an instructor query")
        if source_mode not in SOURCE_MODES:
            raise ReinforcementError("choose a supported source mode")
        available = {row["source_identifier"] for row in self.repository_sources()}
        selected = list(dict.fromkeys(value for value in selected_source_ids if value in available))
        direct = self._direct_sources(direct_source_text)
        if source_mode in {"REPOSITORY", "GOVERNED"} and not selected:
            raise ReinforcementError("select at least one repository source")
        if source_mode == "DIRECT_LOCAL" and not direct:
            raise ReinforcementError("supply at least one direct local source")
        if source_mode == "MIXED" and (not selected or not direct):
            raise ReinforcementError("mixed mode requires repository and direct local sources")
        cluster = self._cluster()
        now = utc_now()
        with self.atomic():
            sequence = self.connection.execute("SELECT COUNT(*)+1 FROM lean_revision_units").fetchone()[0]
            unit_id = f"LR-KC01-{sequence:03d}"
            cursor = self.connection.execute(
                """INSERT INTO lean_revision_units(
                unit_id,cluster_id,unit_type,slide_ids_json,instructor_query,source_mode,
                selected_sources_json,direct_sources_json,status,created_at,updated_at)
                VALUES (?,?,?,?,?,?,?,?,'DRAFT',?,?)""",
                (unit_id, cluster["id"], unit_type, encoded(slides), query, source_mode,
                 encoded(selected), encoded(direct), now, now),
            )
        return self.unit(cursor.lastrowid)

    def unit(self, identifier: int | str) -> dict[str, Any]:
        column = "id" if isinstance(identifier, int) or str(identifier).isdigit() else "unit_id"
        row = self.connection.execute(
            f"SELECT * FROM lean_revision_units WHERE {column}=?", (identifier,)
        ).fetchone()
        if row is None:
            raise ReinforcementError("unknown lean revision unit")
        result = dict(row)
        for field, default in (
            ("slide_ids_json", []), ("selected_sources_json", []), ("direct_sources_json", []),
            ("validated_result_json", {}), ("validation_errors_json", []),
            ("validation_warnings_json", []), ("instructor_edit_json", {}),
            ("accepted_record_json", {}),
        ):
            result[field] = decoded(result[field], default)
        result["proposal"] = result["instructor_edit_json"] or result["validated_result_json"]
        result["artefacts"] = [dict(row) for row in self.connection.execute(
            "SELECT * FROM lean_revision_artefacts WHERE revision_unit_id=? ORDER BY id", (result["id"],)
        )]
        result["presentation_state"] = "ACCEPTED" if result["status"] == "CONTENT_ACCEPTED" else result["status"]
        result["artefact_status"] = "ARTEFACT_ATTACHED" if result["artefacts"] else "NOT_ATTACHED"
        return result

    def _selected_source_records(self, unit: dict[str, Any]) -> list[dict[str, Any]]:
        wanted = set(unit["selected_sources_json"])
        records = []
        for source in self.repository_sources():
            if source["source_identifier"] not in wanted:
                continue
            passages = [
                passage for passage in source["passages"]
                if passage["verification_status"] == "VERIFIED"
                and set(passage["historical_slide_ids"]) & set(unit["slide_ids_json"])
            ]
            records.append({
                "source_id": source["source_identifier"], "title": source["title"],
                "pages": source["relevant_pages_or_sections"], "verification_status": source["verification_status"],
                "passages": passages,
            })
        return records + unit["direct_sources_json"]

    def prepare_packet(self, unit_id: str) -> dict[str, Any]:
        unit = self.unit(unit_id)
        if unit["status"] not in {"DRAFT", "RETURNED", "AI_PREPARED"}:
            raise ReinforcementError("this revision is already beyond packet preparation")
        slide_map = {slide["historical_slide_id"]: slide for slide in self.slides()}
        selected_slides = [slide_map[value] for value in unit["slide_ids_json"]]
        context_numbers = {slide["historical_slide_number"] - 1 for slide in selected_slides}
        context_numbers.update(slide["historical_slide_number"] + 1 for slide in selected_slides)
        selected_numbers = {slide["historical_slide_number"] for slide in selected_slides}
        context = [slide for slide in self.slides()
                   if slide["historical_slide_number"] in context_numbers - selected_numbers]
        sources = self._selected_source_records(unit)
        source_sections = []
        for source in sources:
            passages = source.get("passages", [])
            excerpts = "\n".join(
                f"- {item['source_pages']}: {item['unit_text']} [{item['verification_status']}]"
                for item in passages
            ) or f"- {source.get('pages', 'Pages not supplied')}: {source.get('excerpt', 'No verified excerpt indexed.')}"
            source_sections.append(
                f"### {source['source_id']} — {source['title']}\n"
                f"Location: {source.get('path', 'Repository resource')}\n"
                f"Pages: {source.get('pages', 'Not supplied')}\n"
                f"Status: {source.get('verification_status', 'NOT_VERIFIED')}\n{excerpts}"
            )
        originals = "\n\n".join(
            f"### {slide['historical_slide_id']} — {slide['title']}\n{slide['text_extract'] or '[No extracted text]'}"
            for slide in selected_slides
        )
        adjacent = "\n\n".join(
            f"- {slide['historical_slide_id']} — {slide['title']}: {slide['text_extract'] or '[No text]'}"
            for slide in context
        ) or "- No adjacent slide context available."
        pair_rules = ""
        if unit["unit_type"] != "SINGLE_SLIDE":
            pair_rules = "\n- Give every selected slide a distinct teaching job. Avoid duplicated visible text. Include explicit transitions between slides."
        packet = f"""# Lean Lecture Revision Packet

## Revision unit
Unit: {unit['unit_id']}
Type: {unit['unit_type']}
Slides: {', '.join(unit['slide_ids_json'])}

## Instructor query
{unit['instructor_query']}

## Current slide text
{originals}

## Adjacent context
{adjacent}

## Selected evidence
{chr(10).join(source_sections)}

## Task
Revise only the selected slide unit. Put concise student-visible text first and fuller explanation in speaker notes. Preserve attribution, page references, qualifications, and the distinction between source evidence and interpretation.{pair_rules}

## Output schema
Return YAML or JSON with:

```yaml
unit_id: {unit['unit_id']}
slides:
  - slide_id: {unit['slide_ids_json'][0]}
    title: ...
    student_visible_content: [...]
    speaker_notes: ...
    visual_recommendation: ...
    transition_from_previous: ...
    transition_to_next: ...
sources_used: [...]
claims_qualified: [...]
```
"""
        with self.atomic():
            self.connection.execute(
                """UPDATE lean_revision_units SET packet_markdown=?,status='AI_PREPARED',
                validation_errors_json='[]',updated_at=? WHERE id=?""",
                (packet, utc_now(), unit["id"]),
            )
        return self.unit(unit["id"])

    @staticmethod
    def _structured_payload(text: str) -> Any:
        stripped = text.strip()
        if stripped.startswith("```"):
            lines = stripped.splitlines()
            if lines and lines[0].strip().lower() in {"```yaml", "```yml", "```json", "```"}:
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            stripped = "\n".join(lines)
        return yaml.safe_load(stripped)

    def paste_and_validate(self, unit_id: str, result_text: str) -> dict[str, Any]:
        unit = self.unit(unit_id)
        if unit["status"] not in {"AI_PREPARED", "RETURNED"}:
            raise ReinforcementError("prepare the AI packet before pasting a revision")
        errors: list[str] = []
        warnings: list[str] = []
        try:
            payload = self._structured_payload(result_text)
        except yaml.YAMLError as exc:
            payload = None
            errors.append(f"invalid YAML or JSON: {exc}")
        if not isinstance(payload, dict):
            errors.append("result must be a YAML or JSON mapping")
            payload = {}
        if payload.get("unit_id") != unit["unit_id"]:
            errors.append(f"unit_id must be {unit['unit_id']}")
        revisions = payload.get("slides")
        if not isinstance(revisions, list):
            errors.append("slides must be a list")
            revisions = []
        returned_ids = [item.get("slide_id") for item in revisions if isinstance(item, dict)]
        if returned_ids != unit["slide_ids_json"]:
            errors.append("slides must contain the selected slide IDs once, in sequence")
        visible_blocks: list[str] = []
        for index, item in enumerate(revisions, start=1):
            if not isinstance(item, dict):
                errors.append(f"slide {index} must be a mapping")
                continue
            for field in ("title", "student_visible_content", "speaker_notes"):
                if not item.get(field):
                    errors.append(f"slide {index} requires {field}")
            visible = item.get("student_visible_content", [])
            if not isinstance(visible, list):
                errors.append(f"slide {index} student_visible_content must be a list")
            else:
                visible_text = " ".join(str(value) for value in visible).casefold()
                visible_blocks.append(visible_text)
                notes_text = str(item.get("speaker_notes", "")).strip().casefold()
                if visible_text.strip() and notes_text == visible_text.strip():
                    errors.append(f"slide {index} speaker_notes must add explanation, not repeat visible text")
            if len(revisions) > 1 and index < len(revisions) and not item.get("transition_to_next"):
                errors.append(f"slide {index} requires transition_to_next")
            if len(revisions) > 1 and index > 1 and not item.get("transition_from_previous"):
                errors.append(f"slide {index} requires transition_from_previous")
        if len(visible_blocks) > 1:
            for left, right in zip(visible_blocks, visible_blocks[1:]):
                left_words, right_words = set(left.split()), set(right.split())
                if left_words and len(left_words & right_words) / min(len(left_words), len(right_words)) > 0.7:
                    errors.append("adjacent slides duplicate too much student-visible content")
        allowed = {source["source_id"] for source in self._selected_source_records(unit)}
        mentioned = set(RESOURCE_IDENTIFIER_RE.findall(encoded(payload)))
        unknown = sorted(mentioned - allowed)
        if unknown:
            errors.append("source IDs are outside the active packet: " + ", ".join(unknown))
        sources_used = payload.get("sources_used", [])
        if sources_used and not isinstance(sources_used, list):
            errors.append("sources_used must be a list when present")
        elif isinstance(sources_used, list):
            source_records = self._selected_source_records(unit)
            for citation in sources_used:
                citation_text = str(citation).casefold()
                if not any(
                    source["source_id"].casefold() in citation_text
                    or source["title"].casefold() in citation_text
                    for source in source_records
                ):
                    errors.append(f"source reference is outside the active packet: {citation}")
        if not sources_used:
            warnings.append("No source citations were returned; retain the packet evidence during instructor review.")
        status = "AI_VALIDATED" if not errors else "AI_PREPARED"
        with self.atomic():
            self.connection.execute(
                """UPDATE lean_revision_units SET raw_result_text=?,validated_result_json=?,
                validation_errors_json=?,validation_warnings_json=?,status=?,updated_at=? WHERE id=?""",
                (result_text, encoded(payload) if not errors else "{}", encoded(errors),
                 encoded(warnings), status, utc_now(), unit["id"]),
            )
        return {"valid": not errors, "errors": errors, "warnings": warnings, "unit": self.unit(unit["id"])}

    def save_instructor_edit(self, unit_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        unit = self.unit(unit_id)
        if unit["status"] not in EDITABLE_STATUSES:
            raise ReinforcementError("validate the AI revision before instructor editing")
        slides = payload.get("slides")
        if not isinstance(slides, list) or [item.get("slide_id") for item in slides] != unit["slide_ids_json"]:
            raise ReinforcementError("the instructor edit must preserve the selected slide sequence")
        with self.atomic():
            self.connection.execute(
                """UPDATE lean_revision_units SET instructor_edit_json=?,status='INSTRUCTOR_REVIEWED',
                updated_at=? WHERE id=?""", (encoded(payload), utc_now(), unit["id"]),
            )
        return self.unit(unit["id"])

    def accept_content(self, unit_id: str, accepted_by: str) -> dict[str, Any]:
        unit = self.unit(unit_id)
        if unit["status"] not in {"AI_VALIDATED", "INSTRUCTOR_REVIEWED"}:
            raise ReinforcementError("validate and review the revision before accepting content")
        proposal = unit["instructor_edit_json"] or unit["validated_result_json"]
        now = utc_now()
        record = {
            "Slide or slide pair": unit["slide_ids_json"],
            "Instructor query": unit["instructor_query"],
            "Sources used": [source["source_id"] for source in self._selected_source_records(unit)],
            "Main revision": proposal.get("slides", []),
            "Claims qualified": proposal.get("claims_qualified", []),
            "Accepted by": accepted_by.strip() or "Instructor",
            "Date": now,
            "Status": "CONTENT_ACCEPTED",
        }
        with self.atomic():
            self.connection.execute(
                """UPDATE lean_revision_units SET accepted_record_json=?,accepted_by=?,accepted_at=?,
                status='CONTENT_ACCEPTED',updated_at=? WHERE id=?""",
                (encoded(record), record["Accepted by"], now, now, unit["id"]),
            )
        return self.unit(unit["id"])

    def return_revision(self, unit_id: str, note: str) -> dict[str, Any]:
        unit = self.unit(unit_id)
        if unit["status"] not in {"AI_VALIDATED", "INSTRUCTOR_REVIEWED"}:
            raise ReinforcementError("only a validated revision can be returned")
        if not note.strip():
            raise ReinforcementError("add a concise return note")
        with self.atomic():
            self.connection.execute(
                "UPDATE lean_revision_units SET status='RETURNED',return_note=?,updated_at=? WHERE id=?",
                (note.strip(), utc_now(), unit["id"]),
            )
        return self.unit(unit["id"])

    def attach_artefact(
        self, unit_id: str, *, reference: str, filename: str = "", content: bytes | None = None,
    ) -> dict[str, Any]:
        unit = self.unit(unit_id)
        if unit["status"] != "CONTENT_ACCEPTED":
            raise ReinforcementError("accept the intellectual revision before attaching an artefact")
        if not content and not reference.strip():
            raise ReinforcementError("choose a file or provide an artefact reference")
        now = utc_now()
        count = self.connection.execute(
            "SELECT COUNT(*)+1 FROM lean_revision_artefacts WHERE revision_unit_id=?", (unit["id"],)
        ).fetchone()[0]
        artefact_id = f"{unit_id}-ARTEFACT-{count:03d}"
        storage_path = ""
        digest = ""
        safe_name = Path(filename).name
        if content:
            suffix = Path(safe_name).suffix.lower()
            if suffix not in {".png", ".jpg", ".jpeg", ".pdf", ".pptx", ".odp"}:
                raise ReinforcementError("artefact must be PNG, JPEG, PDF, PPTX or ODP")
            folder = self.project_root / "gui" / "local_state" / "lean_revision_artefacts" / unit_id
            folder.mkdir(parents=True, exist_ok=True)
            target = folder / f"{artefact_id}{suffix}"
            target.write_bytes(content)
            storage_path = str(target.relative_to(self.project_root))
            digest = hashlib.sha256(content).hexdigest()
            reference = reference.strip() or safe_name
        with self.atomic():
            self.connection.execute(
                """INSERT INTO lean_revision_artefacts(
                artefact_id,revision_unit_id,reference,storage_path,original_filename,sha256,attached_at)
                VALUES (?,?,?,?,?,?,?)""",
                (artefact_id, unit["id"], reference.strip(), storage_path, safe_name, digest, now),
            )
        return self.unit(unit["id"])

    def workspace(self, unit_id: str = "") -> dict[str, Any]:
        current = None
        if unit_id:
            current = self.unit(unit_id)
        else:
            row = self.connection.execute("SELECT unit_id FROM lean_revision_units ORDER BY id DESC LIMIT 1").fetchone()
            current = self.unit(row[0]) if row else None
        legacy = self.connection.execute(
            """SELECT p.packet_id,p.final_slide_status,p.decided_at,r.instructor_edit_json
            FROM slide_ai_update_packets p LEFT JOIN slide_ai_update_revisions r ON r.id=p.active_revision_id
            WHERE p.final_slide_status='INSTRUCTOR_ACCEPTED_REINFORCED_SLIDE'
            ORDER BY p.id DESC LIMIT 1"""
        ).fetchone()
        legacy_accepted = dict(legacy) if legacy else None
        if legacy_accepted:
            legacy_accepted["instructor_edit_json"] = decoded(legacy_accepted["instructor_edit_json"], {})
        return {
            "slides": self.slides(), "sources": self.repository_sources(), "current": current,
            "recent_units": [dict(row) for row in self.connection.execute(
                "SELECT unit_id,unit_type,slide_ids_json,status,updated_at FROM lean_revision_units ORDER BY id DESC LIMIT 10"
            )],
            "legacy_accepted": legacy_accepted,
        }
