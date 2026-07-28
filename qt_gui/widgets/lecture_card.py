from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QPushButton, QVBoxLayout

from qt_gui.models.lecture import LectureCardData


class LectureCard(QFrame):
    opened = Signal(int)

    def __init__(self, data: LectureCardData, parent=None):
        super().__init__(parent)
        self.data = data
        self.setObjectName("lectureCard")
        self.setProperty("focusLecture", data.number == 1)
        layout = QVBoxLayout(self)
        eyebrow = QLabel(f"LECTURE {data.number:02d}   ·   {data.title_status}")
        eyebrow.setObjectName("eyebrow")
        title = QLabel(data.weekly_title)
        title.setObjectName("cardTitle")
        title.setWordWrap(True)
        parts = QGridLayout()
        parts.addWidget(QLabel("TUE · PART A"), 0, 0)
        parts.addWidget(QLabel("FRI · PART B"), 0, 1)
        part_a = QLabel(data.part_a_title); part_a.setWordWrap(True)
        part_b = QLabel(data.part_b_title); part_b.setWordWrap(True)
        parts.addWidget(part_a, 1, 0)
        parts.addWidget(part_b, 1, 1)
        status = QLabel(
            f"Decks {data.historical_decks}  ·  Resources {data.resources}  ·  Notes {data.notes}\n"
            f"Plan {data.slide_plan_status}  ·  Output {data.deck_status}  ·  Facts {data.verification_status}\n"
            f"Class {data.class_status}  ·  Ledger {data.ledger_status}"
        )
        status.setObjectName("cardMeta")
        status.setWordWrap(True)
        button = QPushButton("Open lecture pair")
        button.clicked.connect(lambda: self.opened.emit(data.number))
        layout.addWidget(eyebrow)
        layout.addWidget(title)
        layout.addLayout(parts)
        layout.addWidget(status)
        layout.addStretch()
        layout.addWidget(button)
