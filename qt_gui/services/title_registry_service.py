from __future__ import annotations

from qt_gui.database.repositories.title_repository import TitleRepository


class TitleRegistryService:
    def __init__(self, repository: TitleRepository):
        self.repository = repository

    def validate(self):
        return self.repository.validate_files()

    def records(self):
        return self.repository.rows()

    def preview(self):
        return self.repository.preview()

    def apply_selected(self, batch_id: int, proposal_ids: set[int]) -> int:
        return self.repository.apply_selected(batch_id, proposal_ids)

    def save_title(self, target_type: str, identifier: str, title: str, confirmed: bool) -> None:
        self.repository.edit(target_type, identifier, title, confirmed)

    def export_confirmed(self):
        return self.repository.export_confirmed()
