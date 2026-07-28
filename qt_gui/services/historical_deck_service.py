from __future__ import annotations

import json
from pathlib import Path

from gui.services import HISTORICAL_STATUSES, record_historical_derivative, utc_now, validate_relative_path
from qt_gui.database.connection import DatabaseManager
from qt_gui.services.historical_extraction import extract_read_only, resolve_symbolic


class HistoricalDeckService:
    ASSIGNMENTS = {"L01A", "L01B", "SHARED", "SUPPLEMENTARY", "ARCHIVE_ONLY", "REQUIRES_INSPECTION"}

    def __init__(self, database: DatabaseManager, repository_root: Path | None = None,
                 derivative_root: Path | None = None):
        self.database = database
        self.repository_root = repository_root
        self.derivative_root = derivative_root

    def list_for_lecture(self, number: int):
        with self.database.connection() as connection:
            return [dict(row) for row in connection.execute(
                """SELECT hd.* FROM historical_decks hd JOIN lecture_pairs lp
                ON lp.id=hd.lecture_pair_id WHERE lp.lecture_number=? ORDER BY deck_id""", (number,)
            )]

    def register_derivative(self, deck_pk: int, derivative_type: str, relative_path: str, slide_pk: int | None = None) -> None:
        with self.database.connection() as connection:
            record_historical_derivative(connection, deck_pk, derivative_type, relative_path, slide_pk)

    def slides(self, deck_pk: int):
        with self.database.connection() as connection:
            return [dict(row) for row in connection.execute(
                "SELECT * FROM historical_slides WHERE deck_id=? ORDER BY historical_slide_number", (deck_pk,))]

    def confirm_assignment(self, deck_pk: int, assignment: str, actor: str = "Instructor") -> None:
        if assignment not in self.ASSIGNMENTS:
            raise ValueError("invalid historical deck assignment")
        with self.database.connection() as connection:
            connection.execute(
                """UPDATE historical_decks SET instructor_assignment=?,
                instructor_confirmation_required=?,updated_at=?,updated_by=? WHERE id=?""",
                (assignment, int(assignment == "REQUIRES_INSPECTION"), utc_now(), actor, deck_pk),
            )
            connection.commit()

    def classify_slide(self, slide_pk: int, values: dict, actor: str = "Instructor") -> None:
        status = values.get("current_status", "VERIFY")
        if status not in HISTORICAL_STATUSES:
            raise ValueError("invalid historical-slide status")
        target_part = values.get("target_part", "")
        if target_part not in {"", "A", "B", "SHARED", "SUPPLEMENTARY"}:
            raise ValueError("invalid target part")
        confidence = values.get("confidence", "UNASSESSED")
        with self.database.connection() as connection:
            if connection.execute("SELECT id FROM historical_slides WHERE id=?", (slide_pk,)).fetchone() is None:
                raise KeyError(slide_pk)
            connection.execute(
                """UPDATE historical_slides SET current_status=?,reason=?,target_part=?,target_sequence=?,
                factual_update_required=?,visual_update_required=?,linked_resource_ids=?,linked_note_ids=?,
                confidence=?,approval_status='WORKING_DRAFT',instructor_comment=?,updated_at=?,updated_by=? WHERE id=?""",
                (status, values.get("reason", ""), target_part,
                 int(values["target_sequence"]) if values.get("target_sequence") else None,
                 int(bool(values.get("factual_update_required"))), int(bool(values.get("visual_update_required"))),
                 json.dumps(values.get("linked_resource_ids", [])), json.dumps(values.get("linked_note_ids", [])),
                 confidence, values.get("instructor_comment", ""), utc_now(), actor, slide_pk),
            )
            connection.commit()

    def inspect(self, deck_pk: int) -> dict:
        if self.repository_root is None or self.derivative_root is None:
            raise ValueError("historical repository mapping is not configured")
        with self.database.connection() as connection:
            deck = connection.execute("SELECT * FROM historical_decks WHERE id=?", (deck_pk,)).fetchone()
            if deck is None:
                raise KeyError(deck_pk)
            source = resolve_symbolic(deck["source_locator"], self.repository_root)
            output = self.derivative_root / deck["deck_id"]
            result = extract_read_only(source, output)
            if deck["content_sha256"] and result["source_sha256"] != deck["content_sha256"]:
                raise ValueError("source checksum no longer matches the recorded census")
            connection.execute("DELETE FROM historical_slides WHERE deck_id=?", (deck_pk,))
            for record in result["records"]:
                slide_id = f'{deck["deck_id"]}-S{record["number"]:03d}'
                preview = record.get("preview_path", "")
                relative_preview = ""
                if preview:
                    relative_preview = validate_relative_path(Path(preview).relative_to(self.database.project_root).as_posix())
                cursor = connection.execute(
                    """INSERT INTO historical_slides(historical_slide_id,deck_id,historical_slide_number,
                    title,visual_preview,text_extract,current_status,layout_name,image_count,chart_count,
                    table_count,speaker_note_available,page_status,updated_at,updated_by)
                    VALUES (?,?,?,?,?,?,'VERIFY',?,?,?,?,?,?,?,'Application')""",
                    (slide_id, deck_pk, record["number"], record["title"], relative_preview,
                     record["text"], record["layout_name"], record["image_count"], record["chart_count"],
                     record["table_count"], int(record["speaker_note_available"]), record["page_status"], result["timestamp"]),
                )
                if relative_preview:
                    connection.execute(
                        """INSERT INTO historical_derivatives(deck_id,historical_slide_id,derivative_type,
                        relative_path,source_locator,source_sha256,generated_at,derivative_status,extraction_tool)
                        VALUES (?,?,'PREVIEW',?,?,?,?, 'READ_ONLY_DERIVATIVE',?)""",
                        (deck_pk, cursor.lastrowid, relative_preview, deck["source_locator"],
                         result["source_sha256"], result["timestamp"], result["tool"]),
                    )
            cache_relative = validate_relative_path(result["cache"].relative_to(self.database.project_root).as_posix())
            connection.execute(
                """INSERT OR REPLACE INTO historical_derivatives(deck_id,historical_slide_id,derivative_type,
                relative_path,source_locator,source_sha256,generated_at,derivative_status,extraction_tool)
                VALUES (?,NULL,'TEXT_EXTRACT',?,?,?,?, 'READ_ONLY_DERIVATIVE',?)""",
                (deck_pk, cache_relative, deck["source_locator"], result["source_sha256"], result["timestamp"], result["tool"]),
            )
            connection.execute(
                "UPDATE historical_decks SET discovery_status='READ_ONLY_EXTRACTED',updated_at=?,updated_by='Application' WHERE id=?",
                (result["timestamp"], deck_pk),
            )
            if result.get("source_format") == "ODP":
                converted_relative = validate_relative_path(
                    result["converted_pdf"].relative_to(self.database.project_root).as_posix()
                )
                connection.execute(
                    """INSERT INTO odp_conversion_records(deck_id,source_symbolic_reference,source_sha256,
                    conversion_tool,conversion_timestamp,derivative_pdf,derivative_pdf_sha256,page_count)
                    VALUES (?,?,?,?,?,?,?,?)""",
                    (deck_pk, deck["source_locator"], result["source_sha256"], result["conversion_tool"],
                     result["timestamp"], converted_relative, result["converted_pdf_sha256"], result["page_count"]),
                )
            connection.commit()
        return result
