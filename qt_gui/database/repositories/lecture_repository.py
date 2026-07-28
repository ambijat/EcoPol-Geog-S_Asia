from __future__ import annotations

from typing import Any

from gui.services import dashboard, lecture_context, update_pair
from qt_gui.database.connection import DatabaseManager


class LectureRepository:
    def __init__(self, database: DatabaseManager):
        self.database = database

    def dashboard(self) -> list[dict[str, Any]]:
        with self.database.connection() as connection:
            return dashboard(connection)

    def lecture_pair(self, number: int) -> dict[str, Any]:
        with self.database.connection() as connection:
            return lecture_context(connection, number)

    def update_architecture(self, number: int, values: dict[str, str]) -> None:
        with self.database.connection() as connection:
            update_pair(connection, number, values)
