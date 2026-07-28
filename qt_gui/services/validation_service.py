from __future__ import annotations

from gui.pptx_service import validate_deck_plan
from qt_gui.database.connection import DatabaseManager


class ValidationService:
    def __init__(self, database: DatabaseManager):
        self.database = database

    def validate_part(self, number: int, part: str):
        with self.database.connection() as connection:
            pair = connection.execute("SELECT id FROM lecture_pairs WHERE lecture_number=?", (number,)).fetchone()
            return validate_deck_plan(connection, pair[0], part)
