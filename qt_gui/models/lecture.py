from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LectureCardData:
    number: int
    weekly_title: str
    part_a_title: str
    part_b_title: str
    title_status: str
    historical_decks: int
    resources: int
    notes: int
    slide_plan_status: str
    deck_status: str
    verification_status: str
    class_status: str
    ledger_status: str

    @classmethod
    def from_dashboard(cls, row: dict[str, Any]) -> "LectureCardData":
        return cls(
            number=row["lecture_number"], weekly_title=row["weekly_title"],
            part_a_title=row["part_a_title"], part_b_title=row["part_b_title"],
            title_status=row["title_status"], historical_decks=row["historical_decks"],
            resources=row["mapped_resources"], notes=row["revised_notes"],
            slide_plan_status=row["slide_plan_status"], deck_status=row["deliverable_status"],
            verification_status=row["verification_status"], class_status=row["class_conduct_status"],
            ledger_status=row["ledger_event_status"],
        )
