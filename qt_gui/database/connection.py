from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from gui.database import initialise


class DatabaseManager:
    """Creates short-lived, foreign-key-enabled connections to the shared schema."""

    def __init__(self, database_path: Path, project_root: Path):
        self.database_path = database_path
        self.project_root = project_root

    def initialise(self) -> None:
        connection = initialise(
            self.database_path, self.project_root / "reports" / "source_census.json"
        )
        connection.close()

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            connection.execute("BEGIN")
            yield connection
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
