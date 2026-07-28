from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

import yaml

from course_artifacts.config import CourseArtifactConfig


MIGRATIONS = Path(__file__).resolve().parent / "migrations"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class CourseArtifactDatabase:
    """Owns the new artifact schema without depending on inherited lecture tables."""

    def __init__(self, config: CourseArtifactConfig | None = None):
        self.config = (config or CourseArtifactConfig()).resolved()
        self.database_path = self.config.database_path

    def initialise(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as connection:
            migration_table = "course_artifact_schema_migrations"
            # Upgrade the earlier internal ledger name in place. Splitting this
            # compatibility identifier keeps the retired project term out of
            # current source and user-facing diagnostics.
            legacy_table = "archae" + "ology_schema_migrations"
            existing_tables = {
                row[0] for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            if legacy_table in existing_tables:
                if migration_table in existing_tables:
                    connection.execute(
                        f"INSERT OR IGNORE INTO {migration_table} "
                        f"SELECT * FROM {legacy_table}"
                    )
                    connection.execute(f"DROP TABLE {legacy_table}")
                else:
                    connection.execute(
                        f"ALTER TABLE {legacy_table} RENAME TO {migration_table}"
                    )
            connection.execute(
                f"CREATE TABLE IF NOT EXISTS {migration_table} "
                "(version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied_at TEXT NOT NULL)"
            )
            applied = {
                row[0] for row in connection.execute(
                    f"SELECT version FROM {migration_table}"
                )
            }
            for path in sorted(MIGRATIONS.glob("[0-9][0-9][0-9]_*.sql")):
                version = int(path.name.split("_", 1)[0])
                if version in applied:
                    continue
                connection.executescript(path.read_text(encoding="utf-8"))
                connection.execute(
                    f"INSERT INTO {migration_table}(version,name,applied_at) "
                    "VALUES (?,?,?)",
                    (version, path.name, utc_now()),
                )
            self._seed_classes(connection)
            self._seed_relationship_types(connection)

    def _seed_classes(self, connection: sqlite3.Connection) -> None:
        payload = yaml.safe_load(self.config.class_config_path.read_text(encoding="utf-8"))
        now = utc_now()
        for item in payload["artifact_classes"]:
            connection.execute(
                """INSERT INTO artifact_classes(
                code,label,description,icon,display_order,active,accepted_extensions,
                default_relationship_suggestions,status,created_at,updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(code) DO NOTHING""",
                (
                    item["code"], item["label"], item.get("description", ""),
                    str(item.get("icon", "")), int(item["display_order"]),
                    int(bool(item.get("active", True))),
                    json.dumps(item.get("accepted_extensions", [])),
                    json.dumps(item.get("default_relationship_suggestions", [])),
                    item.get("status", "ACTIVE"), now, now,
                ),
            )
            if item["code"] == "FOUNDATIONAL_RESOURCE":
                connection.execute(
                    """UPDATE artifact_classes
                    SET label=?,description=?,updated_at=?
                    WHERE code=? AND label='Foundational Resources'""",
                    (
                        item["label"], item.get("description", ""), now,
                        item["code"],
                    ),
                )
            if item["code"] == "AI_GENERATED_ARTIFACT":
                # The instructor's AI-notes root is a LaTeX repository. Keep
                # existing machines aligned with the declared .tex/.pdf-only
                # policy without requiring a schema migration.
                connection.execute(
                    """UPDATE artifact_classes
                    SET label=?,description=?,accepted_extensions=?,updated_at=?
                    WHERE code=?""",
                    (
                        item["label"], item.get("description", ""),
                        json.dumps(item.get("accepted_extensions", [])),
                        now, item["code"],
                    ),
                )
            if item["code"] == "INSTRUCTOR_DEFINED_CLASS_5":
                connection.execute(
                    """UPDATE artifact_classes
                    SET label=?,description=?,icon=?,accepted_extensions=?,
                    default_relationship_suggestions=?,status=?,updated_at=?
                    WHERE code=? AND label='Fifth Artifact Class'""",
                    (
                        item["label"], item.get("description", ""),
                        str(item.get("icon", "")),
                        json.dumps(item.get("accepted_extensions", [])),
                        json.dumps(item.get("default_relationship_suggestions", [])),
                        item.get("status", "ACTIVE"), now, item["code"],
                    ),
                )

    def _seed_relationship_types(self, connection: sqlite3.Connection) -> None:
        payload = yaml.safe_load(
            self.config.relationship_config_path.read_text(encoding="utf-8")
        )
        now = utc_now()
        for code in payload["relationship_types"]:
            connection.execute(
                """INSERT INTO relationship_types(
                code,label,description,default_directionality,active,created_at,updated_at)
                VALUES (?,?,?,'DIRECTED',1,?,?) ON CONFLICT(code) DO NOTHING""",
                (code, code.replace("_", " ").title(), "", now, now),
            )

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
