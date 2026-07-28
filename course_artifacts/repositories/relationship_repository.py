from __future__ import annotations

from course_artifacts.database.connection import CourseArtifactDatabase, utc_now


class RelationshipRepository:
    def __init__(self, database: CourseArtifactDatabase):
        self.database = database

    def types(self, active_only: bool = True) -> list[dict]:
        where = "WHERE active=1" if active_only else ""
        with self.database.connection() as connection:
            rows = connection.execute(
                f"SELECT * FROM relationship_types {where} ORDER BY label"
            ).fetchall()
        return [dict(row) for row in rows]

    def insert(self, values: dict) -> int:
        columns = tuple(values)
        with self.database.connection() as connection:
            cursor = connection.execute(
                f"INSERT INTO artifact_relationships({','.join(columns)}) "
                f"VALUES ({','.join('?' for _ in columns)})",
                tuple(values[column] for column in columns),
            )
            return int(cursor.lastrowid)

    def list(self, artifact_pk: int | None = None) -> list[dict]:
        where = ""
        parameters: tuple = ()
        if artifact_pk is not None:
            where = "WHERE r.source_artifact_id=? OR r.target_artifact_id=?"
            parameters = (artifact_pk, artifact_pk)
        with self.database.connection() as connection:
            rows = connection.execute(
                f"""SELECT r.*,rt.code AS relationship_type,
                s.artifact_id AS source_identifier,s.title AS source_title,
                t.artifact_id AS target_identifier,t.title AS target_title
                FROM artifact_relationships r
                JOIN relationship_types rt ON rt.id=r.relationship_type_id
                JOIN artifacts s ON s.id=r.source_artifact_id
                JOIN artifacts t ON t.id=r.target_artifact_id
                {where} ORDER BY r.created_at DESC,r.id DESC""",
                parameters,
            ).fetchall()
        return [dict(row) for row in rows]

    def set_status(self, relationship_pk: int, status: str, reviewer: str, note: str = "") -> None:
        with self.database.connection() as connection:
            connection.execute(
                """UPDATE artifact_relationships SET status=?,reviewed_by=?,reviewed_at=?,
                instructor_note=CASE WHEN ?<>'' THEN ? ELSE instructor_note END WHERE id=?""",
                (status, reviewer, utc_now(), note, note, relationship_pk),
            )
