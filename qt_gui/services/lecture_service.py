from __future__ import annotations

from qt_gui.database.repositories.lecture_repository import LectureRepository
from qt_gui.models.lecture import LectureCardData


class LectureService:
    def __init__(self, repository: LectureRepository):
        self.repository = repository

    def dashboard_cards(self) -> list[LectureCardData]:
        return [LectureCardData.from_dashboard(row) for row in self.repository.dashboard()]

    def load_pair(self, number: int):
        return self.repository.lecture_pair(number)

    def save_architecture(self, number: int, values: dict[str, str]) -> None:
        self.repository.update_architecture(number, values)
