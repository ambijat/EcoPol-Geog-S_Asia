from __future__ import annotations

from course_artifacts.database.connection import CourseArtifactDatabase, utc_now


DECISION_STATES = (
    "PENDING", "ACCEPTED", "REJECTED", "DEFERRED",
    "NEEDS_MORE_EVIDENCE", "EDITED_AND_ACCEPTED",
)


class DecisionRepository:
    def __init__(self, database: CourseArtifactDatabase):
        self.database = database

    def create(self, values: dict) -> int:
        columns = tuple(values)
        with self.database.connection() as connection:
            cursor = connection.execute(
                f"INSERT INTO instructor_decisions({','.join(columns)}) "
                f"VALUES ({','.join('?' for _ in columns)})",
                tuple(values[column] for column in columns),
            )
            return int(cursor.lastrowid)

    def list(self, pending_only: bool = False) -> list[dict]:
        where = "WHERE state='PENDING'" if pending_only else ""
        with self.database.connection() as connection:
            rows = connection.execute(
                f"SELECT * FROM instructor_decisions {where} ORDER BY created_at DESC"
            ).fetchall()
        return [dict(row) for row in rows]

    def resolve(self, decision_pk: int, state: str, note: str = "") -> None:
        if state not in DECISION_STATES or state == "PENDING":
            raise ValueError(f"Invalid resolution state: {state}")
        with self.database.connection() as connection:
            connection.execute(
                "UPDATE instructor_decisions SET state=?,resolution_note=?,resolved_at=? WHERE id=?",
                (state, note, utc_now(), decision_pk),
            )
