from __future__ import annotations

from course_artifacts.database.connection import CourseArtifactDatabase, utc_now


class ArtifactRepository:
    def __init__(self, database: CourseArtifactDatabase):
        self.database = database

    def insert(self, values: dict) -> int:
        columns = tuple(values)
        placeholders = ",".join("?" for _ in columns)
        with self.database.connection() as connection:
            cursor = connection.execute(
                f"INSERT INTO artifacts({','.join(columns)}) VALUES ({placeholders})",
                tuple(values[column] for column in columns),
            )
            return int(cursor.lastrowid)

    def list(self, class_code: str | None = None, include_archived: bool = False) -> list[dict]:
        conditions = []
        parameters: list[object] = []
        if class_code:
            conditions.append("c.code=?")
            parameters.append(class_code)
        if not include_archived:
            conditions.append("a.archived=0")
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        with self.database.connection() as connection:
            rows = connection.execute(
                f"""SELECT a.*,c.code AS class_code,c.label AS class_label,
                (SELECT COUNT(*) FROM artifact_relationships r
                 WHERE r.source_artifact_id=a.id OR r.target_artifact_id=a.id) AS relationship_count
                FROM artifacts a JOIN artifact_classes c ON c.id=a.artifact_class_id
                {where} ORDER BY a.updated_at DESC,a.id DESC""",
                parameters,
            ).fetchall()
        return [dict(row) for row in rows]

    def get(self, artifact_pk: int) -> dict:
        with self.database.connection() as connection:
            row = connection.execute(
                """SELECT a.*,c.code AS class_code,c.label AS class_label
                FROM artifacts a JOIN artifact_classes c ON c.id=a.artifact_class_id
                WHERE a.id=?""",
                (artifact_pk,),
            ).fetchone()
        if row is None:
            raise KeyError(f"Unknown artifact: {artifact_pk}")
        return dict(row)

    def by_checksum(self, checksum: str) -> list[dict]:
        if not checksum:
            return []
        with self.database.connection() as connection:
            rows = connection.execute(
                "SELECT * FROM artifacts WHERE checksum_sha256=? AND archived=0", (checksum,)
            ).fetchall()
        return [dict(row) for row in rows]

    def counts(self) -> dict[str, dict[str, int]]:
        with self.database.connection() as connection:
            rows = connection.execute(
                """SELECT c.code,
                COUNT(a.id) AS total,
                COALESCE(SUM(CASE WHEN a.inspection_status='UNINSPECTED' THEN 1 ELSE 0 END),0) AS uninspected,
                COALESCE(SUM(CASE WHEN a.instructor_status='AWAITING_CLASSIFICATION' THEN 1 ELSE 0 END),0) AS awaiting_classification,
                COALESCE(SUM(CASE WHEN a.instructor_status='AWAITING_REVIEW' THEN 1 ELSE 0 END),0) AS awaiting_review,
                COALESCE(SUM(CASE WHEN EXISTS(
                    SELECT 1 FROM artifact_relationships r
                    WHERE r.source_artifact_id=a.id OR r.target_artifact_id=a.id
                ) THEN 1 ELSE 0 END),0) AS related,
                COALESCE(SUM(CASE WHEN a.id IS NOT NULL AND NOT EXISTS(
                    SELECT 1 FROM artifact_relationships r
                    WHERE r.source_artifact_id=a.id OR r.target_artifact_id=a.id
                ) THEN 1 ELSE 0 END),0) AS orphaned,
                COALESCE(SUM(CASE WHEN a.physical_path<>'' AND NOT EXISTS(
                    SELECT 1 FROM artifact_locations l
                    WHERE l.artifact_id=a.id AND l.status='AVAILABLE'
                ) THEN 1 ELSE 0 END),0) AS missing
                FROM artifact_classes c
                LEFT JOIN artifacts a ON a.artifact_class_id=c.id AND a.archived=0
                GROUP BY c.id ORDER BY c.display_order"""
            ).fetchall()
        return {row["code"]: dict(row) for row in rows}

    def archive(self, artifact_pk: int) -> None:
        with self.database.connection() as connection:
            connection.execute("UPDATE artifacts SET archived=1 WHERE id=?", (artifact_pk,))

    def mark_reviewed(self, artifact_pk: int) -> None:
        with self.database.connection() as connection:
            cursor = connection.execute(
                """UPDATE artifacts
                SET inspection_status='INSPECTED',review_status='REVIEWED',
                instructor_status='REVIEWED',updated_at=?
                WHERE id=? AND archived=0""",
                (utc_now(), artifact_pk),
            )
        if cursor.rowcount != 1:
            raise KeyError(f"Unknown active artifact: {artifact_pk}")
