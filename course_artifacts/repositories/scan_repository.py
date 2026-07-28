from __future__ import annotations

from pathlib import Path
import re
import unicodedata

from course_artifacts.database.connection import CourseArtifactDatabase


def _natural_tokens(value: str) -> tuple:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return tuple(
        (0, int(token)) if token.isdigit() else (1, token)
        for token in re.split(r"(\d+)", normalized)
        if token
    )


def natural_candidate_path_key(candidate: dict) -> tuple:
    """Order lecture files academically rather than lexicographically."""
    relative_path = str(candidate["relative_path"])
    stem = unicodedata.normalize(
        "NFKC", Path(relative_path).stem
    ).casefold().strip()
    lecture = re.fullmatch(r"lecture[\s_-]*(\d+)([a-z]?)(.*)", stem)
    if lecture:
        number = int(lecture.group(1))
        letter = lecture.group(2)
        variant = lecture.group(3).strip(" _-")
        if variant:
            form_rank = 2
        elif letter:
            form_rank = 1
        else:
            form_rank = 0
        return (
            0, number, form_rank, letter, _natural_tokens(variant),
            _natural_tokens(relative_path),
        )
    return (1, _natural_tokens(stem), _natural_tokens(relative_path))


class ScanRepository:
    def __init__(self, database: CourseArtifactDatabase):
        self.database = database

    def create_session(self, values: dict) -> int:
        columns = tuple(values)
        with self.database.connection() as connection:
            cursor = connection.execute(
                f"INSERT INTO scan_sessions({','.join(columns)}) "
                f"VALUES ({','.join('?' for _ in columns)})",
                tuple(values[column] for column in columns),
            )
            return int(cursor.lastrowid)

    def add_candidate(self, values: dict) -> int:
        columns = tuple(values)
        with self.database.connection() as connection:
            cursor = connection.execute(
                f"INSERT INTO scan_candidates({','.join(columns)}) "
                f"VALUES ({','.join('?' for _ in columns)})",
                tuple(values[column] for column in columns),
            )
            return int(cursor.lastrowid)

    def add_candidates(self, records: list[dict]) -> None:
        """Store one scan census in a single lightweight transaction."""
        if not records:
            return
        columns = tuple(records[0])
        statement = (
            f"INSERT INTO scan_candidates({','.join(columns)}) "
            f"VALUES ({','.join('?' for _ in columns)})"
        )
        parameters = [
            tuple(record[column] for column in columns)
            for record in records
        ]
        with self.database.connection() as connection:
            connection.executemany(statement, parameters)

    def complete_session(self, session_pk: int, completed_at: str, count: int) -> None:
        with self.database.connection() as connection:
            connection.execute(
                "UPDATE scan_sessions SET status='COMPLETED',completed_at=?,file_count=? WHERE id=?",
                (completed_at, count, session_pk),
            )

    def fail_session(self, session_pk: int, completed_at: str) -> None:
        with self.database.connection() as connection:
            connection.execute(
                """UPDATE scan_sessions
                SET status='FAILED',completed_at=?,
                    file_count=(
                        SELECT COUNT(*) FROM scan_candidates
                        WHERE scan_session_id=?
                    )
                WHERE id=?""",
                (completed_at, session_pk, session_pk),
            )

    def interrupt_running_sessions(self, interrupted_at: str) -> int:
        """Close sessions abandoned by a terminated desktop process."""
        with self.database.connection() as connection:
            cursor = connection.execute(
                """UPDATE scan_sessions
                SET status='INTERRUPTED',completed_at=?,
                    file_count=(
                        SELECT COUNT(*) FROM scan_candidates
                        WHERE scan_session_id=scan_sessions.id
                    )
                WHERE status='RUNNING'""",
                (interrupted_at,),
            )
            return int(cursor.rowcount)

    def candidates(self, class_code: str | None = None) -> list[dict]:
        where = "WHERE c.proposed_class_code=?" if class_code else ""
        parameters = (class_code,) if class_code else ()
        with self.database.connection() as connection:
            rows = connection.execute(
                f"""SELECT c.*,s.scan_id,s.symbolic_root,s.physical_root,s.status AS scan_status
                FROM scan_candidates c JOIN scan_sessions s ON s.id=c.scan_session_id
                {where} ORDER BY c.id DESC""",
                parameters,
            ).fetchall()
        return sorted(
            (dict(row) for row in rows),
            key=natural_candidate_path_key,
        )

    def latest_candidates(self, class_code: str) -> list[dict]:
        """Return the current census without deleting historical scan evidence."""
        with self.database.connection() as connection:
            rows = connection.execute(
                """SELECT c.*,s.scan_id,s.symbolic_root,s.physical_root,
                          s.status AS scan_status
                FROM scan_candidates c
                JOIN scan_sessions s ON s.id=c.scan_session_id
                WHERE c.scan_session_id=(
                    SELECT id FROM scan_sessions
                    WHERE symbolic_root=? AND status='COMPLETED'
                    ORDER BY id DESC LIMIT 1
                )
                ORDER BY c.relative_path COLLATE NOCASE, c.id""",
                (class_code,),
            ).fetchall()
        return sorted(
            (dict(row) for row in rows),
            key=natural_candidate_path_key,
        )

    def latest_session(self, class_code: str) -> dict | None:
        with self.database.connection() as connection:
            row = connection.execute(
                """SELECT * FROM scan_sessions
                WHERE symbolic_root=? AND status='COMPLETED'
                ORDER BY id DESC LIMIT 1""",
                (class_code,),
            ).fetchone()
        return dict(row) if row is not None else None

    def get_candidate(self, candidate_pk: int) -> dict:
        with self.database.connection() as connection:
            row = connection.execute(
                """SELECT c.*,s.symbolic_root,s.physical_root
                FROM scan_candidates c JOIN scan_sessions s ON s.id=c.scan_session_id
                WHERE c.id=?""",
                (candidate_pk,),
            ).fetchone()
        if row is None:
            raise KeyError(f"Unknown scan candidate: {candidate_pk}")
        return dict(row)

    def set_status(
        self, candidate_pk: int, status: str, registered_artifact_id: int | None = None,
        related_artifact_id: int | None = None, note: str = "",
    ) -> None:
        with self.database.connection() as connection:
            connection.execute(
                """UPDATE scan_candidates SET candidate_status=?,registered_artifact_id=?,
                related_artifact_id=?,decision_note=? WHERE id=?""",
                (
                    status, registered_artifact_id, related_artifact_id,
                    note, candidate_pk,
                ),
            )
