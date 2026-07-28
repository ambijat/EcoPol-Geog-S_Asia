from __future__ import annotations

from pathlib import Path

from gui.pptx_service import generate_pptx, next_deck_filename
from qt_gui.database.connection import DatabaseManager


class PptxService:
    def __init__(self, database: DatabaseManager):
        self.database = database

    def next_filename(self, directory: Path, number: int, part: str, status: str):
        return next_deck_filename(directory, number, part, status)

    def generate(self, number: int, part: str, status: str = "DRAFT"):
        with self.database.connection() as connection:
            return generate_pptx(connection, self.database.project_root, number, part, status)
