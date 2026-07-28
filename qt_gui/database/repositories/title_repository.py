from __future__ import annotations

from typing import Any

from gui.title_registry import (
    apply_selected_title_sync, edit_title, export_confirmed_titles,
    load_title_files, propose_title_sync,
)
from qt_gui.database.connection import DatabaseManager


class TitleRepository:
    def __init__(self, database: DatabaseManager):
        self.database = database

    def validate_files(self) -> tuple[dict[str, str], dict[str, str]]:
        return load_title_files(self.database.project_root)

    def rows(self) -> list[dict[str, Any]]:
        with self.database.connection() as connection:
            pairs = connection.execute("SELECT * FROM lecture_pairs ORDER BY lecture_number").fetchall()
            result = []
            for pair in pairs:
                parts = connection.execute(
                    "SELECT * FROM lecture_parts WHERE lecture_pair_id=? ORDER BY part", (pair["id"],)
                ).fetchall()
                evidence = connection.execute(
                    "SELECT * FROM title_evidence WHERE lecture_pair_id=? ORDER BY target_identifier,source_filename",
                    (pair["id"],),
                ).fetchall()
                result.append({"pair": dict(pair), "parts": [dict(row) for row in parts], "evidence": [dict(row) for row in evidence]})
            return result

    def preview(self) -> tuple[int, list[dict[str, Any]]]:
        with self.database.connection() as connection:
            batch_id = propose_title_sync(connection, self.database.project_root)
            proposals = [dict(row) for row in connection.execute(
                "SELECT * FROM title_sync_proposals WHERE batch_id=? ORDER BY target_identifier", (batch_id,)
            )]
            return batch_id, proposals

    def apply_selected(self, batch_id: int, proposal_ids: set[int]) -> int:
        with self.database.connection() as connection:
            return apply_selected_title_sync(connection, batch_id, proposal_ids)

    def edit(self, target_type: str, identifier: str, title: str, confirmed: bool) -> None:
        with self.database.connection() as connection:
            edit_title(connection, target_type, identifier, title, confirmed)

    def export_confirmed(self):
        with self.database.connection() as connection:
            return export_confirmed_titles(connection, self.database.project_root)
