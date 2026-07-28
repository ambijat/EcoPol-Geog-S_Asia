from __future__ import annotations

import json

from course_artifacts.database.connection import CourseArtifactDatabase, utc_now


class ArtifactClassRepository:
    def __init__(self, database: CourseArtifactDatabase):
        self.database = database

    def list(self, active_only: bool = False) -> list[dict]:
        where = "WHERE active=1" if active_only else ""
        with self.database.connection() as connection:
            rows = connection.execute(
                f"SELECT * FROM artifact_classes {where} ORDER BY display_order,code"
            ).fetchall()
        return [self._decode(dict(row)) for row in rows]

    def get(self, code: str) -> dict:
        with self.database.connection() as connection:
            row = connection.execute(
                "SELECT * FROM artifact_classes WHERE code=?", (code,)
            ).fetchone()
        if row is None:
            raise KeyError(f"Unknown artifact class: {code}")
        return self._decode(dict(row))

    def update(self, code: str, values: dict) -> None:
        accepted = json.dumps(values.get("accepted_extensions", []))
        suggestions = json.dumps(values.get("default_relationship_suggestions", []))
        with self.database.connection() as connection:
            cursor = connection.execute(
                """UPDATE artifact_classes SET label=?,description=?,icon=?,display_order=?,
                active=?,accepted_extensions=?,default_relationship_suggestions=?,status=?,updated_at=?
                WHERE code=?""",
                (
                    values["label"].strip(), values.get("description", "").strip(),
                    values.get("icon", "").strip(), int(values["display_order"]),
                    int(bool(values.get("active", True))), accepted, suggestions,
                    values.get("status", "ACTIVE"), utc_now(), code,
                ),
            )
        if cursor.rowcount != 1:
            raise KeyError(f"Unknown artifact class: {code}")

    @staticmethod
    def _decode(row: dict) -> dict:
        row["accepted_extensions"] = json.loads(row["accepted_extensions"])
        row["default_relationship_suggestions"] = json.loads(
            row["default_relationship_suggestions"]
        )
        row["active"] = bool(row["active"])
        return row
